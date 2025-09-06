#!/usr/bin/env python3
"""Build optimization script for Liquid Hive."""

import os
import json
from pathlib import Path
import argparse


def analyze_bundle_size(project_root: str = "."):
    """Analyze frontend bundle sizes."""
    frontend_dist = Path(project_root) / "frontend" / "dist"
    if not frontend_dist.exists():
        return {"error": "Frontend dist directory not found. Run build first."}

    js_files = list(frontend_dist.rglob("*.js"))
    js_sizes = []

    for js_file in js_files:
        size = js_file.stat().st_size
        js_sizes.append({
            "file": str(js_file.relative_to(frontend_dist)),
            "size_mb": round(size / (1024 * 1024), 2)
        })

    js_sizes.sort(key=lambda x: x["size_mb"], reverse=True)
    total_size_mb = sum(f["size_mb"] for f in js_sizes)

    recommendations = []
    if total_size_mb > 2:
        recommendations.append("Consider code splitting - total bundle is large")

    large_files = [f for f in js_sizes if f["size_mb"] > 0.5]
    if large_files:
        recommendations.append(f"Found {len(large_files)} large files (>500KB)")

    return {
        "total_size_mb": total_size_mb,
        "file_count": len(js_sizes),
        "largest_files": js_sizes[:5],
        "recommendations": recommendations
    }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Build Optimizer")
    parser.add_argument("--project-root", default=".", help="Project root")
    args = parser.parse_args()

    print("🔍 Analyzing build...")
    analysis = analyze_bundle_size(args.project_root)

    if "error" in analysis:
        print(f"❌ {analysis['error']}")
        return

    print(f"\n📦 Bundle Analysis:")
    print(f"  Total size: {analysis['total_size_mb']}MB")
    print(f"  Files: {analysis['file_count']}")

    if analysis['largest_files']:
        print(f"\n  Largest files:")
        for f in analysis['largest_files'][:3]:
            print(f"    {f['file']}: {f['size_mb']}MB")

    if analysis['recommendations']:
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(analysis['recommendations'], 1):
            print(f"  {i}. {rec}")


if __name__ == "__main__":
    main()
