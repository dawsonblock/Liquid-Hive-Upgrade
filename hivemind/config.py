from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # External service URLs must come from environment for portability
    vllm_endpoint: Optional[str] = None  # e.g., http://vllm:8000/v1
    vllm_api_key: str = "unused"
    redis_url: Optional[str] = None      # e.g., redis://redis:6379
    neo4j_url: Optional[str] = None      # e.g., bolt://neo4j:7687

    # Observability / estimator config
    PROMETHEUS_BASE_URL: Optional[str] = None
    COST_PER_1K_TOKENS_SMALL: float = 0.0008
    COST_PER_1K_TOKENS_LARGE: float = 0.0030

    vl_model_id: str = "LiquidAI/LFM2-VL-1.6B"
    committee_k: int = 3
    max_new_tokens: int = 512

    # Persisted state locations (mounted via PVC in Kubernetes)
    runs_dir: str = "/app/runs"
    rag_index: str = "/app/rag_index"
    adapters_dir: str = "/app/adapters"

    # Optional currently active text adapter path
    text_adapter_path: Optional[str] = None

    # --- Arbiter Governor Controls ---
    ENABLE_ORACLE_REFINEMENT: bool = True
    FORCE_GPT4O_ARBITER: bool = False

    # --- Autonomy Governor ---
    ENABLE_AUTONOMOUS_EXECUTIVE: bool = True

    # --- Trusted Autonomy (Confidence Modeler) ---
    TRUSTED_AUTONOMY_ENABLED: bool = False
    TRUST_THRESHOLD: float = 0.999
    TRUST_MIN_SAMPLES: int = 200
    TRUST_ALLOWLIST: Optional[str] = None  # comma-separated action types

    class Config:
        env_prefix = ""
        env_file = ".env"