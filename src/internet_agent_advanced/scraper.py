from __future__ import annotations

# Note: redis dependency is optional for tests; we guard its import.
import urllib.parse

from .rate_limit_local import limiter_for_host
from .robots import is_allowed

# optional redis-based rate limiting (may be unavailable in tests)
try:
    from .rate_limit_redis import acquire as redis_acquire
except Exception:

    def redis_acquire(url: str):
        return None


from .schemas import PageContent
from .scraper_http import fetch_httpx
from .scraper_playwright import fetch_playwright

# Optional consent & session modules (overlay)
try:
    from .consent.middleware import require
except Exception:

    def require(scope, target):
        return True


try:
    from .session.session_manager import get_storage_state_for_url
except Exception:

    def get_storage_state_for_url(url):
        return None


async def fetch(url: str, render_js: bool = False) -> PageContent:
    allowed = await is_allowed(url)
    if not allowed:
        return PageContent(
            url=url,
            status=0,
            content=None,
            fetched_at=0.0,
            blocked=True,
            error="Disallowed by robots.txt",
        )
    host = urllib.parse.urlsplit(url).netloc
    if redis_acquire:
        redis_acquire(url)
    lim = limiter_for_host(host)
    async with lim:
        if render_js:
            require("render_js", url)
            storage = get_storage_state_for_url(url)
            return await fetch_playwright(url, storage_state_path=storage)
        else:
            require("fetch_http", url)
            return await fetch_httpx(url)
