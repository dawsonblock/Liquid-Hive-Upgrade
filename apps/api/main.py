"""Main FastAPI application for Liquid Hive API."""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from src.config import get_config
from src.version import get_build_info
from apps.api.routers.memory import memory_router
from apps.api.metrics import get_metrics_response, check_and_update_component_health

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Liquid Hive API...")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Debug mode: {config.debug}")
    
    # Initialize database, Redis, etc.
    # This is where you would set up your database connections, Redis, etc.
    
    yield
    
    # Shutdown
    logger.info("Shutting down Liquid Hive API...")


# Create FastAPI application
app = FastAPI(
    title="Liquid Hive API",
    description="Advanced AI Agent Platform API",
    version=config.version,
    debug=config.debug,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if config.debug else ["localhost", "127.0.0.1"]
)

# Include routers
app.include_router(memory_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Liquid Hive API", "version": config.version}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": config.version}


@app.get("/healthz")
async def healthz_check() -> dict[str, str]:
    """Kubernetes-style health check endpoint."""
    return {"status": "healthy", "version": config.version}


@app.get("/version")
async def version_info() -> dict[str, str]:
    """Version information endpoint."""
    return get_build_info()


@app.get("/config")
async def config_info() -> dict[str, Any]:
    """Configuration information endpoint (debug only)."""
    if not config.debug:
        return {"error": "Configuration endpoint only available in debug mode"}
    
    return {
        "app": {
            "name": config.name,
            "version": config.version,
            "environment": config.environment,
            "debug": config.debug,
        },
        "api": {
            "host": config.api.host,
            "port": config.api.port,
            "workers": config.api.workers,
            "log_level": config.api.log_level,
        },
        "features": {
            "rag_enabled": config.features.rag_enabled,
            "agent_autonomy": config.features.agent_autonomy,
            "swarm_protocol": config.features.swarm_protocol,
            "safety_checks": config.features.safety_checks,
            "confidence_modeling": config.features.confidence_modeling,
        },
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    # Update component health before serving metrics
    check_and_update_component_health()
    return get_metrics_response()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        log_level=config.api.log_level.lower(),
    )