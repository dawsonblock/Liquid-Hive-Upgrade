from pydantic import BaseSettings

class Settings(BaseSettings):
    vllm_endpoint: str = "http://localhost:8000/v1"
    vllm_api_key: str = "unused"
    vl_model_id: str = "LiquidAI/LFM2-VL-1.6B"
    committee_k: int = 3
    max_new_tokens: int = 512
    runs_dir: str = "./runs"
    rag_index: str = "./rag_index"
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    text_adapter_path: str | None = None

    # --- Arbiter Governor Controls ---
    # Master switch to enable/disable the entire Oracle/Arbiter refinement pipeline.
    # If False, dataset construction will bypass external refinement and use
    # the synthesized answer as-is.  This flag is read from the environment.
    ENABLE_ORACLE_REFINEMENT: bool = True

    # Force the use of the GPT‑4o Arbiter, bypassing DeepSeek‑V3 entirely.
    # Only applicable when ENABLE_ORACLE_REFINEMENT is True.  Set this to
    # True to ensure every refinement uses the more powerful GPT‑4o model.
    FORCE_GPT4O_ARBITER: bool = False

    # --- Autonomy Governor ---
    # Master switch to enable the autonomous executive core.  When False
    # the AutonomyOrchestrator will not be started, and all high‑level
    # learning and decision making must be triggered manually by the operator.
    ENABLE_AUTONOMOUS_EXECUTIVE: bool = True
    class Config:
        env_prefix = ""
        env_file = ".env"
