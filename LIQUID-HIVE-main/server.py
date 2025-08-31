"""
Main server entry point for LIQUID-HIVE system.
This file serves as an adapter to maintain compatibility with supervisor configuration.
"""

from unified_runtime.server import app

# Export the app so uvicorn can find it
__all__ = ["app"]