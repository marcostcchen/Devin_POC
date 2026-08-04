"""Application entrypoint: wiring, error handling and serving the panel.

Run with `./run.sh` (or `uvicorn app.main:app`).
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR
from app.db import init_db
from app.errors import DomainError
from app.routers import audit, evaluation, flags, identity
from app.seed import seed_if_empty

INDEX_FILE = os.path.join(STATIC_DIR, "index.html")


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


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    """Readiness probe, polled by whatever is running the app."""
    return {"status": "ok", "app": "feature-flag-admin"}


@app.get("/", include_in_schema=False)
def index() -> Response:
    """Serve the panel."""
    return FileResponse(INDEX_FILE)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
