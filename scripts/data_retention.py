#!/usr/bin/env python3
from __future__ import annotations

import os
import pathlib
import time

BASE = pathlib.Path(os.getenv("RUNS_DIR", "/app/data/runs"))
DAYS = int(os.getenv("DATA_RETENTION_DAYS", "30"))
CUT = time.time() - DAYS * 86400

if not BASE.exists():
    raise SystemExit(0)

removed = 0
for p in BASE.glob("**/*"):
    try:
        if p.is_file() and p.stat().st_mtime < CUT:
            p.unlink()
            removed += 1
    except Exception:
        pass
print(f"Removed {removed} old files from {BASE}")
