"""
Confidence Modeler 2.0 (Enhanced Trust Protocol)
================================================

An advanced confidence scoring system that estimates the probability an operator
would approve a proposed action based on:
- Historical approval rates (Phase 1)
- Semantic similarity to previously approved/denied actions (Phase 2)
- Cost and risk factors (Phase 2)
- Online calibration and SHAP explanations (Future)
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
import time
import json
import hashlib


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
        self.stats: Dict[str, Tuple[int, int]] = {}
        self.updated_at = 0.0

        # Enhanced Phase 2 features
        self.semantic_cache: Dict[str, np.ndarray] = {}  # text_hash -> embedding
        self.historical_actions: List[Dict[str, Any]] = []  # Full action history with outcomes
        self.cost_risk_history: Dict[str, List[float]] = {}  # action_type -> [cost/risk values]

        # Initialize embedding model if available
        self.embedding_model = None
        self._initialize_embeddings()

    def _initialize_embeddings(self):
        """Initialize sentence transformer for semantic similarity."""
        try:
            from sentence_transformers import SentenceTransformer

            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            self.embedding_model = None

    def _get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text with caching."""
        if not self.embedding_model:
            return None

        text_hash = hashlib.md5(text.encode()).hexdigest()

        if text_hash in self.semantic_cache:
            return self.semantic_cache[text_hash]

        try:
            embedding = self.embedding_model.encode([text])[0]
            self.semantic_cache[text_hash] = embedding
            return embedding
        except Exception:
            return None

    def _calculate_semantic_similarity(self, proposal_text: str, action_type: str) -> float:
        """Calculate semantic similarity to previously approved actions of same type."""
        if not self.embedding_model:
            return 0.5  # Neutral similarity if embeddings unavailable

        proposal_embedding = self._get_text_embedding(proposal_text)
        if proposal_embedding is None:
            return 0.5

        # Find similar actions of the same type
        similar_approved = []
        similar_denied = []

        for action in self.historical_actions:
            if action.get("action_type") != action_type:
                continue

            action_embedding = self._get_text_embedding(action.get("text", ""))
            if action_embedding is None:
                continue

            # Calculate cosine similarity
            similarity = np.dot(proposal_embedding, action_embedding) / (
                np.linalg.norm(proposal_embedding) * np.linalg.norm(action_embedding)
            )

            if action.get("approved"):
                similar_approved.append(similarity)
            else:
                similar_denied.append(similarity)

        # Weighted similarity score
        if not similar_approved and not similar_denied:
            return 0.5  # No historical data

        avg_approved_sim = np.mean(similar_approved) if similar_approved else 0.0
        avg_denied_sim = np.mean(similar_denied) if similar_denied else 0.0

        # Higher similarity to approved actions increases confidence
        # Higher similarity to denied actions decreases confidence
        semantic_score = (avg_approved_sim - avg_denied_sim + 1) / 2
        return max(0.0, min(1.0, semantic_score))

    def _calculate_cost_risk_factor(self, proposal: Dict[str, Any]) -> float:
        """Calculate cost/risk adjustment factor."""
        action_type = proposal.get("action_type", "generic")

        # Get estimated cost and risk from proposal
        estimated_cost = proposal.get("estimated_cost", 1.0)
        risk_level = proposal.get("risk_level", "medium")

        # Risk level mapping
        risk_multipliers = {"low": 1.0, "medium": 0.8, "high": 0.5, "critical": 0.2}

        risk_factor = risk_multipliers.get(risk_level, 0.8)

        # Cost factor - higher costs reduce confidence
        if estimated_cost <= 0.01:  # Very low cost
            cost_factor = 1.0
        elif estimated_cost <= 0.1:  # Low cost
            cost_factor = 0.9
        elif estimated_cost <= 1.0:  # Medium cost
            cost_factor = 0.7
        else:  # High cost
            cost_factor = 0.5

        # Combine risk and cost factors
        combined_factor = (risk_factor + cost_factor) / 2

        # Store for historical analysis
        if action_type not in self.cost_risk_history:
            self.cost_risk_history[action_type] = []
        self.cost_risk_history[action_type].append(combined_factor)

        return combined_factor

    def update_from_events(self, events: list[dict[str, Any]]) -> None:
        """Update confidence model from approval/denial events with enhanced tracking."""
        approvals: Dict[str, Tuple[int, int]] = {}

        for ev in events:
            if ev.get("role") == "approval_feedback":
                txt = (ev.get("content") or "").upper()
                # Expect content like "APPROVED: <proposal>" or "DENIED: <proposal>"
                approved = txt.startswith("APPROVED:")

                # Try to infer action_type tag embedded in proposal
                prop = txt.split(":", 1)[-1] if ":" in txt else txt
                action_type = "generic"
                if "[action:" in prop:
                    try:
                        action_type = prop.split("[action:", 1)[1].split("]", 1)[0]
                    except Exception:
                        action_type = "generic"

                # Store detailed action history for semantic analysis
                action_record = {
                    "action_type": action_type,
                    "text": prop,
                    "approved": approved,
                    "timestamp": ev.get("timestamp", time.time()),
                }
                self.historical_actions.append(action_record)

                # Keep only recent actions (last 1000)
                if len(self.historical_actions) > 1000:
                    self.historical_actions = self.historical_actions[-1000:]

                # Update approval statistics
                a, t = approvals.get(action_type, (0, 0))
                approvals[action_type] = (a + (1 if approved else 0), t + 1)

        self.stats = approvals
        self.updated_at = time.time()

    def _score(self, action_type: str) -> Tuple[float, int]:
        """Calculate base approval probability with Laplace smoothing."""
        a, t = self.stats.get(action_type, (0, 0))
        # Laplace smoothing (1,1)
        p = (a + 1) / (t + 2) if t >= 0 else 0.5
        return p, t

    def decide(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced decision making with semantic similarity and cost/risk factors."""
        action_type = proposal.get("action_type", "generic")
        proposal_text = proposal.get("text", "")

        # Phase 1: Base approval rate
        base_confidence, n = self._score(action_type)

        # Phase 2: Semantic similarity adjustment
        semantic_similarity = self._calculate_semantic_similarity(proposal_text, action_type)

        # Phase 2: Cost/risk factor
        cost_risk_factor = self._calculate_cost_risk_factor(proposal)

        # Combine all factors with weights
        weights = {"base": 0.5, "semantic": 0.3, "cost_risk": 0.2}

        final_confidence = (
            weights["base"] * base_confidence
            + weights["semantic"] * semantic_similarity
            + weights["cost_risk"] * cost_risk_factor
        )

        # Ensure confidence is in valid range
        final_confidence = max(0.0, min(1.0, final_confidence))

        # Bypass decision based on enhanced confidence
        bypass = (
            self.policy.enabled
            and (action_type in self.policy.allowlist if self.policy.allowlist else True)
            and n >= self.policy.min_samples
            and final_confidence >= self.policy.threshold
        )

        return {
            "score": float(final_confidence),
            "base_score": float(base_confidence),
            "semantic_similarity": float(semantic_similarity),
            "cost_risk_factor": float(cost_risk_factor),
            "samples": int(n),
            "bypass": bool(bypass),
            "reason": f"enhanced_confidence={final_confidence:.3f} (base={base_confidence:.3f}, semantic={semantic_similarity:.3f}, cost_risk={cost_risk_factor:.3f}) n={n} threshold={self.policy.threshold}",
            "version": "2.0",
        }

    def update_policy(self, policy: TrustPolicy) -> None:
        """Update trust policy."""
        self.policy = policy

    def get_model_stats(self) -> Dict[str, Any]:
        """Get detailed statistics about the confidence model."""
        return {
            "version": "2.0",
            "action_types": len(self.stats),
            "total_historical_actions": len(self.historical_actions),
            "semantic_cache_size": len(self.semantic_cache),
            "cost_risk_categories": len(self.cost_risk_history),
            "embedding_model_available": self.embedding_model is not None,
            "last_updated": self.updated_at,
            "stats_breakdown": dict(self.stats),
        }
