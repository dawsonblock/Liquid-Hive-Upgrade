from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx

from .config import DEFAULT_UA, HTTP_TIMEOUT_S
from .normalizer import html_to_text
from .schemas import PageContent

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def fetch_httpx(url: str, timeout: int = HTTP_TIMEOUT_S) -> PageContent:
    t0 = time.time()
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=timeout, headers=DEFAULT_HEADERS
    ) as client:
        r = await client.get(url)
        mime = (r.headers.get("Content-Type", "").split(";")[0] or "").lower()
        title, text = (None, None)
        content_html = r.text if "text/html" in mime else None
        if content_html:
            title, text = html_to_text(content_html)
        elif "application/json" in mime:
            text = r.text
        dt = int((time.time() - t0) * 1000)
        return PageContent(
            url=str(r.url),
            status=r.status_code,
            title=title,
            mime=mime,
            content=text,
            content_html=content_html,
            fetched_at=time.time(),
            captcha_required=(
                "captcha" in (r.text or "").lower()
                or "are you human" in (r.text or "").lower()
            ),
            blocked=(r.status_code in (401, 403, 429)),
            headers=dict(r.headers),
            rendered=False,
            elapsed_ms=dt,
        )
