"""
API v1 Router - Aggregates all v1 endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import ai_analyze, auth, images, upload, users

# Create API v1 router
api_router = APIRouter(prefix="/v1", tags=["v1"])

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(images.router, prefix="/images", tags=["Images"])
api_router.include_router(ai_analyze.router, prefix="/ai", tags=["AI Analyze"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])


@api_router.get("/")
async def api_v1_root() -> dict[str, str]:
    """API v1 root endpoint."""
    return {
        "message": "Image Rating Server API v1",
        "version": "1.0.0",
        "docs": "/docs",
    }
