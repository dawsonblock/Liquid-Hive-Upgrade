#!/usr/bin/env python3
import argparse, hashlib, json, os
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SKIP_DIRS = {".git", "node_modules", "dist", "build", "out", ".cache", "__pycache__", ".venv", "venv", "env"}

PRIORITY_DIRS = ["src/", "backend/", "frontend/", "docs/"]

def hash_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def should_skip(p: Path) -> bool:
    parts = set(pp for pp in p.relative_to(ROOT).parts)
    return any(d in parts for d in SKIP_DIRS)

def gather_files() -> List[Path]:
    files: List[Path] = []
    for d, subdirs, fns in os.walk(ROOT, topdown=True):
        subdirs[:] = [s for s in subdirs if s not in SKIP_DIRS]
        for fn in fns:
            p = Path(d) / fn
            if p.is_symlink() or not p.is_file():
                continue
            files.append(p)
    return files

def preferred(files: List[Path]) -> Path:
    rels = [f.relative_to(ROOT).as_posix() for f in files]
    # Priority by prefix, then shortest path name as tiebreaker
    for pref in PRIORITY_DIRS:
        candidates = [files[i] for i, r in enumerate(rels) if r.startswith(pref)]
        if candidates:
            return sorted(candidates, key=lambda p: len(p.as_posix()))[0]
    return sorted(files, key=lambda p: len(p.as_posix()))[0]

def build_groups() -> Dict[str, List[Path]]:
    groups: Dict[str, List[Path]] = {}
    for p in gather_files():
        if should_skip(p):
            continue
        try:
            h = hash_file(p)
        except Exception:
            continue
        groups.setdefault(h, []).append(p)
    # keep only duplicates
    return {h: ps for h, ps in groups.items() if len(ps) > 1}

def main():
    ap = argparse.ArgumentParser(description="Deduplicate identical files by SHA-256")
    ap.add_argument("--apply", action="store_true", help="Delete duplicates (default: dry-run)")
    ap.add_argument("--report-out", default=str(REPORTS / "duplicate_report.json"), help="Path to write duplicate report")
    args = ap.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    groups = build_groups()
    report = {"groups": []}

    for h, files in groups.items():
        keep = preferred(files)
        to_remove = [p for p in files if p != keep]
        report["groups"].append(
            {
                "hash": h,
                "size": keep.stat().st_size if keep.exists() else 0,
                "keep": keep.relative_to(ROOT).as_posix(),
                "remove": [p.relative_to(ROOT).as_posix() for p in to_remove],
            }
        )
        for p in to_remove:
            rel = p.relative_to(ROOT).as_posix()
            if args.apply:
                try:
                    p.unlink(missing_ok=True)
                    print(f"Removed duplicate: {rel}")
                except Exception as e:
                    print(f"WARN: failed to remove {rel}: {e}")
            else:
                print(f"DRY: would remove duplicate {rel} (keeping {keep.relative_to(ROOT).as_posix()})")

    with open(args.report_out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())