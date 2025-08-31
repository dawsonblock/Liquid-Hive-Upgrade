from __future__ import annotations

import asyncio
import time
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
import yaml
from fastapi import APIRouter, HTTPException, Request
from prometheus_client import Counter
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from prometheus_client import make_asgi_app

# Load permissions
import pathlib

CONFIG_PATH = pathlib.Path(__file__).resolve().parent / "config" / "permissions.yaml"
DEFAULT_PERMISSIONS = {
    "render_js": {"require_consent": True},
    "ingest_index": {"require_consent": True},
    "large_download": {"require_consent": True},
    "captcha_bypass": {"allowed": False},
    "robots_override": {"allowed": False},
}
try:
    with open(CONFIG_PATH, "r") as f:
        PERMS = yaml.safe_load(f) or DEFAULT_PERMISSIONS
except Exception:
    PERMS = DEFAULT_PERMISSIONS

# Simple in-memory consent/session store
_CONSENTS: Dict[str, Dict[str, float]] = {}

# Metrics
FETCH_COUNT = Counter(
    "ia_fetch_requests_total",
    "Total internet fetch requests",
    ["domain", "render_js", "status"],
)
INGEST_COUNT = Counter(
    "ia_ingest_requests_total",
    "Total internet ingest requests",
    ["domain", "render_js", "status"],
)

router = APIRouter(prefix="/tools", tags=["internet-agent-advanced"])
metrics_app = make_asgi_app()

test_router = APIRouter(prefix="/test", tags=["internet-agent-test"])


def _now() -> float:
    return time.time()


def _domain_of(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _has_consent(scope: str, domain: str) -> bool:
    if not domain:
        return False
    entry = _CONSENTS.get(domain, {})
    exp = entry.get(scope)
    return bool(exp and exp > _now())


@router.post("/consent/request")
async def consent_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    scope = str(payload.get("scope", "")).strip()
    target = str(payload.get("target", "")).strip()
    ttl = int(payload.get("ttl", 600))
    if not scope or not target:
        raise HTTPException(status_code=400, detail="invalid_scope_or_target")
    # We don't auto-approve; just acknowledge request
    return {"requested": True, "scope": scope, "target": target, "ttl": ttl}


@router.post("/consent/approve")
async def consent_approve(payload: Dict[str, Any]) -> Dict[str, Any]:
    scope = str(payload.get("scope", "")).strip()
    target = str(payload.get("target", "")).strip()
    ttl = int(payload.get("ttl", 600))
    if not scope or not target:
        raise HTTPException(status_code=400, detail="invalid_scope_or_target")
    exp = _now() + max(1, ttl)
    _CONSENTS.setdefault(target, {})[scope] = exp
    return {"approved": True, "scope": scope, "target": target, "expires_at": int(exp)}


@router.post("/consent/clear_session")
async def consent_clear(payload: Dict[str, Any]) -> Dict[str, Any]:
    domain = str(payload.get("domain", "")).strip()
    if not domain:
        raise HTTPException(status_code=400, detail="invalid_domain")
    _CONSENTS.pop(domain, None)
    return {"cleared": True, "domain": domain}


@router.post("/internet_fetch")
async def internet_fetch(payload: Dict[str, Any]) -> Dict[str, Any]:
    urls: List[str] = payload.get("urls") or []
    render_js: bool = bool(payload.get("render_js", False))

    if render_js and PERMS.get("render_js", {}).get("require_consent", True):
        # ensure all target domains have consent
        for u in urls:
            dom = _domain_of(u)
            if not _has_consent("render_js", dom):
                raise HTTPException(status_code=403, detail="consent_required")

    trusted: List[Dict[str, Any]] = []
    unverified: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for url in urls:
            dom = _domain_of(url)
            status_label = "error"
            try:
                # Socket sanity to avoid obvious non-routable targets
                if dom:
                    try:
                        socket.getaddrinfo(dom, 80, proto=socket.IPPROTO_TCP)
                    except Exception:
                        raise HTTPException(status_code=502, detail="dns_resolution_failed")
                r = await client.get(url)
                status = r.status_code
                data = {
                    "url": url,
                    "status_code": status,
                    "content_snippet": r.text[:500],
                }
                if 200 <= status < 400:
                    # Simple heuristic: https domains count as trusted; else unverified
                    bucket = trusted if urlparse(url).scheme == "https" else unverified
                    bucket.append(data)
                    status_label = "ok"
                else:
                    unverified.append(data)
                    status_label = "bad_status"
            except HTTPException as he:
                errors.append({"url": url, "error": he.detail})
            except Exception as e:
                errors.append({"url": url, "error": str(e)})
            finally:
                FETCH_COUNT.labels(dom or "", str(render_js).lower(), status_label).inc()

    return {"trusted": trusted, "unverified": unverified, "errors": errors}


@router.post("/internet_ingest")
async def internet_ingest(payload: Dict[str, Any]) -> Dict[str, Any]:
    url: str = payload.get("url") or ""
    render_js: bool = bool(payload.get("render_js", False))

    if not url:
        raise HTTPException(status_code=400, detail="missing_url")

    dom = _domain_of(url)
    if render_js and PERMS.get("ingest_index", {}).get("require_consent", True):
        if not _has_consent("render_js", dom):
            raise HTTPException(status_code=403, detail="consent_required")

    chunks = 0
    status_label = "error"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code == 200:
                text = r.text
                # naive chunking by paragraphs
                chunks = max(1, len([p for p in text.split("\n\n") if p.strip()]))
                status_label = "ok"
            else:
                status_label = "bad_status"
    except Exception:
        status_label = "error"
    finally:
        INGEST_COUNT.labels(dom or "", str(render_js).lower(), status_label).inc()

    return {"url": url, "chunks_count": chunks}


@test_router.get("/challenge")
async def test_challenge() -> Dict[str, Any]:
    return {
        "challenge_status": "challenge_detected",
        "captcha_required": True,
        "blocked": True,
    }