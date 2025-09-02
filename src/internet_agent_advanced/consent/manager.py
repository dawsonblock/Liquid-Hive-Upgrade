from __future__ import annotations

import fnmatch
import os
import threading
import time
import urllib.parse
from typing import Any, Dict, Optional, Tuple

try:
    import redis  # optional
except Exception:
    redis = None

DEFAULT_TTL_S = int(os.getenv("CONSENT_TTL_S", "3600"))


class InMemoryStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Tuple[float, dict]] = {}

    def set(self, key: str, value: dict, ttl: int):
        with self._lock:
            self._data[key] = (time.time() + ttl, value)

    def get(self, key: str) -> Optional[dict]:
        with self._lock:
            v = self._data.get(key)
            if not v:
                return None
            exp, data = v
            if time.time() > exp:
                del self._data[key]
                return None
            return data

    def delete(self, key: str):
        with self._lock:
            self._data.pop(key, None)


def _host(url: str) -> str:
    return urllib.parse.urlsplit(url).netloc.lower()


def _redis():
    url = os.getenv("REDIS_URL")
    if not url or not redis:
        return None
    try:
        return redis.Redis.from_url(url)
    except Exception:
        return None


class ConsentManager:
    def __init__(self, policy: dict):
        self.policy = policy
        self.r = _redis()
        self.mem = InMemoryStore()

    def _key(self, scope: str, target: str) -> str:
        # target may be domain or glob; for URLs, key by host
        dom = _host(target) if "://" in target else target
        return f"consent:{scope}:{dom}"

    def get_domain_rules(self, host: str) -> dict:
        rules = {}
        for entry in self.policy.get("domains", []):
            patt = entry.get("pattern")
            if patt and fnmatch.fnmatch(host, patt):
                rules.update(entry.get("rules", {}))
        return rules

    def check(self, scope: str, target: str) -> dict:
        # Enforce never-allowed scopes
        defaults = self.policy.get("defaults", {})
        cfg = defaults.get(scope, {"require_consent": False})
        if scope in ("robots_override", "captcha_bypass"):
            allowed = cfg.get("allowed", False)
            return {
                "allowed": False,
                "reason": "prohibited_scope",
                "require_consent": True,
                "scope": scope,
            }

        host = _host(target) if "://" in target else target
        domain_over = self.get_domain_rules(host).get(scope, {})
        require = bool(
            domain_over.get("require_consent", cfg.get("require_consent", False))
        )

        key = self._key(scope, host)
        if self.r:
            v = self.r.get(key)
            if v:
                return {"allowed": True, "scope": scope, "target": host, "via": "redis"}
        else:
            v = self.mem.get(key)
            if v:
                return {
                    "allowed": True,
                    "scope": scope,
                    "target": host,
                    "via": "memory",
                }
        if require:
            return {
                "allowed": False,
                "reason": "consent_required",
                "scope": scope,
                "target": host,
            }
        return {"allowed": True, "scope": scope, "target": host, "via": "default"}

    def approve(self, scope: str, target: str, ttl: Optional[int] = None):
        ttl = ttl or DEFAULT_TTL_S
        key = self._key(scope, target)
        if self.r:
            self.r.setex(key, ttl, "1")
        else:
            self.mem.set(key, {"ok": True}, ttl)
        return {"approved": True, "scope": scope, "target": target, "ttl": ttl}

    def revoke(self, scope: str, target: str):
        key = self._key(scope, target)
        if self.r:
            self.r.delete(key)
        else:
            self.mem.delete(key)
        return {"revoked": True, "scope": scope, "target": target}
