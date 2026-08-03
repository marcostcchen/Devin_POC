"""The platform portal: a catalog, and the mocked SSO in front of every project.

Two jobs, both of which a real deployment hands to something else:

* `GET /auth` is the subrequest every project's Ingress makes before it serves a
  request. It answers 202 plus the identity headers, or 401 to send the browser
  to the sign-in page. Replace this Deployment with oauth2-proxy in front of
  Entra ID and no project changes.
* `GET /` lists the projects, what each one demonstrates, what it fakes, and the
  role the signed-in persona holds there.

Nothing here talks to the Kubernetes API: the catalog is a JSON file rendered by
`platformctl` into a ConfigMap.
"""

import os
from typing import Optional

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import PortalConfig, Principal, load

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE_NAME = "poc_persona"

app = FastAPI(title="POC Platform Portal", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

config: PortalConfig = load()
cookie_domain = os.environ.get("PORTAL_COOKIE_DOMAIN", config.domain)


def current_principal(request: Request) -> Optional[Principal]:
    """The cookie is the whole session: no cookie is no identity, never a default.

    It is set for the parent domain, so one sign-in covers every project
    subdomain — and a browser that did not sign in inherits nothing.
    """
    email = request.cookies.get(COOKIE_NAME)
    return config.principal(email) if email else None


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"status": "ok", "app": "poc-portal", "projects": len(config.projects)}


@app.get("/auth", include_in_schema=False)
def auth(request: Request, response: Response) -> Response:
    """Ingress auth subrequest: who is this, and which groups do they hold?

    The three headers are copied onto the upstream request by the Ingress, which
    means they also overwrite anything the browser tried to send.
    """
    principal = current_principal(request)
    if principal is None:
        return Response(status_code=401)
    return Response(
        status_code=202,
        headers={
            "X-Auth-Request-Email": principal.email,
            "X-Auth-Request-User": principal.display_name,
            "X-Auth-Request-Groups": ",".join(principal.groups),
        },
    )


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_form(request: Request, rd: str = "") -> Response:
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "config": config,
            "rd": rd,
            "current": current_principal(request),
        },
    )


@app.post("/login", include_in_schema=False)
def login(email: str = Form(...), rd: str = Form(default="")) -> Response:
    if config.principal(email) is None:
        return RedirectResponse("/login", status_code=303)
    response = RedirectResponse(rd or "/", status_code=303)
    response.set_cookie(
        COOKIE_NAME, email, domain=cookie_domain or None, path="/", samesite="lax"
    )
    return response


@app.post("/logout", include_in_schema=False)
def logout() -> Response:
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(COOKIE_NAME, domain=cookie_domain or None, path="/")
    return response


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    principal = current_principal(request)
    cards = [
        {
            "project": project,
            "role": project.role_for(principal) if principal else None,
        }
        for project in config.projects
    ]
    return templates.TemplateResponse(
        request,
        "portal.html",
        {"config": config, "current": principal, "cards": cards},
    )
