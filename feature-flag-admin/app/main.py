"""Application entrypoint: wiring, error handling and serving the React build.

Run with `./run.sh` (or `uvicorn app.main:app`).
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.config import WEB_DIST_DIR
from app.db import init_db
from app.errors import DomainError
from app.routers import audit, evaluation, flags, identity
from app.seed import seed_if_empty

INDEX_FILE = os.path.join(WEB_DIST_DIR, "index.html")
BUILD_MISSING = "Frontend not built. Run ./run.sh, or `npm install && npm run build` in web/."


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    seed_if_empty()
    yield


app = FastAPI(title="Feature Flag Admin", lifespan=lifespan)

for module in (identity, flags, audit, evaluation):
    app.include_router(module.router)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    """Render domain errors like FastAPI's own `HTTPException` responses."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/", include_in_schema=False)
def index() -> Response:
    """Serve the React single-page app."""
    if not os.path.exists(INDEX_FILE):
        return PlainTextResponse(BUILD_MISSING, status_code=503)
    return FileResponse(INDEX_FILE)


if os.path.isdir(os.path.join(WEB_DIST_DIR, "assets")):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(WEB_DIST_DIR, "assets")),
        name="assets",
    )
