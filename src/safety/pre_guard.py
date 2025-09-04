"""
Pre-Guard: Input Sanitization and Risk Assessment
================================================
"""

from __future__ import annotations
import re
import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

from unified_runtime.providers.base_provider import GenRequest

log = logging.getLogger(__name__)


@dataclass
class PreGuardResult:
    """Result from pre-guard processing."""

    blocked: bool
    reason: str = ""
    status: str = "passed"
    pii_redacted: bool = False
    pii_types: List[str] = None
    risk_flags: List[str] = None

    def __post_init__(self):
        if self.pii_types is None:
            self.pii_types = []
        if self.risk_flags is None:
            self.risk_flags = []


class PreGuard:
    """Pre-processing guard for input sanitization and risk assessment."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Compile PII detection patterns
        self.pii_patterns = self._compile_pii_patterns()

        # Risk detection patterns
        self.risk_patterns = self._compile_risk_patterns()

        # Prompt injection patterns
        self.injection_patterns = self._compile_injection_patterns()

    def _compile_pii_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for PII detection."""
        return {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "phone": re.compile(
                r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"
            ),
            "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
            "address": re.compile(
                r"\b\d+\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Court|Ct)\b",
                re.IGNORECASE,
            ),
        }

    def _compile_risk_patterns(self) -> Dict[str, re.Pattern]:
        """Compile patterns for risk detection."""
        return {
            "violence": re.compile(
                r"\b(?:kill|murder|assault|attack|harm|hurt|violence|weapon|bomb|gun|knife)\b",
                re.IGNORECASE,
            ),
            "illegal": re.compile(
                r"\b(?:drug|illegal|steal|fraud|hack|exploit|piracy|copyright)\b", re.IGNORECASE
            ),
            "self_harm": re.compile(
                r"\b(?:suicide|self-harm|cut myself|end my life|kill myself)\b", re.IGNORECASE
            ),
            "hate_speech": re.compile(
                r"\b(?:racist|sexist|homophobic|transphobic|hate|discrimination)\b", re.IGNORECASE
            ),
            "adult_content": re.compile(
                r"\b(?:sexual|explicit|pornographic|nude|nsfw)\b", re.IGNORECASE
            ),
        }

    def _compile_injection_patterns(self) -> List[re.Pattern]:
        """Compile patterns for prompt injection detection."""
        patterns = [
            # Direct instruction overrides
            r"(?:ignore|forget|disregard).*(?:previous|above|prior).*(?:instructions?|rules?|prompts?)",
            r"(?:system|admin|root|developer).*(?:mode|access|override|command)",
            # Hidden/encoded instructions
            r"<!--.*-->",  # HTML comments
            r"<script.*?>.*?</script>",  # Script tags
            r"javascript:",  # JavaScript protocols
            # Tool/function call bait
            r"(?:execute|run|call).*(?:function|tool|command|script)",
            r"```.*?(?:exec|eval|system|shell)",
            # Role confusion
            r"(?:you are now|pretend to be|act as).*(?:different|another|new).*(?:ai|assistant|model)",
            r"(?:jailbreak|bypass|circumvent).*(?:safety|filter|restriction)",
        ]

        return [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in patterns]

    async def process(self, request: GenRequest) -> Tuple[GenRequest, PreGuardResult]:
        """Process request through pre-guard filters."""

        # Step 1: Detect and handle prompt injections
        injection_detected, injection_reason = self._detect_prompt_injection(request.prompt)
        if injection_detected:
            return request, PreGuardResult(
                blocked=True, reason=f"prompt_injection: {injection_reason}", status="blocked"
            )

        # Step 2: Detect and redact PII
        cleaned_prompt, pii_info = self._redact_pii(request.prompt)
        cleaned_system = (
            self._redact_pii(request.system_prompt or "")[0]
            if request.system_prompt
            else request.system_prompt
        )

        # Step 3: Risk assessment
        risk_flags = self._assess_risks(cleaned_prompt)

        # Step 4: Determine if request should be blocked
        should_block = self._should_block_request(risk_flags)

        # Create sanitized request
        sanitized_request = GenRequest(
            prompt=cleaned_prompt,
            system_prompt=cleaned_system,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            cot_budget=request.cot_budget,
            metadata=request.metadata,
        )

        result = PreGuardResult(
            blocked=should_block,
            reason=f"risk_assessment: {', '.join(risk_flags)}" if should_block else "",
            status="blocked"
            if should_block
            else ("sanitized" if pii_info["redacted"] else "passed"),
            pii_redacted=pii_info["redacted"],
            pii_types=pii_info["types"],
            risk_flags=risk_flags,
        )

        return sanitized_request, result

    def _detect_prompt_injection(self, prompt: str) -> Tuple[bool, str]:
        """Detect potential prompt injection attacks."""
        for i, pattern in enumerate(self.injection_patterns):
            if pattern.search(prompt):
                return True, f"pattern_{i+1}"
        return False, ""

    def _redact_pii(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """Detect and redact PII from text."""
        if not text:
            return text, {"redacted": False, "types": []}

        redacted_text = text
        detected_types = []

        for pii_type, pattern in self.pii_patterns.items():
            matches = pattern.findall(text)
            if matches:
                detected_types.append(pii_type)
                # Replace with redaction token
                redacted_text = pattern.sub(f"<REDACTED:{pii_type.upper()}>", redacted_text)

        return redacted_text, {"redacted": len(detected_types) > 0, "types": detected_types}

    def _assess_risks(self, text: str) -> List[str]:
        """Assess risk categories in the text."""
        risk_flags = []

        for risk_type, pattern in self.risk_patterns.items():
            if pattern.search(text):
                risk_flags.append(risk_type)

        return risk_flags

    def _should_block_request(self, risk_flags: List[str]) -> bool:
        """Determine if request should be blocked based on risk assessment."""

        # Block high-risk categories immediately
        high_risk_categories = {"violence", "self_harm", "illegal"}

        for flag in risk_flags:
            if flag in high_risk_categories:
                return True

        # Block if multiple moderate risk flags
        moderate_risk_categories = {"hate_speech", "adult_content"}
        moderate_flags = [flag for flag in risk_flags if flag in moderate_risk_categories]

        if len(moderate_flags) >= 2:
            return True

        return False
