"""Main FastAPI application for Liquid Hive API."""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from apps.api.routers.memory import memory_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Liquid Hive API...")

    yield

    # Shutdown
    logger.info("Shutting down Liquid Hive API...")


# Create FastAPI application
app = FastAPI(
    title="Liquid Hive API",
    description="Advanced AI Agent Platform API",
    version="1.0.0",
    debug=True,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Include routers
app.include_router(memory_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Liquid Hive API", "version": "1.0.0"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/healthz")
async def healthz_check() -> dict[str, str]:
    """Kubernetes-style health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/version")
async def version_info() -> dict[str, str]:
    """Version information endpoint."""
    return {
        "version": "1.0.0",
        "build_date": "2024-01-01T00:00:00Z",
        "git_commit": "unknown"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
