"""The gateway: console, platform API and reverse proxy in one process.

Run with `./run.sh` (or `uvicorn platform_core.main:app` from `poc-platform/`).
"""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from platform_core.config import (
    LOG_DIR,
    PLATFORM_DIR,
    STATE_DIR,
    Principal,
    default_config_path,
    load_config,
)
from platform_core.identity import SESSION_COOKIE, IdentityService
from platform_core.policy import default_policy_path, load_policy
from platform_core.proxy import AppProxy
from platform_core.registry import Registry
from platform_core.supervisor import AppStatus

CONSOLE_DIR = os.path.join(PLATFORM_DIR, "console")
DOCS_DIR = os.path.join(PLATFORM_DIR, "docs")

config = load_config(default_config_path())
policy = load_policy(default_policy_path(PLATFORM_DIR))
identity = IdentityService(config.principals, config.default_principal)
registry = Registry(config, policy, PLATFORM_DIR)
proxy = AppProxy(identity, config.gateway.proxy_timeout_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    os.makedirs(LOG_DIR, exist_ok=True)
    registry.start_polling()
    registry.autostart()
    try:
        yield
    finally:
        registry.stop_polling()
        registry.stop_all()
        await proxy.aclose()


app = FastAPI(title="POC Platform", lifespan=lifespan)


def current_principal(request: Request) -> Principal:
    """The persona selected in the console, from its cookie."""
    return identity.get(request.cookies.get(SESSION_COOKIE))


class SessionRequest(BaseModel):
    email: str


class PrincipalView(BaseModel):
    email: str
    display_name: str
    title: str
    platform_role: str
    app_roles: dict[str, str]


def _principal_view(principal: Principal) -> PrincipalView:
    return PrincipalView(**principal.model_dump())


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"status": "ok", "service": "poc-platform", "apps": len(registry.ids())}


@app.get("/api/platform/overview")
def overview(principal: Principal = Depends(current_principal)) -> dict[str, Any]:
    """Everything the console renders: apps, personas, guardrails, problems."""
    manifests = registry.manifests
    return {
        "environment": policy.environment,
        "state_dir": os.path.relpath(STATE_DIR, PLATFORM_DIR),
        "current_principal": _principal_view(principal),
        "principals": [_principal_view(p) for p in identity.principals],
        "apps": [
            {
                **registered.model_dump(),
                "role_for_current_principal": identity.resolve(
                    principal, registered.manifest
                ).app_role,
            }
            for registered in registry.apps()
        ],
        "policy": policy.model_dump(),
        "problems": [error.model_dump() for error in registry.errors]
        + [{"path": "platform.yaml", "error": problem} for problem in identity.unknown_roles(manifests)],
        "docs": _docs_index(),
    }


@app.post("/api/platform/session")
def set_session(payload: SessionRequest, response: Response) -> PrincipalView:
    """Switch persona for every prototype at once (mocked SSO)."""
    if not identity.knows(payload.email):
        raise HTTPException(status_code=400, detail=f"unknown principal {payload.email}")
    response.set_cookie(SESSION_COOKIE, payload.email, httponly=False, samesite="lax")
    return _principal_view(identity.get(payload.email))


@app.get("/api/platform/apps")
def list_apps() -> list[dict[str, Any]]:
    return [registered.model_dump() for registered in registry.apps()]


def _app_or_404(app_id: str):
    managed = registry.get(app_id)
    if managed is None:
        raise HTTPException(status_code=404, detail=f"unknown app {app_id}")
    return managed


@app.post("/api/platform/apps/{app_id}/start")
def start_app(app_id: str) -> AppStatus:
    _app_or_404(app_id)
    try:
        return registry.start(app_id)
    except PermissionError as exc:
        # Policy violations are a platform decision, not a transient failure.
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/platform/apps/{app_id}/stop")
def stop_app(app_id: str) -> AppStatus:
    _app_or_404(app_id)
    return registry.stop(app_id)


@app.post("/api/platform/apps/{app_id}/restart")
def restart_app(app_id: str) -> AppStatus:
    _app_or_404(app_id)
    registry.stop(app_id)
    try:
        return registry.start(app_id)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/platform/apps/{app_id}/logs", response_class=PlainTextResponse)
def app_logs(app_id: str) -> str:
    return _app_or_404(app_id).tail_log() or "(no output yet)"


@app.post("/api/platform/reload")
def reload_registry() -> dict[str, Any]:
    """Rescan `poc.yaml` files without restarting the gateway."""
    registry.reload()
    return {"apps": registry.ids(), "problems": [e.model_dump() for e in registry.errors]}


# Reading order in the console; anything else follows, alphabetically.
DOC_ORDER = [
    "poc-environment",
    "poc-architecture",
    "platform-contract",
    "target-architecture",
    "roadmap",
    "graduating-a-poc",
]


def _doc_rank(filename: str) -> tuple[int, str]:
    slug = filename[:-3]
    return (DOC_ORDER.index(slug) if slug in DOC_ORDER else len(DOC_ORDER), slug)


def _docs_index() -> list[dict[str, str]]:
    if not os.path.isdir(DOCS_DIR):
        return []
    docs = []
    # README.md is the folder's index on GitHub; the console has its own tabs.
    for filename in sorted(os.listdir(DOCS_DIR), key=_doc_rank):
        if not filename.endswith(".md") or filename == "README.md":
            continue
        with open(os.path.join(DOCS_DIR, filename), "r", encoding="utf-8") as handle:
            first_line = handle.readline().strip()
        docs.append(
            {
                "slug": filename[:-3],
                "title": first_line.lstrip("# ").strip() or filename,
            }
        )
    return docs


@app.get("/api/platform/docs/{slug}", response_class=PlainTextResponse)
def read_doc(slug: str) -> str:
    path = os.path.join(DOCS_DIR, f"{slug}.md")
    # `slug` reaches the filesystem, so keep it inside the docs directory.
    if not os.path.normpath(path).startswith(DOCS_DIR) or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"unknown doc {slug}")
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


@app.api_route(
    "/apps/{app_id}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
@app.api_route(
    "/apps/{app_id}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
async def proxy_to_app(
    app_id: str,
    request: Request,
    path: str = "",
    principal: Principal = Depends(current_principal),
) -> Response:
    """Forward everything under an app's mount point to that app."""
    managed = registry.get(app_id)
    if managed is None:
        return JSONResponse(status_code=404, content={"error": "unknown_app", "app": app_id})
    return await proxy.forward(request, managed, principal, path)


@app.get("/", include_in_schema=False)
def console() -> FileResponse:
    return FileResponse(os.path.join(CONSOLE_DIR, "index.html"))


app.mount("/console", StaticFiles(directory=CONSOLE_DIR), name="console")
# Images referenced by the docs, which the console renders inline.
app.mount("/docs", StaticFiles(directory=DOCS_DIR), name="docs")


def gateway_url(host: Optional[str] = None) -> str:
    return f"http://{host or config.gateway.host}:{config.gateway.port}"
