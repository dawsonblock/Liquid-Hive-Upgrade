"""FastAPI application for Oracle decision engine service."""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog

from .router import oracle_router
from services.event_bus.bus import get_default_event_bus, shutdown_default_event_bus, EventSubscription

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
ORACLE_API_HOST = os.getenv("ORACLE_API_HOST", "0.0.0.0")
ORACLE_API_PORT = int(os.getenv("ORACLE_API_PORT", "8092"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Oracle Decision Engine", port=ORACLE_API_PORT)
    
    # Initialize event bus
    event_bus = await get_default_event_bus()
    
    # Subscribe to feedback events
    subscription = EventSubscription(
        subscriber_id="oracle_engine",
        event_types={"feedback.explicit", "feedback.implicit", "system.metric"}
    )
    subscription_id = await event_bus.subscribe(subscription)
    
    logger.info(
        "Oracle subscribed to events",
        subscription_id=subscription_id,
        event_types=list(subscription.event_types)
    )
    
    # Store in app state for access in routes
    app.state.event_bus = event_bus
    app.state.subscription_id = subscription_id
    
    yield
    
    # Shutdown
    logger.info("Shutting down Oracle Decision Engine")
    
    # Unsubscribe from events
    if hasattr(app.state, 'subscription_id'):
        await event_bus.unsubscribe(app.state.subscription_id)
    
    await shutdown_default_event_bus()


# Create FastAPI application
app = FastAPI(
    title="Liquid Hive Oracle API",
    description="AI-driven decision engine for system optimization and continuous learning",
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
app.include_router(oracle_router, prefix="/api/v1/oracle", tags=["oracle"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Liquid Hive Oracle API",
        "version": "1.0.0",
        "status": "running",
        "description": "AI-driven decision engine for continuous system optimization",
        "capabilities": [
            "Feedback pattern analysis",
            "Mutation plan generation", 
            "Safety validation",
            "Automated system optimization"
        ],
        "endpoints": {
            "analyze": "/api/v1/oracle/analyze",
            "plan": "/api/v1/oracle/plan",
            "execute": "/api/v1/oracle/execute",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check event bus health and subscription status
        event_bus = app.state.event_bus
        stats = await event_bus.get_stats()
        
        return {
            "status": "healthy",
            "service": "oracle_api",
            "event_bus_status": "connected",
            "subscription_active": hasattr(app.state, 'subscription_id'),
            "event_stats": {
                "events_published": stats.get("events_published", 0),
                "events_delivered": stats.get("events_delivered", 0),
                "active_subscriptions": stats.get("active_subscriptions", 0)
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "oracle_api",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=ORACLE_API_HOST,
        port=ORACLE_API_PORT,
        reload=True,
        log_level="info"
    )