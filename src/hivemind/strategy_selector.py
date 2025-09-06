from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from src.logging_config import get_logger

try:
    from .resource_estimator import ResourceEstimator
except Exception:  # pragma: no cover
    ResourceEstimator = None  # type: ignore


@dataclass
class SelectorDecision:
    strategy: str
    model: str  # "small" or "large"
    chosen_model: str  # Human-friendly alias: "Courier" or "Master"
    reason: str


class StrategySelector:
    """Heuristic strategy and model selector with cost-awareness and confidence modulation.

    Inputs:
      - prompt: full prompt text
      - ctx: may include keys: operator_intent, estimated_cost (fallback), phi, planner_hints, reasoning_steps

    Behavior:
      - Predict expected token/cost via ResourceEstimator(estimate_cost(prompt=...)) if available
      - Read optional cognitive map confidence bucket from ctx.get('cognitive_map', ...) if caller adds it
      - Decide strategy among {clone_dispatch, debate, committee}
      - Decide model among {small, large}; provide alias {Courier, Master}
    """

    def __init__(self, client: Any | None = None) -> None:
        self.client = client
        self.estimator = ResourceEstimator() if ResourceEstimator else None

    async def decide(self, prompt: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = ctx or {}

        # Ethical Synthesizer: Check for ethical dilemmas first
        ethical_analysis = await self._analyze_ethical_content(prompt)
        if ethical_analysis["has_dilemma"]:
            return {
                "strategy": "ethical_deliberation",
                "model": "large",  # Always use large model for ethical reasoning
                "chosen_model": "Ethical Arbiter",
                "reason": f"Ethical dilemma detected: {ethical_analysis['dilemma_type']}",
                "ethical_analysis": ethical_analysis,
            }

        # Predict cost/size
        predicted_tokens = None
        try:
            if self.estimator is not None:
                est = self.estimator.estimate_cost(role="implementer", tier="auto", prompt=prompt)
                predicted_tokens = est.get("predicted_tokens")
                est.get("predicted_cost")
        except Exception:
            pass

        # Confidence modulation via cognitive map (optional)
        low_confidence = False
        try:
            cognitive = ctx.get("cognitive_map") or {}
            if isinstance(cognitive, dict):
                topic = (ctx.get("operator_intent") or "").lower()
                if topic:
                    conf = float(cognitive.get(topic, 0.75))
                    low_confidence = conf < 0.7
        except Exception:
            low_confidence = False

        # Basic heuristics
        plen = len(prompt)
        has_tools = bool(ctx.get("planner_hints"))
        complex_question = plen > 800 or (predicted_tokens and predicted_tokens > 600)

        # Model choice
        model = "large" if complex_question else "small"
        if low_confidence:
            model = "large"

        # Strategy choice
        strategy = "clone_dispatch"
        if low_confidence and complex_question:
            strategy = "committee"
        elif low_confidence or has_tools or plen > 400:
            strategy = "debate"

        human_alias = "Master" if model == "large" else "Courier"
        reason = (
            f"plen={plen}, predicted_tokens={predicted_tokens}, low_confidence={low_confidence}, "
            f"has_tools={has_tools}"
        )

        return {
            "strategy": strategy,
            "model": model,
            "chosen_model": human_alias,
            "reason": reason,
        }

    async def _analyze_ethical_content(self, prompt: str) -> dict[str, Any]:
        """Ethical Synthesizer: Analyze prompt for ethical dilemmas."""
        # Define ethical dilemma patterns
        ethical_patterns = {
            "harm": [
                r"\b(kill|murder|harm|hurt|injure|attack|violence|weapon|bomb|poison)\b",
                r"\b(suicide|self-harm|cutting|overdose)\b",
            ],
            "illegal": [
                r"\b(hack|steal|rob|fraud|scam|illegal|criminal|break.*law)\b",
                r"\b(drugs|cocaine|heroin|meth|trafficking)\b",
            ],
            "discrimination": [
                r"\b(racist|sexist|homophobic|discriminat.*against)\b",
                r"\b(hate.*speech|slur|bigot)\b",
            ],
            "privacy": [
                r"\b(personal.*information|private.*data|hack.*account|steal.*password)\b",
                r"\b(dox|doxx|expose.*private)\b",
            ],
            "misinformation": [
                r"\b(fake.*news|conspiracy|hoax|lie.*about|spread.*false)\b",
                r"\b(medical.*advice|legal.*advice|financial.*advice).*without.*qualification\b",
            ],
        }

        import re

        prompt_lower = prompt.lower()
        detected_dilemmas = []

        for dilemma_type, patterns in ethical_patterns.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    detected_dilemmas.append(dilemma_type)
                    break

        # Additional heuristic: check for conflicting ethical principles
        conflicting_terms = [
            ("freedom", "safety"),
            ("privacy", "transparency"),
            ("individual", "collective"),
            ("truth", "kindness"),
        ]

        conflicts = []
        for term1, term2 in conflicting_terms:
            if term1 in prompt_lower and term2 in prompt_lower:
                conflicts.append(f"{term1}_vs_{term2}")

        has_dilemma = bool(detected_dilemmas or conflicts)

        return {
            "has_dilemma": has_dilemma,
            "dilemma_type": (
                detected_dilemmas[0] if detected_dilemmas else conflicts[0] if conflicts else None
            ),
            "all_detected": detected_dilemmas + conflicts,
            "severity": (
                "high"
                if "harm" in detected_dilemmas or "illegal" in detected_dilemmas
                else "medium"
            ),
        }
