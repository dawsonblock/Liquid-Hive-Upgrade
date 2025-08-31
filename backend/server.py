"""
Adapter entrypoint to run LIQUID-HIVE unified runtime under platform supervisor.
It imports the FastAPI app from the LIQUID-HIVE repo and exposes it as `app`.
All routes are already prefixed with /api inside unified_runtime/server.py
"""
import os
import sys
from pathlib import Path

# Ensure LIQUID-HIVE repo is importable
REPO_ROOT = Path('/app/liquid_hive_src/LIQUID-HIVE-main')
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load .env from LIQUID-HIVE if present
try:
    from dotenv import load_dotenv  # type: ignore
    env_path = REPO_ROOT / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path))
except Exception:
    pass

# Expose FastAPI app for uvicorn
from unified_runtime.server import app  # noqa: E402