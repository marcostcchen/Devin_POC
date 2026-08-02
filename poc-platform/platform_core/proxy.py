"""Reverse proxy: one origin for every prototype.

`/apps/<id>/<path>` is forwarded to the prototype's local port with the mount
prefix intact, and the app is told about that prefix through
`PLATFORM_BASE_PATH` (FastAPI `root_path`, an Express mount). Keeping the prefix
is what makes the frameworks' own machinery - static file mounts, generated
docs URLs, SPA fallbacks - line up with the URLs the browser actually sees.

Identity headers are injected here, and stripped from the incoming request
first, so a browser cannot claim a persona the console did not select.
"""

import uuid
from typing import Optional

import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from platform_core.config import Principal
from platform_core.identity import MANAGED_HEADERS, IdentityService
from platform_core.supervisor import AppState, ManagedApp

#: Connection-level headers that must not be forwarded in either direction.
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}
_MANAGED_LOWER = {header.lower() for header in MANAGED_HEADERS}


def _forwardable(headers, base_url: str, base_path: str) -> dict[str, str]:
    out = {}
    for key, value in headers.items():
        lowered = key.lower()
        if lowered in HOP_BY_HOP or lowered in _MANAGED_LOWER:
            continue
        out[key] = value
    out["X-Forwarded-Prefix"] = base_path
    out["X-Forwarded-Host"] = base_url
    return out


def _rewrite_location(location: str, base_path: str) -> str:
    """Keep upstream redirects inside the app's mount point."""
    if location.startswith("/") and not location.startswith(base_path):
        return f"{base_path}{location}"
    return location


def not_running_response(app: ManagedApp, accept: str) -> Response:
    """Explain a stopped prototype instead of leaking a connection error."""
    status = app.status()
    detail = status.message or f"{app.manifest.name} is {status.state.value}"
    if "text/html" in accept:
        body = f"""<!doctype html>
<meta charset="utf-8"><title>{app.manifest.name} is not running</title>
<style>body{{font:15px/1.6 system-ui,sans-serif;margin:80px auto;max-width:44rem;color:#1c1f23}}
code{{background:#f1f3f5;padding:2px 6px;border-radius:4px}}a{{color:#1f6feb}}</style>
<h1>{app.manifest.name} is not running</h1>
<p>{detail}</p>
<p>Start it from the <a href="/">platform console</a>, or run
<code>cd {app.manifest.id} && ./run.sh</code> to run it standalone.</p>
"""
        return Response(content=body, status_code=503, media_type="text/html")
    return JSONResponse(
        status_code=503,
        content={
            "error": "app_not_running",
            "app": app.manifest.id,
            "state": status.state.value,
            "detail": detail,
        },
    )


class AppProxy:
    """Forwards requests to prototypes over a shared connection pool."""

    def __init__(self, identity: IdentityService, timeout: float) -> None:
        self._identity = identity
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def forward(
        self,
        request: Request,
        app: ManagedApp,
        principal: Principal,
        path: str,
        request_id: Optional[str] = None,
    ) -> Response:
        base_path = app.manifest.base_path
        state = app.status().state
        if state not in (AppState.RUNNING, AppState.STARTING):
            return not_running_response(app, request.headers.get("accept", ""))

        # A prototype served at its mount point resolves relative URLs against
        # the trailing slash; without it every asset would 404 one level up.
        if not path and not request.url.path.endswith("/"):
            return RedirectResponse(url=f"{base_path}/", status_code=307)

        headers = _forwardable(request.headers, str(request.base_url), base_path)
        headers.update(
            self._identity.headers_for(principal, app.manifest, request_id or uuid.uuid4().hex)
        )

        url = httpx.URL(f"{app.base_url}{base_path}/{path}")
        if request.url.query:
            url = url.copy_with(query=request.url.query.encode("utf-8"))

        try:
            upstream = await self._client.request(
                request.method,
                url,
                content=await request.body(),
                headers=headers,
            )
        except httpx.HTTPError as exc:
            if state == AppState.STARTING:
                return not_running_response(app, request.headers.get("accept", ""))
            return JSONResponse(
                status_code=502,
                content={"error": "upstream_error", "app": app.manifest.id, "detail": str(exc)},
            )

        response_headers = {
            key: value
            for key, value in upstream.headers.items()
            if key.lower() not in HOP_BY_HOP
        }
        if "location" in upstream.headers:
            response_headers["location"] = _rewrite_location(
                upstream.headers["location"], base_path
            )

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
        )
