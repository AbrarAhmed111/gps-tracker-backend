import os
from datetime import datetime, timezone
from fastapi import APIRouter
from config import API_VERSION


router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": API_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/version")
async def version():
    return {
        "version": API_VERSION,
        "build_date": os.getenv("BUILD_DATE", ""),
        "api_prefix": "/api/v1",
        "documentation_url": "/docs",
    }

