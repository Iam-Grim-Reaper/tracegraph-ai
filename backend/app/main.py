from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description="Backend API for TraceGraph AI",
    version="0.1.0",
    debug=settings.debug,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
        "status": "running",
    }