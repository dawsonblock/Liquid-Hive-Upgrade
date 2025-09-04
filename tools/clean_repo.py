#!/usr/bin/env python3
import argparse, shutil
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]

BASE_PATTERNS = [
    "**/__pycache__",
    "**/.pytest_cache",
    "**/.mypy_cache",
    "**/.ruff_cache",
    "**/.cache",
    "**/node_modules",              # handled in deep mode at top-level too
    "**/dist",
    "**/build",
    "**/out",
    "**/coverage",
    "**/*.map",
    "**/*.log",
    "**/*.tmp",
    "**/*.tsbuildinfo",
    "**/.DS_Store",
    "**/Thumbs.db",
]

DEEP_EXTRAS = [
    "frontend/node_modules",
    "sdks/js/node_modules",
    "frontend/dist",
    "frontend/build",
    "reports",
    "pip*.out",
    "pytest*.out",
    "flake.out",
]

def resolve_patterns(patterns: List[str]) -> List[Path]:
    seen = set()
    paths: List[Path] = []
    for pat in patterns:
        for p in ROOT.glob(pat):
            try:
                rel = p.resolve()
            except Exception:
                continue
            if rel in seen:
                continue
            seen.add(rel)
            paths.append(p)
    return paths

def rm_path(p: Path, dry: bool) -> None:
    if not p.exists():
        return
    if dry:
        print(f"DRY: would remove {p}")
        return
    if p.is_file() or p.is_symlink():
        p.unlink(missing_ok=True)
    else:
        shutil.rmtree(p, ignore_errors=True)

def main():
    ap = argparse.ArgumentParser(description="Clean repo artifacts safely")
    ap.add_argument("--apply", action="store_true", help="Perform deletions (default: dry-run)")
    ap.add_argument("--deep", action="store_true", help="Include heavy caches (node_modules, reports, *.out)")
    ap.add_argument("--extra", action="append", default=[], help="Additional glob(s) to remove")
    args = ap.parse_args()
    patterns = BASE_PATTERNS + (DEEP_EXTRAS if args.deep else []) + args.extra
    targets = resolve_patterns(patterns)
    if not targets:
        print("Nothing to remove")
        return 0
    # sort: longer paths later
    targets.sort(key=lambda p: (p.is_file(), len(p.as_posix())), reverse=True)
    for p in targets:
        rm_path(p, dry=not args.apply)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())