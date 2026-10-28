"""
FastAPI Application Entry Point for ClassSnap.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from classsnap.api.v1.router import api_v1_router
from classsnap.config import get_settings
from classsnap.db.session import init_db
from classsnap.exceptions import (
    ClassSnapError,
    classsnap_exception_handler,
    generic_exception_handler,
)
from classsnap.logger import configure_logging, get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown tasks."""
    settings = get_settings()
    configure_logging(log_level=settings.log_level, json_format=(settings.app_env == "production"))
    logger.info(f"Starting {settings.app_name} (Environment: {settings.app_env}, Version: {settings.app_version})")

    # Ensure required runtime directories exist
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)

    # Initialize database tables
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}", exc_info=True)

    yield

    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    """Factory function to build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Single-Image Classroom Attendance System with Human-in-the-Loop Review.",
        docs_url="/docs" if settings.debug or settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.debug or settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    # Cross-Origin Resource Sharing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def disable_dashboard_html_cache(request, call_next):
        response = await call_next(request)
        if request.url.path == "/review/" or request.url.path == "/review":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Register Exception Handlers
    app.add_exception_handler(ClassSnapError, classsnap_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Include Versioned API Routers
    app.include_router(api_v1_router)
    app.mount(
        "/review",
        StaticFiles(directory=str(get_settings().base_dir / "classsnap" / "web" / "dist"), html=True),
        name="review",
    )

    # Root redirect / friendly health check
    @app.get("/health", include_in_schema=False)
    def root_health():
        from classsnap.api.v1.endpoints.health import get_health
        from classsnap.db.session import SessionLocal

        with SessionLocal() as db:
            return get_health(db=db)

    @app.get("/", include_in_schema=False)
    def root():
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "status": "online",
            "docs_url": "/docs",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "classsnap.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
