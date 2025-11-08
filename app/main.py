"""Application entrypoint for pdf2tables-saas."""
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import time
from datetime import datetime
from contextvars import ContextVar
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.responses import PlainTextResponse

from . import views
from . import api
from .state import RequestRegistry
from .limits import limiter
from slowapi.middleware import SlowAPIAsyncMiddleware as SlowAPIMiddleware

logger = logging.getLogger("pdf2tables")
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class JSONLogFormatter(logging.Formatter):
    """Simple JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        data = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
        }
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        request_id = request_id_ctx.get()
        if request_id:
            data["request_id"] = request_id
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            data.update(record.extra)
        return json.dumps(data, ensure_ascii=False)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a per-request ID for observability."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        req_id = request.headers.get("x-request-id") or os.urandom(8).hex()
        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply common security headers on every response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net;"
            " style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"
            " img-src 'self' data:; connect-src 'self';",
        )
        return response


def configure_logging() -> None:
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JSONLogFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="pdf2tables-saas", version="1.0.0")
    app.state.limiter = limiter
    app.state.registry = RequestRegistry()

    origin = os.getenv("APP_ORIGIN")
    try:
        max_bytes = int(os.getenv("MAX_CONTENT_LENGTH", str(25 * 1024 * 1024)))
    except ValueError:
        max_bytes = 25 * 1024 * 1024
    max_upload_mb = max(1, max_bytes // (1024 * 1024))
    if origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[origin],
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

    if os.getenv("FORCE_HTTPS", "false").lower() == "true":
        app.add_middleware(HTTPSRedirectMiddleware)

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(SlowAPIMiddleware)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next: Callable):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        return response

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
        retry_after = exc.reset_in
        headers = {"Retry-After": str(int(retry_after))} if retry_after else {}
        return PlainTextResponse(
            "Too Many Requests",
            status_code=429,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "request_id": request_id_ctx.get()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
        logger.exception("Unhandled exception", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "request_id": request_id_ctx.get()},
        )

    app.include_router(views.router)
    app.include_router(api.router, prefix="/api")

    templates_dir = Path(__file__).parent / "templates"
    views.templates.env.globals.update(
        app_name="pdf2tables-saas",
        max_upload_mb=max_upload_mb,
        now=datetime.utcnow,
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.on_event("startup")
    async def log_startup() -> None:
        port = os.getenv("PORT", "7860")
        origin_hint = origin or f"http://{socket.gethostname()}:{port}"
        logger.info(
            "pdf2tables-saas ready",
            extra={
                "origin": origin_hint,
                "limits": "25MB per file, 30 requests/minute",
                "privacy": "Uploads stored temporarily and purged automatically.",
            },
        )

    return app


app = create_app()
