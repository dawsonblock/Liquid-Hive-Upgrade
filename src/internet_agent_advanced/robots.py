from __future__ import annotations

import time
import urllib.parse

import httpx
from robotexclusionrulesparser import RobotExclusionRulesParser

from .config import RESPECT_ROBOTS, ROBOTS_TTL_S

_cache: dict[str, tuple[RobotExclusionRulesParser, float]] = {}


async def is_allowed(url: str, user_agent: str = "internet_agent_advanced"):
    if not RESPECT_ROBOTS:
        return True
    parts = urllib.parse.urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    now = time.time()

    rp, ts = _cache.get(robots_url, (None, 0))
    if (not rp) or (now - ts > ROBOTS_TTL_S):
        rp = RobotExclusionRulesParser()
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(robots_url, follow_redirects=True)
                if r.status_code < 400:
                    rp.parse(r.text)
                else:
                    rp.parse("")
        except Exception:
            rp.parse("")
        _cache[robots_url] = (rp, now)
    return rp.is_allowed(user_agent, url)
