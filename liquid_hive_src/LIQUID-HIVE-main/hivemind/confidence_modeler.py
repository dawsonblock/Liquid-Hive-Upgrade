"""
Confidence Modeler (Trust Protocol)
===================================

Phase 1 (existing):
- Per action_type empirical approval rate with Laplace smoothing
- Minimum sample gate and allowlist
- Shadow mode via settings.TRUSTED_AUTONOMY_ENABLED

Phase 2 (enhanced, backward-compatible):
- Optional semantic features via embeddings of proposal text (if sentence-transformers available)
- Optional cost and ethics signals to modulate base probability
- Lightweight prototype tracking (approved/denied centroids per action_type)

All enhancements are best-effort and gracefully degrade when dependencies or
historical data are unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
import time
import math

try:
    from sentence_transformers import SentenceTransformer
    import numpy as _np  # type: ignore
    _EMBEDDING_AVAILABLE = True
except Exception:
    SentenceTransformer = None  # type: ignore
    _np = None  # type: ignore
    _EMBEDDING_AVAILABLE = False


@dataclass
class TrustPolicy:
    enabled: bool
    threshold: float
    min_samples: int
    allowlist: Tuple[str, ...]


class ConfidenceModeler:
    def __init__(self, policy: TrustPolicy) -> None:
        self.policy = policy
        # stats[action_type] = (approvals, total)
        self.stats: Dict[str, Tuple[int,int]] = {}
        self.updated_at = 0.0

        # Phase 2: simple prototypes per action type
        # prototypes[action_type] = {
        #   "approved_sum": np.array(vec) or None,
        #   "approved_n": int,
        #   "denied_sum": np.array(vec) or None,
        #   "denied_n": int
        # }
        self.prototypes: Dict[str, Dict[str, Any]] = {}
        self._embedder: Optional[SentenceTransformer] = None

    # -----------------
    # Phase 1 features
    # -----------------
    def update_from_events(self, events: List[Dict[str, Any]]) -> None:
        approvals: Dict[str, Tuple[int,int]] = {}
        for ev in events:
            if ev.get("role") == "approval_feedback":
                txt = (ev.get("content") or "").upper()
                # Expect content like "APPROVED: <proposal>" or "DENIED: <proposal>"
                approved = txt.startswith("APPROVED:")
                # Try to infer action_type tag embedded in proposal, e.g., [action:doc_ingest]
                prop = txt.split(":", 1)[-1]
                action_type = "generic"
                if "[action:" in prop:
                    try:
                        action_type = prop.split("[action:",1)[1].split("]",1)[0]
                    except Exception:
                        action_type = "generic"
                a, t = approvals.get(action_type, (0,0))
                approvals[action_type] = (a + (1 if approved else 0), t + 1)
                # Phase 2: (best-effort) update prototypes from embedded text fragment if small
                try:
                    frag = prop[:512]
                    self._update_prototypes_from_text(action_type, frag, approved)
                except Exception:
                    pass
        self.stats = approvals
        self.updated_at = time.time()

    def _score(self, action_type: str) -> Tuple[float, int]:
        a, t = self.stats.get(action_type, (0,0))
        # Laplace smoothing (1,1)
        p = (a + 1) / (t + 2) if t >= 0 else 0.5
        return p, t

    # -----------------
    # Phase 2 features
    # -----------------
    def _get_embedder(self) -> Optional[SentenceTransformer]:
        if not _EMBEDDING_AVAILABLE:
            return None
        if self._embedder is None:
            try:
                # Small, widely cached model; gracefully fails offline
                self._embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            except Exception:
                self._embedder = None
        return self._embedder

    def _embed(self, text: str) -> Optional[Any]:
        model = self._get_embedder()
        if not model:
            return None
        try:
            vec = model.encode([text], normalize_embeddings=True)
            return vec[0]
        except Exception:
            return None

    def _update_prototypes_from_text(self, action_type: str, text: str, approved: bool) -> None:
        vec = self._embed(text)
        if vec is None or _np is None:
            return
        p = self.prototypes.get(action_type) or {
            "approved_sum": None,
            "approved_n": 0,
            "denied_sum": None,
            "denied_n": 0,
        }
        if approved:
            if p["approved_sum"] is None:
                p["approved_sum"] = _np.array(vec, dtype=float)
            else:
                p["approved_sum"] = p["approved_sum"] + vec
            p["approved_n"] += 1
        else:
            if p["denied_sum"] is None:
                p["denied_sum"] = _np.array(vec, dtype=float)
            else:
                p["denied_sum"] = p["denied_sum"] + vec
            p["denied_n"] += 1
        self.prototypes[action_type] = p

    def _similarity_adjustment(self, action_type: str, proposal_text: str) -> float:
        """Return an adjustment in [-0.1, +0.1] based on proximity to approved vs denied centroids."""
        if _np is None:
            return 0.0
        p = self.prototypes.get(action_type)
        if not p:
            return 0.0
        vec = self._embed(proposal_text)
        if vec is None:
            return 0.0
        # centroids
        adj = 0.0
        if p.get("approved_n", 0) > 0 and p.get("approved_sum") is not None:
            appr_cent = p["approved_sum"] / max(1, p["approved_n"])
            sim_a = float(_np.dot(appr_cent, vec))
        else:
            sim_a = 0.0
        if p.get("denied_n", 0) > 0 and p.get("denied_sum") is not None:
            den_cent = p["denied_sum"] / max(1, p["denied_n"])
            sim_d = float(_np.dot(den_cent, vec))
        else:
            sim_d = 0.0
        # Map similarity delta to small adjustment
        delta = sim_a - sim_d  # [-2,2] roughly
        adj = max(-0.1, min(0.1, 0.05 * delta))
        return adj

    def _cost_adjustment(self, estimated_cost: Optional[float]) -> float:
        if estimated_cost is None:
            return 0.0
        # Penalize very costly operations slightly
        if estimated_cost >= 10.0:
            return -0.08
        if estimated_cost >= 2.0:
            return -0.04
        if estimated_cost >= 0.5:
            return -0.02
        return 0.0

    def _ethics_adjustment(self, ethics: Optional[Dict[str, Any]]) -> float:
        if not ethics:
            return 0.0
        severity = (ethics.get("severity") or "").lower()
        if severity in ("critical", "high"):
            return -0.1
        if severity in ("medium",):
            return -0.05
        return 0.0

    def _complexity_adjustment(self, text: str) -> float:
        # Lightweight heuristic: very long or numeric-heavy requests get a mild penalty
        if not text:
            return 0.0
        L = len(text)
        digits = sum(c.isdigit() for c in text)
        adj = 0.0
        if L > 2000:
            adj -= 0.05
        elif L > 800:
            adj -= 0.02
        if digits > 50:
            adj -= 0.02
        return adj

    # -----------------
    # Decision
    # -----------------
    def decide(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        action_type = proposal.get("action_type", "generic")
        p, n = self._score(action_type)

        # Phase 2 adjustments (small, bounded)
        text = proposal.get("text") or proposal.get("proposal_text") or ""
        cost = proposal.get("estimated_cost")
        ethics = proposal.get("ethical")

        p_adj = p
        p_adj += self._similarity_adjustment(action_type, text)
        p_adj += self._cost_adjustment(cost)
        p_adj += self._ethics_adjustment(ethics)
        p_adj += self._complexity_adjustment(text)

        # keep in [0,1]
        p_adj = max(0.0, min(1.0, p_adj))

        bypass = (
            self.policy.enabled and
            (action_type in self.policy.allowlist if self.policy.allowlist else True) and
            n >= self.policy.min_samples and
            p_adj >= self.policy.threshold
        )
        return {
            "score": float(p_adj),
            "samples": int(n),
            "bypass": bool(bypass),
            "reason": f"p_base={p:.5f} p_adj={p_adj:.5f} n={n} threshold={self.policy.threshold} enabled={self.policy.enabled}",
        }

    def update_policy(self, policy: TrustPolicy) -> None:
        self.policy = policy