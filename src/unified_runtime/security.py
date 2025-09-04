from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import HTTPException, Request

# Optional JWT verification using a public key file if provided
try:
    import jwt  # type: ignore
except Exception:  # PyJWT may not be installed; make this optional
    jwt = None  # type: ignore

# Optional metrics
try:
    from .metrics import bump_rate_limit  # type: ignore
except Exception:

    def bump_rate_limit(*args, **kwargs):
        return None


# Simple in-memory rate limits map as fallback (tenant -> (tokens, refill_ts))
_rate_state: dict[str, dict[str, float]] = {}


def _tenant_id_from_request(req: Request) -> str:
    # Prefer Authorization: Bearer (JWT sub), else X-API-Key, else 'anon'
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        sub = _extract_sub_from_jwt(token)
        if sub:
            return f"jwt:{sub}"
    api_key = req.headers.get("x-api-key") or req.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"
    return "anon"


def _extract_sub_from_jwt(token: str) -> Optional[str]:
    if not jwt:
        return None
    pub_path = os.getenv("API_JWT_PUBLIC_KEY_PATH")
    aud = os.getenv("API_JWT_AUDIENCE")
    if not pub_path:
        return None
    try:
        with open(pub_path, "rb") as f:
            pub = f.read()
        payload = jwt.decode(
            token,
            pub,
            algorithms=["RS256", "ES256"],
            audience=aud,
            options={"verify_aud": bool(aud)},
        )
        return str(payload.get("sub")) if payload.get("sub") else None
    except Exception:
        return None


async def auth_optional(request: Request) -> None:
    """Authentication dependency that only enforces auth when TENANCY_MODE != single.
    - TENANCY_MODE=single: allow anonymous
    - Otherwise: require either valid JWT (if configured) or X-API-Key header present
    """
    tenancy = (os.getenv("TENANCY_MODE") or "single").lower()
    if tenancy == "single":
        return

    # If JWT public key configured, try verify
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        sub = _extract_sub_from_jwt(token)
        if sub:
            return
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fallback: API key
    api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if api_key:
        return
    raise HTTPException(status_code=401, detail="Unauthorized")


async def rate_limit_dependency(request: Request) -> None:
    """Simple token-bucket RPS limiter per tenant. Uses Redis if REDIS_URL configured, else in-memory.
    Default RATE_LIMIT_RPS=10.
    """
    rps = float(os.getenv("RATE_LIMIT_RPS") or 10)
    if rps <= 0:
        return

    tenant = _tenant_id_from_request(request)

    # Redis branch
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis  # type: ignore

            r = redis.Redis.from_url(redis_url, decode_responses=True)
            key = f"lh:rl:{tenant}"
            now = time.time()
            # store: tokens, ts
            pipe = r.pipeline()
            pipe.hget(key, "tokens")
            pipe.hget(key, "ts")
            tokens_str, ts_str = pipe.execute()
            tokens = float(tokens_str or rps)
            last = float(ts_str or now)
            # refill
            tokens = min(rps, tokens + (now - last) * rps)
            if tokens < 1.0:
                r.hset(key, mapping={"tokens": tokens, "ts": now})
                bump_rate_limit(tenant, False)
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            tokens -= 1.0
            r.hset(key, mapping={"tokens": tokens, "ts": now})
            r.expire(key, 60)
            bump_rate_limit(tenant, True)
            return
        except HTTPException:
            raise
        except Exception:
            # fall back to memory on error
            pass

    # In-memory fallback
    st = _rate_state.get(tenant) or {"tokens": rps, "ts": time.time()}
    now = time.time()
    tokens = min(rps, st["tokens"] + (now - st["ts"]) * rps)
    if tokens < 1.0:
        st["tokens"], st["ts"] = tokens, now
        _rate_state[tenant] = st
        bump_rate_limit(tenant, False)
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    st["tokens"], st["ts"] = tokens - 1.0, now
    _rate_state[tenant] = st
    bump_rate_limit(tenant, True)
