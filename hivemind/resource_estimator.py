"""
Resource usage estimation service
=================================

This module defines a ``ResourceEstimator`` class that tracks basic
resource consumption metrics (e.g. token usage, latency) for the HiveMind
models and roles.  In a production deployment this would ingest data from
Prometheus to compute an exponentially weighted moving average (EWMA) per
role and model.  Here we provide a minimal in‑memory implementation that
can be queried by the ``StrategySelector`` to make cost‑aware decisions.

The estimator exposes public methods to update the statistics manually
(`update`) and to derive statistics from run logs (`update_from_logs`).
It also provides ``estimate_cost`` for a rough cost estimate per role.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional
import time, json
from pathlib import Path

@dataclass
class RoleStats:
    """Simple container to track EWMA of tokens and latency for a role."""
    ewma_tokens: float = 0.0
    ewma_latency: float = 0.0
    last_update: float = field(default_factory=time.time)

class ResourceEstimator:
    """
    Estimate the dollar cost of running tasks.

    In lieu of real monitoring data this estimator maintains an EWMA of
    observed token counts and latencies.  When called with a role name it
    returns a rough cost based on a fixed token price.  The estimator can
    also be updated after tasks complete to refine its estimates and can
    ingest historic run logs for initialisation.
    """
    def __init__(self, token_price_per_k: float = 0.002) -> None:
        self.token_price_per_k = token_price_per_k
        self.roles: Dict[str, RoleStats] = {}
        self.alpha = 0.3

    def update(self, role: str, tokens: int, latency: float) -> None:
        """Record a new observation for the given role."""
        stats = self.roles.setdefault(role, RoleStats())
        stats.ewma_tokens = (1 - self.alpha) * stats.ewma_tokens + self.alpha * tokens
        stats.ewma_latency = (1 - self.alpha) * stats.ewma_latency + self.alpha * latency
        stats.last_update = time.time()

    def update_from_logs(self, runs_dir: str = "./runs") -> None:
        """
        Update EWMA estimates based on run logs.

        This method scans JSONL files in ``runs_dir``.  It approximates the
        token count by counting words in the answers stored in the logs and
        updates the estimator accordingly.  Latency is ignored.
        """
        p = Path(runs_dir)
        for log_file in p.glob("*.jsonl"):
            try:
                for line in log_file.read_text().splitlines():
                    rec = json.loads(line)
                    kind = rec.get("kind")
                    pay = rec.get("payload", {})
                    if kind == "text_single":
                        ans = pay.get("winner", "")
                        tokens = len(ans.split())
                        self.update("implementer", tokens, 0.0)
                    elif kind == "text_committee":
                        answers = pay.get("answers", [])
                        for a in answers:
                            tokens = len(a.split())
                            self.update("implementer", tokens, 0.0)
                    elif kind == "text_debate":
                        cands = pay.get("candidates", [])
                        for a in cands:
                            tokens = len(a.split())
                            self.update("implementer", tokens, 0.0)
            except Exception:
                continue

    def estimate_cost(self, role: str, expected_tokens: Optional[int] = None) -> float:
        """
        Estimate the dollar cost of running a task for the specified role.

        If ``expected_tokens`` is provided it overrides the EWMA token
        estimate.  Otherwise the EWMA token count is used with a minimum
        default of 50 tokens.
        """
        stats = self.roles.get(role)
        tokens = expected_tokens if expected_tokens is not None else (stats.ewma_tokens if stats else 50)
        return max((tokens / 1000.0) * self.token_price_per_k, 0.0001)