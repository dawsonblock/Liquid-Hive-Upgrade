"""
Determinism setup for internet_agent_advanced
- Sets global seeds where applicable
- Establishes default stable behavior knobs
"""
from __future__ import annotations

def setup() -> None:
    import os
    import random
    # Hash seed for deterministic dict/set order across processes
    os.environ.setdefault("PYTHONHASHSEED", "0")
    # Python RNG seed
    random.seed(42)
    # Numpy seed if available
    try:
        import numpy as np  # type: ignore
        np.random.seed(42)
    except Exception:
        pass