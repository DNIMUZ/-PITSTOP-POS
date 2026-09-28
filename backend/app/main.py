"""FastAPI application factory.

Composes middleware (request IDs), CORS, exception handlers (consistent
JSON error envelopes, never raw stack traces) and all v1 routers.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import logging as app_logging
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import request_id_var
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)


class RequestIdMiddleware:
    """Associates a request_id (UUID) with every request and log line."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex[:16]
        token = request_id_var.set(request_id)
        try:
            await self.app(scope, receive, send)  # type: ignore[arg-type]
        finally:
            request_id_var.reset(token)


def _envelope(request: Request, code: str, message: str) -> dict:
    return {
        "error": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", "-"),
    }


def _attach_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(request, exc.code, exc.message),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMITED",
        }.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(request, code, str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = exc.errors()
        message = "Request validation failed."
        if details:
            first = details[0]
            loc = ".".join(str(part) for part in first.get("loc", []))
            message = f"{first.get('msg', 'invalid')} at {loc}"
        return JSONResponse(
            status_code=422,
            content=_envelope(request, "VALIDATION_ERROR", message),
        )

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=_envelope(request, "RATE_LIMITED", "Too many requests, please slow down."),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled API error",
            extra={"method": request.method, "path": request.url.path},
        )
        return JSONResponse(
            status_code=500,
            content=_envelope(
                request,
                "INTERNAL_ERROR",
                "An unexpected error occurred. Please try again later.",
            ),
        )


def create_app() -> FastAPI:
    settings = get_settings()
    app_logging.setup_logging(settings.LOG_LEVEL)

    docs = settings.EXPOSE_DOCS
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "PITSTOP POS - a production-style point-of-sale backend. "
            "Full API documentation for every v1 endpoint is available here and at /redoc."
        ),
        openapi_url="/docs/openapi.json" if docs else None,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    app.state.limiter = limiter
    _attach_handlers(app)

    from app.routers import (
        analytics,
        auth,
        categories,
        inventory,
        products,
        refunds,
        system,
        transactions,
        users,
    )

    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(categories.router)
    app.include_router(products.router)
    app.include_router(inventory.router)
    app.include_router(transactions.router)
    app.include_router(refunds.router)
    app.include_router(analytics.router)

    return app


app = create_app()
