from __future__ import annotations
from aiolimiter import AsyncLimiter

_limiters: dict[str, AsyncLimiter] = {}


def limiter_for_host(host: str, rps: int = 5) -> AsyncLimiter:
    if host not in _limiters:
        _limiters[host] = AsyncLimiter(rps, 1)
    return _limiters[host]
