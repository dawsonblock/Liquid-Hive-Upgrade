from __future__ import annotations

import os
import random

try:
    import numpy as np
except Exception:
    np = None

DEFAULT_SEED = int(os.getenv("DETERMINISTIC_SEED", "42"))


def set_determinism():
    random.seed(DEFAULT_SEED)
    if np:
        np.random.seed(DEFAULT_SEED)
    # If torch is available, set it; we don't import unconditionally
    try:
        import torch

        torch.manual_seed(DEFAULT_SEED)
        torch.cuda.manual_seed_all(DEFAULT_SEED)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass
