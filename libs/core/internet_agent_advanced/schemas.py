from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PageContent(BaseModel):
    url: str
    status: int
    title: str | None = None
    mime: str | None = None
    content: str | None = None
    content_html: str | None = None
    screenshot_png: bytes | None = None
    network_payloads: list[dict[str, Any]] = Field(default_factory=list)
    fetched_at: float
    captcha_required: bool = False
    blocked: bool = False
    headers: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    rendered: bool = False
    elapsed_ms: int | None = None
    # NEW:
    challenge_status: str | None = None  # one of: "none","challenge_detected","blocked"


class ScoredItem(BaseModel):
    url: str
    score: float
    title: str | None = None
    content: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class FetchResult(BaseModel):
    trusted: list[ScoredItem] = Field(default_factory=list)
    unverified: list[ScoredItem] = Field(default_factory=list)
    blocked: list[ScoredItem] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
