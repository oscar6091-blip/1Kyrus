"""FastAPI app. Run as ONE process without --reload or extra workers:

    .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import logging
from urllib.parse import urlsplit
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import artifacts, exports, jobs, projects, runs, stages
from .config import settings
from .db import init_engine
from .errors import AppError, pydantic_fields
from .services import jobs as job_service

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_engine()
    n = job_service.recover_on_startup()
    if n:
        log.warning("marked %d active job(s) from a previous process as interrupted", n)
    yield


def _err(status: int, code: str, message: str, fields=None, retryable=False) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {
        "code": code, "message": message, "fields": fields or [], "retryable": retryable}})


def _loopback_aliases(origin: str) -> set[str]:
    """FRONTEND_ORIGIN plus its localhost/127.0.0.1 twin, so a changed web port works with either address."""
    u = urlsplit(origin)
    if u.hostname not in ("localhost", "127.0.0.1"):
        return {origin}
    port = f":{u.port}" if u.port else ""
    return {origin, f"{u.scheme}://localhost{port}", f"{u.scheme}://127.0.0.1{port}"}


def create_app() -> FastAPI:
    app = FastAPI(title="Research Workflow Course Prototype", version="1.0", lifespan=lifespan)
    origins = {"http://localhost:3000", "http://127.0.0.1:3000", *_loopback_aliases(settings.frontend_origin)}
    app.add_middleware(CORSMiddleware, allow_origins=sorted(origins), allow_methods=["*"], allow_headers=["*"],
                       expose_headers=["Content-Disposition"])

    @app.exception_handler(AppError)
    async def _app_error(_req: Request, exc: AppError):
        return JSONResponse(status_code=exc.status, content={"error": exc.to_dict()})

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError):
        return _err(422, "INVALID_PAYLOAD", "요청 형식이 올바르지 않습니다.", pydantic_fields(exc.errors()))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_req: Request, exc: StarletteHTTPException):
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        return _err(exc.status_code, code, "요청한 경로를 찾을 수 없습니다." if exc.status_code == 404 else str(exc.detail))

    @app.exception_handler(Exception)
    async def _crash(_req: Request, exc: Exception):
        log.exception("unhandled error")
        return _err(500, "INTERNAL_ERROR", "서버 내부 오류가 발생했습니다.", retryable=True)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "default_mode": settings.app_mode, "live_configured": job_service.live_available()}

    for r in (projects, stages, artifacts, jobs, runs, exports):
        app.include_router(r.router, prefix="/api")
    return app


app = create_app()
