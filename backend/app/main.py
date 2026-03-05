"""
FastAPI Application Entry Point
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logger import setup_logger
from app.services.ai.bootstrap import register_builtin_models
from app.services.ai.store import ensure_ai_models, restore_active_model


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Initialize database tables
    try:
        from app.core.database import init_db
        await init_db()
        logger.info("Database initialized successfully")

        await register_builtin_models()
        from app.core.database import async_session_maker
        async with async_session_maker() as session:
            await ensure_ai_models(session)
            await restore_active_model(session)
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")
    # Close database connections
    from app.core.database import close_db
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Enterprise-level image rating API server",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix="/api")

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> JSONResponse:
        return JSONResponse(
            content={
                "status": "healthy",
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
            }
        )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return app


# Setup logger
setup_logger()

# Create application instance
app = create_app()
