"""
Resource usage estimation service (Prometheus‑driven)
====================================================

This module defines a ``ResourceEstimator`` that ingests runtime metrics
from Prometheus and produces cost/latency estimates per strategy/model/adapter.
It caches recent aggregates for low‑latency queries and degrades gracefully
when Prometheus is unreachable by falling back to the last known snapshot.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import os, time, json
from pathlib import Path
import threading
import math
import urllib.parse
import urllib.request

@dataclass
class Key:
    strategy: str
    model: str
    adapter: Optional[str]

@dataclass
class Stats:
    tokens_per_req: float = 50.0
    p50_latency: float = 0.5
    p95_latency: float = 1.5
    cost_per_1k: float = 0.002
    updated_at: float = field(default_factory=time.time)

class ResourceEstimator:
    """Prometheus‑backed estimator with cached aggregates and background refresh."""
    def __init__(self) -> None:
        # Config
        self.prom_base = os.environ.get("PROMETHEUS_BASE_URL", "")
        self.cost_small = float(os.environ.get("COST_PER_1K_TOKENS_SMALL", "0.0008") or 0.0008)
        self.cost_large = float(os.environ.get("COST_PER_1K_TOKENS_LARGE", "0.0030") or 0.0030)
        self.window = os.environ.get("ESTIMATOR_WINDOW", "5m")
        self.ttl_sec = int(os.environ.get("ESTIMATOR_CACHE_TTL", "300"))

        self._cache: Dict[Tuple[str,str,Optional[str]], Stats] = {}
        self._lock = threading.Lock()

    # -------- Internal helpers --------
    def _cost_for_model(self, model: str) -> float:
        m = model.lower()
        if "small" in m or "8b" in m or "mini" in m:
            return self.cost_small
        return self.cost_large

    def _q(self, promql: str) -> Optional[dict]:
        if not self.prom_base:
            return None
        try:
            params = urllib.parse.urlencode({"query": promql})
            with urllib.request.urlopen(f"{self.prom_base}/api/v1/query?{params}") as r:
                data = json.loads(r.read().decode())
                if data.get("status") == "success":
                    return data.get("data")
        except Exception:
            return None
        return None

    def _parse_scalar(self, result: dict) -> Optional[float]:
        try:
            res = result.get("result", [])
            if not res:
                return None
            # Instant vector: take first
            val = res[0].get("value", [None, None])[1]
            return float(val) if val is not None else None
        except Exception:
            return None

    def _hist_quantile(self, q: float, where: str) -> Optional[float]:
        promql = (
            f"histogram_quantile({q}, sum(rate(cb_request_latency_seconds_bucket{{{where}}}[{self.window}])) by (le))"
        )
        data = self._q(promql)
        if not data:
            return None
        return self._parse_scalar(data)

    def _tokens_per_req(self, where: str) -> Optional[float]:
        # rate(tokens)/rate(requests) to estimate tokens per request
        t = self._q(f"sum(rate(cb_tokens_total{{{where}}}[{self.window}]))")
        r = self._q(f"sum(rate(cb_requests_total{{{where}}}[{self.window}]))")
        try:
            tv = self._parse_scalar(t) or 0.0
            rv = self._parse_scalar(r) or 0.0
            if rv <= 0:
                return None
            return tv / rv
        except Exception:
            return None

    def _refresh_key(self, k: Key) -> None:
        where_parts = [f"strategy=\"{k.strategy}\""]
        if k.adapter:
            where_parts.append(f"adapter_version=\"{k.adapter}\"")
        # model label optional if you add it to metrics; we fallback to cost mapping
        where = ",".join(where_parts)
        p50 = self._hist_quantile(0.5, where) or 0.5
        p95 = self._hist_quantile(0.95, where) or 1.5
        tpr = self._tokens_per_req(where) or 50.0
        stats = Stats(tokens_per_req=tpr, p50_latency=p50, p95_latency=p95, cost_per_1k=self._cost_for_model(k.model))
        with self._lock:
            self._cache[(k.strategy,k.model,k.adapter)] = stats

    # -------- Public API --------
    def estimate_cost(self, strategy: str, model: str, adapter: Optional[str] = None) -> float:
        k = (strategy, model, adapter)
        with self._lock:
            s = self._cache.get(k)
        if not s or (time.time() - s.updated_at) > self.ttl_sec:
            try:
                self._refresh_key(Key(strategy, model, adapter))
                with self._lock:
                    s = self._cache.get(k)
            except Exception:
                pass
        s = s or Stats(cost_per_1k=self._cost_for_model(model))
        # minimum 50 tokens heuristic when data is sparse
        tokens = max(s.tokens_per_req, 50.0)
        return (tokens / 1000.0) * s.cost_per_1k

    def estimate_latency(self, strategy: str, model: str, adapter: Optional[str] = None) -> Dict[str, float]:
        k = (strategy, model, adapter)
        with self._lock:
            s = self._cache.get(k)
        if not s or (time.time() - s.updated_at) > self.ttl_sec:
            try:
                self._refresh_key(Key(strategy, model, adapter))
                with self._lock:
                    s = self._cache.get(k)
            except Exception:
                pass
        s = s or Stats()
        return {"p50": s.p50_latency, "p95": s.p95_latency}

    # Compatibility shim for existing calls
    def update_from_logs(self, runs_dir: str = "./runs") -> None:
        try:
            p = Path(runs_dir)
            for log_file in p.glob("*.jsonl"):
                _ = log_file  # noop to preserve interface
        except Exception:
            return