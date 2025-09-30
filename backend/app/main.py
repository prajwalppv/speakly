from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import DATA_DIR, settings
from .database import get_session, init_database
from .errors import format_http_exception, format_unhandled_exception
from .logging_config import configure_logging
from .models import User
from .routers import audio as audio_router
from .routers import sessions as sessions_router
from .routers import webhooks as webhooks_router
from .services import ensure_pj_profile

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    configure_logging()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Speakly API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_event_handlers(app)
    register_exception_handlers(app)
    register_routes(app)

    return app


def register_routes(app: FastAPI) -> None:
    app.include_router(audio_router.router)
    app.include_router(sessions_router.router)
    app.include_router(webhooks_router.router)


def register_event_handlers(app: FastAPI) -> None:
    @app.on_event("startup")
    def _startup() -> None:
        logger.info("Starting Speakly API", extra={"extra_data": {"env": settings.environment}})
        init_database()
        ensure_default_user()
        ensure_default_speakers()


async def log_request(request: Request, call_next: Callable):
    logger.debug(
        "Handling request",
        extra={"extra_data": {"method": request.method, "path": request.url.path}},
    )
    response = await call_next(request)
    logger.info(
        "Request completed",
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            }
        },
    )
    return response


def register_exception_handlers(app: FastAPI) -> None:
    app.middleware("http")(log_request)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        error = format_http_exception(exc)
        if settings.developer_mode:
            error.debug = {
                "detail": exc.detail,
                "headers": getattr(exc, "headers", None),
            }
        return JSONResponse(status_code=exc.status_code, content=error.dict())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        error = format_unhandled_exception(exc)
        if settings.developer_mode:
            error.debug = {
                "exception": exc.__class__.__name__,
                "message": str(exc),
            }
        return JSONResponse(status_code=500, content=error.dict())


def ensure_default_user() -> None:
    from .database import SessionLocal

    with SessionLocal() as db:
        user = db.query(User).filter_by(name="default").one_or_none()
        if not user:
            user = User(name="default")
            db.add(user)
            db.commit()
        logger.debug("Default user ready", extra={"extra_data": {"user_id": user.id}})


def ensure_default_speakers() -> None:
    from .database import SessionLocal

    with SessionLocal() as db:
        ensure_pj_profile(db)


app = create_app()


__all__ = ["app", "create_app"]
