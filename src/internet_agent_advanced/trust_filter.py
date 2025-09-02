from __future__ import annotations
from urllib.parse import urlparse
import tldextract
from .config import TRUSTED_TLDS, TRUSTED_DOMAINS_TIER1, TRUSTED_DOMAINS_TIER2, TRUSTED_DOMAINS_TIER3, TRUSTED_DOMAINS_TIER4, BASE_TRUST_SCORES

def domain_from_url(url: str) -> str:
    ext = tldextract.extract(url)
    parts = [p for p in [ext.domain, ext.suffix] if p]
    return ".".join(parts).lower()

def https_bonus(url: str) -> int:
    return BASE_TRUST_SCORES["https_bonus"] if url.lower().startswith("https://") else 0

def score_url(url: str) -> int:
    d = domain_from_url(url)
    suffix = f".{tldextract.extract(url).suffix}".lower() if tldextract.extract(url).suffix else ""
    score = 0
    if suffix in TRUSTED_TLDS: score = max(score, BASE_TRUST_SCORES["tld"])
    if d in TRUSTED_DOMAINS_TIER1: score = max(score, BASE_TRUST_SCORES["tier1"])
    elif d in TRUSTED_DOMAINS_TIER2: score = max(score, BASE_TRUST_SCORES["tier2"])
    elif d in TRUSTED_DOMAINS_TIER3: score = max(score, BASE_TRUST_SCORES["tier3"])
    elif d in TRUSTED_DOMAINS_TIER4: score = max(score, BASE_TRUST_SCORES["tier4"])
    score += https_bonus(url)
    return min(score, 100)

def is_trusted(url: str, threshold: int = 75) -> bool:
    return score_url(url) >= threshold
