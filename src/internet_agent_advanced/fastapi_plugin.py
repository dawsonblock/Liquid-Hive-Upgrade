from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .main_tool import internet_fetch, internet_ingest, internet_search
from .metrics import metrics_app

router = APIRouter(prefix="/tools", tags=["tools"])


class FetchReq(BaseModel):
    urls: list[str] = Field(default_factory=list)
    render_js: bool = False


class SearchReq(BaseModel):
    query: str
    max_results: int = 5


class IngestReq(BaseModel):
    url: str
    render_js: bool = False


# === Consent add-ons ===
try:
    from .consent.middleware import CONSENT
except Exception:
    CONSENT = None


class ConsentReq(BaseModel):
    scope: str
    target: str
    ttl: int | None = None


@router.post("/consent/request")
async def api_consent_request(req: ConsentReq) -> dict[str, Any]:
    # Agent/UI should display this to user; back-end just acknowledges.
    return {"ok": True, "pending": True, "scope": req.scope, "target": req.target}


@router.post("/consent/approve")
async def api_consent_approve(req: ConsentReq) -> dict[str, Any]:
    if not CONSENT:
        raise HTTPException(status_code=400, detail="Consent manager not installed")
    return CONSENT.approve(req.scope, req.target, ttl=req.ttl)


@router.post("/consent/revoke")
async def api_consent_revoke(req: ConsentReq) -> dict[str, Any]:
    if not CONSENT:
        raise HTTPException(status_code=400, detail="Consent manager not installed")
    return CONSENT.revoke(req.scope, req.target)


# Session upload/clear
try:
    from .session.session_manager import clear_storage_state, save_storage_state
except Exception:
    save_storage_state = clear_storage_state = None


class SessionUpload(BaseModel):
    domain: str
    storage_state: Any  # dict or string


@router.post("/consent/upload_session")
async def api_upload_session(req: SessionUpload) -> dict[str, Any]:
    if not save_storage_state:
        raise HTTPException(status_code=400, detail="Session manager not installed")
    path = save_storage_state(req.domain, req.storage_state)
    return {"ok": True, "domain": req.domain, "path": path}


class SessionClear(BaseModel):
    domain: str


@router.post("/consent/clear_session")
async def api_clear_session(req: SessionClear) -> dict[str, Any]:
    if not clear_storage_state:
        raise HTTPException(status_code=400, detail="Session manager not installed")
    ok = clear_storage_state(req.domain)
    return {"ok": ok, "domain": req.domain}


# === Tools ===
@router.post("/internet_fetch")
async def api_internet_fetch(req: FetchReq) -> dict[str, Any]:
    try:
        res = await internet_fetch(req.urls, render_js=req.render_js)
        return res.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/internet_search")
async def api_internet_search(req: SearchReq) -> dict[str, Any]:
    try:
        res = await internet_search(req.query, max_results=req.max_results)
        return res.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/internet_ingest")
async def api_internet_ingest(req: IngestReq) -> dict[str, Any]:
    try:
        return await internet_ingest(req.url, render_js=req.render_js)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Test harness endpoints ===
test_router = APIRouter(prefix="/test", tags=["test"])


@test_router.get("/challenge")
async def test_challenge():
    html = """
    <html><head><title>Bot Check</title></head>
    <body>
      <h1>Are you human?</h1>
      <p>This page intentionally contains keywords like CAPTCHA and bot detection.</p>
    </body></html>
    """
    return html


@test_router.get("/ok")
async def test_ok():
    html = """<html><head><title>OK</title></head><body><p>Normal content.</p></body></html>"""
    return html


# expose metrics under /metrics via mount from app
metrics_app = metrics_app
