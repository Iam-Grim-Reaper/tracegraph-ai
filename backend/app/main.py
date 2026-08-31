import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.api.routes.chat import (
    router as chat_router,
)
from app.api.routes.documents import (
    router as documents_router,
)
from app.api.routes.health import (
    router as health_router,
)
from app.core.config import settings
from app.core.config import Settings
from app.core.observability import RequestContextMiddleware, configure_logging, log_event
from app.core.lifecycle import stream_workers
from app.services.tracegraph_service import close_tracegraph_service


logger = logging.getLogger(__name__)


def create_app(app_settings: Settings = settings) -> FastAPI:
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        stream_workers.start()
        try:
            yield
        finally:
            active_worker_count = len(stream_workers.active_workers())
            log_event(
                logger,
                logging.INFO,
                "application_shutdown_started",
                operation="application_shutdown",
                status="started",
                active_worker_count=active_worker_count,
            )
            _, workers_stopped, remaining_worker_count = stream_workers.shutdown(
                app_settings.stream_shutdown_timeout_seconds
            )
            close_tracegraph_service()
            log_event(
                logger,
                logging.INFO,
                "application_shutdown_completed",
                operation="application_shutdown",
                status="complete",
                active_worker_count=active_worker_count,
                workers_stopped=workers_stopped,
                remaining_worker_count=remaining_worker_count,
            )

    application = FastAPI(
        title=app_settings.app_name,
        description="Backend API for TraceGraph AI",
        version="0.1.0",
        debug=app_settings.debug,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    application.add_middleware(RequestContextMiddleware)

    application.include_router(health_router)
    application.include_router(chat_router)
    application.include_router(documents_router)

    @application.get("/")
    async def root():
        return {
            "name": app_settings.app_name,
            "environment": app_settings.app_env,
            "status": "running",
        }

    return application


app = create_app()
