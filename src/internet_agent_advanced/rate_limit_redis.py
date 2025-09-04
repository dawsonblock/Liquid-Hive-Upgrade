from __future__ import annotations

import time
import urllib.parse

import redis

from .config import PACE_RPS_DEFAULT, REDIS_URL

_r = redis.Redis.from_url(REDIS_URL) if REDIS_URL else None


def acquire(url: str, rps: float | None = None):
    if not _r:
        return  # no-op if Redis not configured
    host = urllib.parse.urlsplit(url).netloc
    rate = rps or PACE_RPS_DEFAULT
    period = 1.0 / max(rate, 0.001)
    key = f"pace:{host}"
    while True:
        now = time.time()
        last = _r.get(key)
        last_t = float(last) if last else 0.0
        wait = max(0.0, last_t + period - now)
        if wait > 0:
            time.sleep(min(wait, 2.0))
            continue
        pipe = _r.pipeline()
        pipe.set(key, now)
        try:
            pipe.execute()
            return
        except Exception:
            time.sleep(0.05)
