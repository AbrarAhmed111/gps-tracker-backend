"""
Backend Template API (FastAPI)
Minimal, reusable API starter for connecting with a Next.js app.
"""
import os
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from api.routers.ai import router as ai_router

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_VERSION = os.getenv("API_VERSION", "1.0.0")
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = (
    [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]
    if ALLOWED_ORIGINS_STR and ALLOWED_ORIGINS_STR != "*"
    else ["*"]
)

# Create FastAPI app
app = FastAPI(
    title="Backend Template API",
    description="A clean FastAPI template for building backend APIs.",
    version=API_VERSION,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API router (versionable)
api_router = APIRouter(prefix="/api", tags=["api"])


@app.get("/")
async def root():
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    is_railway = os.getenv("RAILWAY_ENVIRONMENT", "") != ""
    return {
        "message": "Backend Template API",
        "version": API_VERSION,
        "environment": ENVIRONMENT,
        "base_url": base_url,
        "deployment": "Railway" if is_railway else "Local",
        "docs": f"{base_url}/docs",
        "health": f"{base_url}/health",
        "example_routes": {
            "ping": f"{base_url}/api/ping",
            "echo": f"{base_url}/api/echo",
        },
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "backend-template",
        "version": API_VERSION,
        "environment": ENVIRONMENT,
    }


@api_router.get("/ping")
async def ping():
    return {"pong": True}


@api_router.post("/echo")
async def echo(payload: dict):
    return {"received": payload}


# Mount router
app.include_router(api_router)
app.include_router(ai_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True, log_level="info")
