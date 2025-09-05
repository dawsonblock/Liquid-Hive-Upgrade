from __future__ import annotations

import hashlib

try:
    from prometheus_client import Counter, Gauge  # type: ignore
except Exception:  # pragma: no cover
    Counter = None  # type: ignore
    Gauge = None  # type: ignore

if Counter is not None:
    RATE_LIMIT_ALLOWED = Counter(
        "cb_rate_limit_allowed_total", "Rate limit allowed", labelnames=("tenant",)
    )
    RATE_LIMIT_DENIED = Counter(
        "cb_rate_limit_denied_total", "Rate limit denied", labelnames=("tenant",)
    )
    BUDGET_TOKENS = Counter(
        "cb_budget_tokens_total", "Budget tokens recorded", labelnames=("tenant",)
    )
    BUDGET_USD = Counter("cb_budget_usd_total", "Budget USD recorded", labelnames=("tenant",))
    BUDGET_EXCEEDED = Gauge(
        "cb_budget_exceeded", "Budget exceeded flag (1=yes)", labelnames=("tenant",)
    )
else:  # pragma: no cover
    RATE_LIMIT_ALLOWED = RATE_LIMIT_DENIED = BUDGET_TOKENS = BUDGET_USD = BUDGET_EXCEEDED = None  # type: ignore


def _tenant_label(tenant: str | None) -> str:
    t = tenant or "global"
    try:
        h = hashlib.sha256(t.encode()).hexdigest()[:8]
        return f"t-{h}"
    except Exception:
        return "t-unknown"


def bump_rate_limit(tenant: str | None, allowed: bool) -> None:
    if Counter is None:
        return
    lab = _tenant_label(tenant)
    try:
        if allowed:
            RATE_LIMIT_ALLOWED.labels(tenant=lab).inc()
        else:
            RATE_LIMIT_DENIED.labels(tenant=lab).inc()
    except Exception:
        pass


def record_budget_usage(tokens: int, cost_usd: float, tenant: str | None) -> None:
    if Counter is None:
        return
    lab = _tenant_label(tenant)
    try:
        BUDGET_TOKENS.labels(tenant=lab).inc(max(0, int(tokens)))
        BUDGET_USD.labels(tenant=lab).inc(max(0.0, float(cost_usd)))
    except Exception:
        pass


def set_budget_exceeded(tenant: str | None, exceeded: bool) -> None:
    if Gauge is None:
        return
    lab = _tenant_label(tenant)
    try:
        BUDGET_EXCEEDED.labels(tenant=lab).set(1.0 if exceeded else 0.0)
    except Exception:
        pass
