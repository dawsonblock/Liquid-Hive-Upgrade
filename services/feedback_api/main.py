"""FastAPI application for feedback collection service."""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog

from .router import feedback_router
from services.event_bus.bus import get_default_event_bus, shutdown_default_event_bus

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration from environment
FEEDBACK_API_HOST = os.getenv("FEEDBACK_API_HOST", "0.0.0.0")
FEEDBACK_API_PORT = int(os.getenv("FEEDBACK_API_PORT", "8091"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Feedback Collection API", port=FEEDBACK_API_PORT)
    
    # Initialize event bus
    event_bus = await get_default_event_bus()
    logger.info("Event bus initialized")
    
    # Store event bus in app state for access in routes
    app.state.event_bus = event_bus
    
    yield
    
    # Shutdown
    logger.info("Shutting down Feedback Collection API")
    await shutdown_default_event_bus()


# Create FastAPI application
app = FastAPI(
    title="Liquid Hive Feedback API",
    description="Collects user feedback and system metrics for continuous learning",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Include routers
app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["feedback"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Liquid Hive Feedback API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "collect": "/api/v1/feedback/collect",
            "metrics": "/api/v1/feedback/metrics",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check event bus health
        event_bus = app.state.event_bus
        stats = await event_bus.get_stats()
        
        return {
            "status": "healthy",
            "service": "feedback_api",
            "event_bus_status": "connected",
            "event_stats": {
                "events_published": stats.get("events_published", 0),
                "active_subscriptions": stats.get("active_subscriptions", 0)
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "feedback_api",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=FEEDBACK_API_HOST,
        port=FEEDBACK_API_PORT,
        reload=True,
        log_level="info"
    )