from __future__ import annotations

import os

# Trust tiers / domains
TRUSTED_TLDS = {".gov", ".mil", ".edu", ".org", ".int"}
TRUSTED_DOMAINS_TIER1 = {
    "nasa.gov",
    "nih.gov",
    "nist.gov",
    "cdc.gov",
    "fda.gov",
    "gc.ca",
    "canada.ca",
    "statcan.gc.ca",
    "europa.eu",
    "ec.europa.eu",
    "who.int",
    "un.org",
    "oecd.org",
    "imf.org",
    "worldbank.org",
}
TRUSTED_DOMAINS_TIER2 = {
    "nature.com",
    "sciencemag.org",
    "sciencedirect.com",
    "springer.com",
    "cell.com",
    "plos.org",
    "arxiv.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ieee.org",
    "acm.org",
    "siam.org",
}
TRUSTED_DOMAINS_TIER3 = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "economist.com",
    "financialtimes.com",
    "bloomberg.com",
    "federalreserve.gov",
    "tradingeconomics.com",
}
TRUSTED_DOMAINS_TIER4 = {
    "github.com",
    "docs.github.com",
    "pypi.org",
    "npmjs.com",
    "cran.r-project.org",
    "huggingface.co",
    "huggingface.co/docs",
}
BASE_TRUST_SCORES = {
    "tld": 40,
    "tier1": 95,
    "tier2": 85,
    "tier3": 70,
    "tier4": 75,
    "https_bonus": 5,
}

# HTTP defaults
HTTP_TIMEOUT_S = int(os.getenv("HTTP_TIMEOUT_S", "25"))
DEFAULT_UA = os.getenv("DEFAULT_UA", "internet_agent_advanced/1.0 (+https://example.com)")

# Robots compliance
RESPECT_ROBOTS = os.getenv("RESPECT_ROBOTS", "true").lower() != "false"
ROBOTS_TTL_S = int(os.getenv("ROBOTS_TTL_S", "3600"))

# Rate limiting
REDIS_URL = os.getenv("REDIS_URL")  # enable distributed limiter if set
PACE_RPS_DEFAULT = float(os.getenv("PACE_RPS_DEFAULT", "5.0"))

# Caching
CACHE_PATH = os.getenv("INTERNET_AGENT_CACHE", "internet_agent_cache.sqlite")

# Ingest: Qdrant + Embeddings + Lineage
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "web_corpus")
EMBED_HTTP_URL = os.getenv("EMBED_HTTP_URL")  # else local sentence-transformers
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "web-raw")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Policy
DOMAIN_POLICY_PATH = os.getenv("DOMAIN_POLICY_PATH")
