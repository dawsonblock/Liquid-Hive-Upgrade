from __future__ import annotations
import os, yaml, urllib.parse
from .manager import ConsentManager
from ..config import DEFAULT_UA
from .determinism import set_determinism


def _load_policy(path: str | None = None) -> dict:
    if not path:
        # resolve next to this overlay's config or fallback to package config if copied inside
        path = os.path.join(os.path.dirname(__file__), "..", "config", "permissions.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


_policy = _load_policy()
CONSENT = ConsentManager(_policy)


def require(scope: str, target: str):
    result = CONSENT.check(scope, target)
    if not result.get("allowed", False):
        # hard prohibitions surface as specific error
        reason = result.get("reason", "consent_required")
        raise PermissionError(reason)
    return True


def stable_headers(headers: dict | None = None) -> dict:
    # Ensure deterministic UA unless overridden
    h = {"User-Agent": DEFAULT_UA}
    if headers:
        h.update(headers)
    return h


# One shot determinism seed (call at app start)
set_determinism()
