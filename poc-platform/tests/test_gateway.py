"""The gateway: console API, and the proxy in front of a stub prototype."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from platform_core.config import Principal
from platform_core.identity import IdentityService
from platform_core.main import app as gateway_app
from platform_core.proxy import AppProxy
from platform_core.supervisor import AppState, AppStatus, ManagedApp


class _Echo(BaseHTTPRequestHandler):
    """Reports back what the prototype actually received."""

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path.endswith("/redirect"):
            self.send_response(302)
            self.send_header("Location", "/somewhere-else")
            self.end_headers()
            return
        body = json.dumps(
            {"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # keep pytest output clean
        pass


@pytest.fixture()
def upstream():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Echo)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


@pytest.fixture()
def proxy_client(upstream, manifest):
    """A one-route app that proxies to the stub as if it were a running POC."""
    manifest.runtime.port = upstream.server_address[1]

    class _RunningApp(ManagedApp):
        def status(self) -> AppStatus:
            return AppStatus(
                id=self.manifest.id,
                state=AppState.RUNNING,
                port=self.manifest.runtime.port,
                log_file=self.log_file,
            )

    principal = Principal(
        email="ada@example.com",
        display_name="Ada Lovelace",
        platform_role="platform_admin",
        app_roles={manifest.id: "admin"},
    )
    identity = IdentityService([principal], principal.email)
    proxy = AppProxy(identity, timeout=5)
    managed = _RunningApp(manifest, ".", "http://127.0.0.1:8080")

    api = FastAPI()

    @api.api_route("/apps/{app_id}/{path:path}", methods=["GET"])
    async def _forward(app_id: str, path: str, request: Request):
        return await proxy.forward(request, managed, principal, path)

    with TestClient(api) as client:
        yield client


def test_mount_prefix_and_query_reach_the_app_unchanged(proxy_client):
    # The app knows its prefix (root_path / express mount), so it is forwarded
    # rather than stripped - see docs/platform-contract.md.
    payload = proxy_client.get("/apps/example-poc/api/flags?limit=2").json()
    assert payload["path"] == "/apps/example-poc/api/flags?limit=2"


def test_identity_headers_are_injected(proxy_client):
    headers = proxy_client.get("/apps/example-poc/api/me").json()["headers"]
    assert headers["x-platform-user"] == "ada@example.com"
    assert headers["x-platform-role"] == "admin"
    assert headers["x-platform-base-path"] == "/apps/example-poc"


def test_client_supplied_identity_headers_are_overwritten(proxy_client):
    headers = proxy_client.get(
        "/apps/example-poc/api/me",
        headers={"X-Platform-User": "attacker@example.com", "X-Platform-Role": "admin"},
    ).json()["headers"]
    assert headers["x-platform-user"] == "ada@example.com"


def test_upstream_redirects_stay_inside_the_mount_point(proxy_client):
    response = proxy_client.get("/apps/example-poc/redirect", follow_redirects=False)
    assert response.headers["location"] == "/apps/example-poc/somewhere-else"


@pytest.fixture(scope="module")
def console():
    with TestClient(gateway_app) as client:
        yield client


def test_gateway_is_healthy(console):
    assert console.get("/healthz").json()["status"] == "ok"


def test_overview_lists_every_prototype_without_configuration_problems(console):
    overview = console.get("/api/platform/overview").json()
    assert {app["manifest"]["id"] for app in overview["apps"]} >= {
        "feature-flag-admin",
        "kyc-review-queue",
        "refunds-dashboard",
    }
    assert overview["problems"] == []
    assert all(app["violations"] == [] for app in overview["apps"])
    # The console links to this; it is derived, so it is not inside "manifest".
    assert all(
        app["base_path"] == f"/apps/{app['manifest']['id']}" for app in overview["apps"]
    )


def test_switching_persona_changes_the_role_reported_per_app(console):
    console.post("/api/platform/session", json={"email": "nora@example.com"})
    roles = {
        app["manifest"]["id"]: app["role_for_current_principal"]
        for app in console.get("/api/platform/overview").json()["apps"]
    }
    assert roles["kyc-review-queue"] == "analyst"
    assert roles["feature-flag-admin"] == "viewer"

    console.post("/api/platform/session", json={"email": "ada@example.com"})
    roles = {
        app["manifest"]["id"]: app["role_for_current_principal"]
        for app in console.get("/api/platform/overview").json()["apps"]
    }
    assert roles["kyc-review-queue"] == "senior_reviewer"
    assert roles["feature-flag-admin"] == "admin"


def test_unknown_persona_is_rejected(console):
    assert console.post("/api/platform/session", json={"email": "ghost@example.com"}).status_code == 400


def test_stopped_prototype_answers_with_an_explanation(console):
    response = console.get("/apps/kyc-review-queue/api/cases")
    assert response.status_code == 503
    assert response.json()["error"] == "app_not_running"


def test_unknown_prototype_is_a_404(console):
    assert console.get("/apps/nope/").status_code == 404


def test_docs_are_served_to_the_console(console):
    slugs = [doc["slug"] for doc in console.get("/api/platform/overview").json()["docs"]]
    assert {"poc-environment", "platform-contract", "target-architecture", "roadmap"} <= set(slugs)
    assert console.get("/api/platform/docs/poc-environment").text.startswith("#")


def test_doc_images_are_served(console):
    response = console.get("/docs/images/target-architecture.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_docs_endpoint_refuses_to_escape_the_docs_directory(console):
    assert console.get("/api/platform/docs/../platform").status_code in (404, 400)
