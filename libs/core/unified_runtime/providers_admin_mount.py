from __future__ import annotations

from fastapi import FastAPI


def mount_admin_providers(app: FastAPI) -> None:
    # Only mount when explicitly allowed
    try:
        from .admin_providers import router as admin_router
    except Exception:
        admin_router = None  # type: ignore

    if not admin_router:
        return
    # Endpoint path lives at /api/admin/* per router prefix
    already = any(getattr(r, "prefix", "").startswith("/api/admin") for r in app.router.routes)
    if not already:
        app.include_router(admin_router)
