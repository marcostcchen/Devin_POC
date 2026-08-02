"""The registry: which prototypes exist, whether they comply, and their state.

Discovery is a directory scan for `poc.yaml`, so adding a prototype to the
platform is one file - no code change here.
"""

import os
import threading
import time
from typing import Iterator, Optional

import httpx
from pydantic import BaseModel

from platform_core.config import PlatformConfig
from platform_core.manifest import MANIFEST_FILENAME, Manifest, ManifestError, load_manifest
from platform_core.policy import Policy
from platform_core.supervisor import AppState, AppStatus, ManagedApp

#: Directories that never contain a hosted prototype.
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".data", "dist", "build"}
HEALTH_POLL_SECONDS = 2.0


class RegisteredApp(BaseModel):
    """A discovered prototype plus everything the console needs to render it."""

    manifest: Manifest
    directory: str
    base_path: str
    violations: list[str]
    status: AppStatus

    @property
    def compliant(self) -> bool:
        return not self.violations


class DiscoveryError(BaseModel):
    """A `poc.yaml` that could not be loaded, surfaced instead of swallowed."""

    path: str
    error: str


def discover_manifests(apps_root: str) -> tuple[dict[str, tuple[Manifest, str]], list[DiscoveryError]]:
    """Find every `poc.yaml` one level below `apps_root`."""
    found: dict[str, tuple[Manifest, str]] = {}
    errors: list[DiscoveryError] = []

    for entry in sorted(os.listdir(apps_root)):
        directory = os.path.join(apps_root, entry)
        if entry in SKIP_DIRS or entry.startswith(".") or not os.path.isdir(directory):
            continue
        path = os.path.join(directory, MANIFEST_FILENAME)
        if not os.path.exists(path):
            continue
        try:
            manifest = load_manifest(path)
        except ManifestError as exc:
            errors.append(DiscoveryError(path=path, error=str(exc)))
            continue
        if manifest.id in found:
            errors.append(DiscoveryError(path=path, error=f"duplicate app id {manifest.id!r}"))
            continue
        found[manifest.id] = (manifest, directory)

    return found, errors


class Registry:
    """Owns the discovered prototypes and their processes."""

    def __init__(self, config: PlatformConfig, policy: Policy, platform_dir: str) -> None:
        self.config = config
        self.policy = policy
        self.apps_root = config.resolved_apps_root(platform_dir)
        self.gateway_url = f"http://127.0.0.1:{config.gateway.port}"
        self._lock = threading.Lock()
        self._apps: dict[str, ManagedApp] = {}
        self._violations: dict[str, list[str]] = {}
        self.errors: list[DiscoveryError] = []
        self._stop_polling = threading.Event()
        self._poller: Optional[threading.Thread] = None
        self.reload()

    def reload(self) -> None:
        """Rescan manifests, keeping the processes of apps that still exist."""
        manifests, errors = discover_manifests(self.apps_root)
        with self._lock:
            self.errors = errors
            self._violations = {
                app_id: self.policy.check_manifest(manifest)
                for app_id, (manifest, _) in manifests.items()
            }
            for app_id in list(self._apps):
                if app_id not in manifests:
                    self._apps.pop(app_id).stop()
            for app_id, (manifest, directory) in manifests.items():
                existing = self._apps.get(app_id)
                if existing is None:
                    self._apps[app_id] = ManagedApp(manifest, directory, self.gateway_url)
                else:
                    existing.manifest = manifest

    @property
    def manifests(self) -> dict[str, Manifest]:
        with self._lock:
            return {app_id: app.manifest for app_id, app in self._apps.items()}

    def ids(self) -> list[str]:
        with self._lock:
            return list(self._apps)

    def get(self, app_id: str) -> Optional[ManagedApp]:
        with self._lock:
            return self._apps.get(app_id)

    def apps(self) -> list[RegisteredApp]:
        with self._lock:
            apps = list(self._apps.values())
            violations = dict(self._violations)
        return [
            RegisteredApp(
                manifest=app.manifest,
                directory=os.path.relpath(app.app_dir, self.apps_root),
                base_path=app.manifest.base_path,
                violations=violations.get(app.manifest.id, []),
                status=app.status(),
            )
            for app in apps
        ]

    def violations_for(self, app_id: str) -> list[str]:
        with self._lock:
            return list(self._violations.get(app_id, []))

    def start(self, app_id: str) -> AppStatus:
        """Start a prototype, refusing anything that breaks environment policy."""
        app = self.get(app_id)
        if app is None:
            raise KeyError(app_id)
        violations = self.violations_for(app_id)
        if violations:
            raise PermissionError(
                f"{app_id} violates environment policy: " + "; ".join(violations)
            )
        return app.start()

    def stop(self, app_id: str) -> AppStatus:
        app = self.get(app_id)
        if app is None:
            raise KeyError(app_id)
        return app.stop()

    def stop_all(self) -> None:
        for app in list(self._apps.values()):
            app.stop()

    def running(self) -> Iterator[ManagedApp]:
        for app in list(self._apps.values()):
            if app.status().state in (AppState.RUNNING, AppState.STARTING):
                yield app

    def start_polling(self) -> None:
        """Health-check starting/running apps in the background."""
        if self._poller is not None:
            return

        def loop() -> None:
            with httpx.Client() as client:
                while not self._stop_polling.is_set():
                    for app in list(self._apps.values()):
                        app.poll_health(client)
                    self._stop_polling.wait(HEALTH_POLL_SECONDS)

        self._poller = threading.Thread(target=loop, name="health-poller", daemon=True)
        self._poller.start()

    def stop_polling(self) -> None:
        self._stop_polling.set()
        if self._poller is not None:
            self._poller.join(timeout=HEALTH_POLL_SECONDS + 1)
            self._poller = None

    def autostart(self) -> None:
        for app_id in self.config.gateway.autostart_ids(self.ids()):
            try:
                self.start(app_id)
            except PermissionError:
                continue
            time.sleep(0.2)
