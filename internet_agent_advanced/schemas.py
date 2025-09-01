from __future__ import annotations
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class PageContent(BaseModel):
    url: str
    status: int
    title: Optional[str] = None
    mime: Optional[str] = None
    content: Optional[str] = None
    content_html: Optional[str] = None
    screenshot_png: Optional[bytes] = None
    network_payloads: List[Dict[str,Any]] = Field(default_factory=list)
    fetched_at: float
    captcha_required: bool = False
    blocked: bool = False
    headers: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    rendered: bool = False
    elapsed_ms: Optional[int] = None
    # NEW:
    challenge_status: Optional[str] = None  # one of: "none","challenge_detected","blocked"
