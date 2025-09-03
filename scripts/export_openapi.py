#!/usr/bin/env python3
import os, sys, json, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / 'src'))
from unified_runtime.server import app

if __name__ == "__main__":
    out_dir = pathlib.Path(__file__).resolve().parents[1] / 'docs'
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / 'openapi.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(app.openapi(), indent=2))
    print("Exported OpenAPI to docs/openapi.json")