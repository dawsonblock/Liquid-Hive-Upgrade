#!/usr/bin/env python3
import argparse, hashlib, json, os, sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".cache", "__pycache__", "node_modules", "dist", "build", "out", ".next", ".turbo",
    ".venv", "venv", "env", ".mypy_cache", ".pytest_cache", "coverage", ".tox", ".nox",
}
SKIP_TOP_LEVEL = {"data/ingest/qdrant_storage"}  # large test/runtime storage
HASH_CHUNK = 1024 * 1024

ARTIFACT_GLOBS = [
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/.cache/**",
    "**/node_modules/**",
    "**/dist/**",
    "**/build/**",
    "**/out/**",
    "**/coverage/**",
    "**/*.map",
    "**/*.log",
    "**/*.tmp",
    "**/*.tsbuildinfo",
    "**/.DS_Store",
    "**/Thumbs.db",
]

def is_skipped_dir(path: Path) -> bool:
    parts = set(p.name for p in path.parts)
    if any(p in SKIP_DIRS for p in parts):
        return True
    rel = path.relative_to(ROOT).as_posix()
    return any(rel.startswith(prefix) for prefix in SKIP_TOP_LEVEL)

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(HASH_CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def walk_files() -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT, topdown=True):
        # prune
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        cur = Path(dirpath)
        if is_skipped_dir(cur):
            dirnames[:] = []
            continue
        for fn in filenames:
            p = cur / fn
            try:
                if p.is_symlink() or not p.is_file():
                    continue
            except OSError:
                continue
            files.append(p)
    return files

def list_artifacts() -> List[str]:
    found: Set[str] = set()
    for pattern in ARTIFACT_GLOBS:
        for p in ROOT.glob(pattern):
            try:
                rel = p.relative_to(ROOT).as_posix()
            except Exception:
                continue
            found.add(rel)
    return sorted(found)

def duplicates(files: List[Path]) -> Tuple[int, List[Dict]]:
    by_size: Dict[int, List[Path]] = {}
    for p in files:
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        by_size.setdefault(sz, []).append(p)
    groups: Dict[str, List[str]] = {}
    count_hashed = 0
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        for p in paths:
            try:
                h = sha256_file(p)
                count_hashed += 1
                groups.setdefault(h, []).append(p.relative_to(ROOT).as_posix())
            except Exception:
                continue
    result = []
    for h, flist in groups.items():
        if len(flist) < 2:
            continue
        size = (ROOT / flist[0]).stat().st_size if flist else 0
        result.append({"hash": h, "size": size, "files": sorted(flist)})
    result.sort(key=lambda g: g["size"], reverse=True)
    return count_hashed, result

def main():
    parser = argparse.ArgumentParser(description="Audit repo: inventory and duplicate report")
    args = parser.parse_args()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    files = walk_files()
    total_size = sum((p.stat().st_size for p in files), 0)
    inv_path = REPORTS_DIR / "pre_cleanup_inventory.txt"
    with inv_path.open("w", encoding="utf-8") as f:
        f.write(f"Root: {ROOT}\n")
        f.write(f"Total files (scanned): {len(files)}\n")
        f.write(f"Total size (bytes): {total_size}\n\n")
        f.write("Files:\n")
        for p in sorted(files):
            try:
                sz = p.stat().st_size
            except OSError:
                sz = -1
            f.write(f"{p.relative_to(ROOT).as_posix()}\t{sz}\n")
        f.write("\nArtifact candidates:\n")
        for rel in list_artifacts():
            f.write(rel + "\n")

    hashed_count, dup_groups = duplicates(files)
    dup_path = REPORTS_DIR / "duplicate_report.json"
    with dup_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "skipped_dirs": sorted(list(SKIP_DIRS | set(d for d in SKIP_TOP_LEVEL))),
                "total_files_hashed": hashed_count,
                "groups": dup_groups,
            },
            f,
            indent=2,
        )

    print(f"Wrote {inv_path} and {dup_path}")

if __name__ == "__main__":
    main()