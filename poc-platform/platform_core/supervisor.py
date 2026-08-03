"""Starts, stops and health-checks the prototype processes.

Each prototype is an ordinary process started from its own directory with the
environment described in docs/platform-contract.md. The supervisor keeps no
state a restart cannot rebuild: if the gateway dies, the children are killed
with it and started again on demand.
"""

import os
import signal
import subprocess
import time
from enum import Enum
from typing import Optional

import httpx
from pydantic import BaseModel

from platform_core.config import LOG_DIR, STATE_DIR
from platform_core.manifest import Manifest

#: How often the readiness poller retries the health endpoint.
POLL_INTERVAL_SECONDS = 1.0
HEALTH_TIMEOUT_SECONDS = 2.0
#: Grace period between SIGTERM and SIGKILL when stopping an app.
STOP_GRACE_SECONDS = 8.0
LOG_TAIL_BYTES = 64 * 1024


class AppState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    #: The process is alive but has not passed a health check in time, or it
    #: exited on its own. Either way the logs are the next stop.
    UNHEALTHY = "unhealthy"


class AppStatus(BaseModel):
    id: str
    state: AppState
    pid: Optional[int] = None
    port: int
    #: Populated once the app answers its health endpoint.
    started_at: Optional[float] = None
    ready_at: Optional[float] = None
    exit_code: Optional[int] = None
    message: str = ""
    log_file: str


def app_env(manifest: Manifest, gateway_url: str, state_dir: str = STATE_DIR) -> dict[str, str]:
    """The environment contract every hosted prototype can rely on."""
    data_dir = os.path.join(state_dir, manifest.id)
    os.makedirs(data_dir, exist_ok=True)
    env = dict(os.environ)
    env.update(
        {
            "PORT": str(manifest.runtime.port),
            "PLATFORM_MANAGED": "1",
            "PLATFORM_APP_ID": manifest.id,
            "PLATFORM_BASE_PATH": manifest.base_path,
            "PLATFORM_DATA_DIR": data_dir,
            "PLATFORM_GATEWAY_URL": gateway_url,
        }
    )
    return env


class ManagedApp:
    """One prototype process."""

    def __init__(self, manifest: Manifest, app_dir: str, gateway_url: str) -> None:
        self.manifest = manifest
        self.app_dir = app_dir
        self.gateway_url = gateway_url
        self.log_file = os.path.join(LOG_DIR, f"{manifest.id}.log")
        self._process: Optional[subprocess.Popen] = None
        self._started_at: Optional[float] = None
        self._ready_at: Optional[float] = None
        self._message = ""

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.manifest.runtime.port}"

    def status(self) -> AppStatus:
        exit_code = None
        if self._process is None:
            state = AppState.STOPPED
        else:
            exit_code = self._process.poll()
            if exit_code is not None:
                state = AppState.UNHEALTHY if exit_code != 0 else AppState.STOPPED
                if exit_code != 0 and not self._message:
                    self._message = f"process exited with code {exit_code}"
            elif self._ready_at is not None:
                state = AppState.RUNNING
            elif self._is_timed_out():
                state = AppState.UNHEALTHY
            else:
                state = AppState.STARTING

        return AppStatus(
            id=self.manifest.id,
            state=state,
            pid=self._process.pid if self._process and exit_code is None else None,
            port=self.manifest.runtime.port,
            started_at=self._started_at,
            ready_at=self._ready_at,
            exit_code=exit_code,
            message=self._message,
            log_file=self.log_file,
        )

    def _is_timed_out(self) -> bool:
        if self._started_at is None:
            return False
        elapsed = time.time() - self._started_at
        if elapsed <= self.manifest.runtime.ready_timeout_seconds:
            return False
        self._message = (
            f"did not answer {self.manifest.runtime.health_path} within "
            f"{self.manifest.runtime.ready_timeout_seconds}s"
        )
        return True

    def start(self) -> AppStatus:
        """Launch the app if it is not already running. Returns immediately.

        Cold starts install dependencies and build frontends, so readiness is
        polled in the background rather than waited on here.
        """
        if self._process is not None and self._process.poll() is None:
            return self.status()

        os.makedirs(LOG_DIR, exist_ok=True)
        self._message = ""
        self._ready_at = None
        self._started_at = time.time()

        with open(self.log_file, "ab", buffering=0) as log:
            log.write(
                f"\n=== {time.strftime('%Y-%m-%dT%H:%M:%S')} starting "
                f"{self.manifest.id} on port {self.manifest.runtime.port} ===\n".encode()
            )
            self._process = subprocess.Popen(  # noqa: S602 - command comes from a trusted manifest
                self.manifest.runtime.command,
                shell=True,
                cwd=self.app_dir,
                env=app_env(self.manifest, self.gateway_url),
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        return self.status()

    def stop(self) -> AppStatus:
        """Terminate the app's whole process group (run.sh spawns children)."""
        process = self._process
        if process is not None and process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                process.terminate()
            try:
                process.wait(timeout=STOP_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    process.kill()
                process.wait(timeout=STOP_GRACE_SECONDS)

        self._process = None
        self._started_at = None
        self._ready_at = None
        self._message = ""
        return self.status()

    def poll_health(self, client: httpx.Client) -> None:
        """One health probe; flips a starting app to running."""
        if self._process is None or self._process.poll() is not None:
            return
        try:
            response = client.get(
                f"{self.base_url}{self.manifest.runtime.health_path}",
                timeout=HEALTH_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError:
            return
        if response.status_code < 400:
            if self._ready_at is None:
                self._ready_at = time.time()
            self._message = ""

    def tail_log(self, max_bytes: int = LOG_TAIL_BYTES) -> str:
        if not os.path.exists(self.log_file):
            return ""
        with open(self.log_file, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - max_bytes))
            return handle.read().decode("utf-8", errors="replace")
