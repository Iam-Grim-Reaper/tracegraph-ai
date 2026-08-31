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
from app.core.observability import RequestContextMiddleware, configure_logging


def create_app(app_settings: Settings = settings) -> FastAPI:
    configure_logging(app_settings.log_level)
    application = FastAPI(
        title=app_settings.app_name,
        description="Backend API for TraceGraph AI",
        version="0.1.0",
        debug=app_settings.debug,
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
