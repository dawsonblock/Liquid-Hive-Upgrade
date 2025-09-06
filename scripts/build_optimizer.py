#!/usr/bin/env python3
"""
Build optimization script for Liquid Hive.
Provides caching, parallel processing, incremental builds, and performance optimization.
"""

import os
import sys
import json
import time
import hashlib
import shutil
import subprocess
import multiprocessing
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timedelta
import argparse


class BuildOptimizer:
    """Advanced build optimization system."""

    def __init__(self, cache_dir: str = ".build_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        self.manifest_file = self.cache_dir / "build_manifest.json"
        self.dependency_cache = self.cache_dir / "dependencies.json"
        self.parallel_jobs = min(multiprocessing.cpu_count(), 8)

        self.manifest = self.load_manifest()
        self.dependencies = self.load_dependencies()

    def load_manifest(self) -> Dict[str, Any]:
        """Load build manifest for incremental builds."""
        if self.manifest_file.exists():
            with open(self.manifest_file, 'r') as f:
                return json.load(f)
        return {
            "last_build": None,
            "files": {},
            "builds": {},
            "cache_hits": 0,
            "cache_misses": 0
        }

    def save_manifest(self):
        """Save build manifest."""
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)

    def load_dependencies(self) -> Dict[str, Any]:
        """Load dependency information."""
        if self.dependency_cache.exists():
            with open(self.dependency_cache, 'r') as f:
                return json.load(f)
        return {"python": {}, "node": {}, "docker": {}}

    def save_dependencies(self):
        """Save dependency information."""
        with open(self.dependency_cache, 'w') as f:
            json.dump(self.dependencies, f, indent=2)

    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""

    def get_file_dependencies(self, file_path: Path) -> Set[Path]:
        """Get dependencies for a file (imports, includes, etc.)."""
        dependencies = set()

        if file_path.suffix == '.py':
            dependencies.update(self.get_python_dependencies(file_path))
        elif file_path.suffix in ['.ts', '.tsx', '.js', '.jsx']:
            dependencies.update(self.get_js_dependencies(file_path))
        elif file_path.suffix == '.dockerfile':
            dependencies.update(self.get_docker_dependencies(file_path))

        return dependencies

    def get_python_dependencies(self, file_path: Path) -> Set[Path]:
        """Get Python file dependencies."""
        dependencies = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple import detection (could be enhanced with AST parsing)
            import re
            import_patterns = [
                r'from\s+(\S+)\s+import',
                r'import\s+(\S+)',
                r'from\s+\.(\S+)\s+import'
            ]

            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Convert import to potential file path
                    if match.startswith('.'):
                        # Relative import
                        base_dir = file_path.parent
                        module_path = match.replace('.', '/') + '.py'
                        dep_path = base_dir / module_path
                        if dep_path.exists():
                            dependencies.add(dep_path)
                    else:
                        # Absolute import - check if it's a local module
                        module_parts = match.split('.')
                        for i in range(len(module_parts)):
                            potential_path = Path('.') / '/'.join(module_parts[:i+1]) / '__init__.py'
                            if potential_path.exists():
                                dependencies.add(potential_path)
                                break
        except Exception:
            pass

        return dependencies

    def get_js_dependencies(self, file_path: Path) -> Set[Path]:
        """Get JavaScript/TypeScript file dependencies."""
        dependencies = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple import detection
            import re
            import_patterns = [
                r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'import\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)'
            ]

            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.startswith('.'):
                        # Relative import
                        base_dir = file_path.parent
                        if match.endswith(('.ts', '.tsx', '.js', '.jsx')):
                            dep_path = base_dir / match
                        else:
                            # Try common extensions
                            for ext in ['.ts', '.tsx', '.js', '.jsx']:
                                dep_path = base_dir / (match + ext)
                                if dep_path.exists():
                                    break
                            else:
                                dep_path = base_dir / (match + '/index.ts')

                        if dep_path.exists():
                            dependencies.add(dep_path)
        except Exception:
            pass

        return dependencies

    def get_docker_dependencies(self, file_path: Path) -> Set[Path]:
        """Get Dockerfile dependencies."""
        dependencies = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for COPY and ADD instructions
            import re
            copy_patterns = [
                r'COPY\s+([^\s]+)\s+',
                r'ADD\s+([^\s]+)\s+'
            ]

            for pattern in copy_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if not match.startswith('http'):
                        dep_path = Path(match)
                        if dep_path.exists():
                            dependencies.add(dep_path)
        except Exception:
            pass

        return dependencies

    def is_file_changed(self, file_path: Path) -> bool:
        """Check if a file has changed since last build."""
        current_hash = self.calculate_file_hash(file_path)
        stored_hash = self.manifest["files"].get(str(file_path), {}).get("hash", "")

        if current_hash != stored_hash:
            return True

        # Check if any dependencies have changed
        dependencies = self.get_file_dependencies(file_path)
        for dep in dependencies:
            if self.is_file_changed(dep):
                return True

        return False

    def update_file_manifest(self, file_path: Path):
        """Update file information in manifest."""
        file_path_str = str(file_path)
        self.manifest["files"][file_path_str] = {
            "hash": self.calculate_file_hash(file_path),
            "mtime": file_path.stat().st_mtime,
            "dependencies": [str(dep) for dep in self.get_file_dependencies(file_path)]
        }

    def get_changed_files(self, target_dir: str, extensions: List[str]) -> List[Path]:
        """Get list of changed files in target directory."""
        changed_files = []
        target_path = Path(target_dir)

        for file_path in target_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                if self.is_file_changed(file_path):
                    changed_files.append(file_path)
                    self.update_file_manifest(file_path)

        return changed_files

    def optimize_python_build(self) -> bool:
        """Optimize Python build with incremental compilation."""
        print("🐍 Optimizing Python build...")

        # Check if we need to rebuild
        python_files = self.get_changed_files("src", [".py"])
        python_files.extend(self.get_changed_files("apps", [".py"]))

        if not python_files:
            print("✅ No Python files changed, skipping build")
            return True

        print(f"📝 Found {len(python_files)} changed Python files")

        # Use parallel compilation if possible
        if len(python_files) > 1:
            return self.parallel_python_compile(python_files)
        else:
            return self.compile_python_file(python_files[0])

    def parallel_python_compile(self, files: List[Path]) -> bool:
        """Compile Python files in parallel."""
        try:
            with multiprocessing.Pool(self.parallel_jobs) as pool:
                results = pool.map(self.compile_python_file, files)
            return all(results)
        except Exception as e:
            print(f"❌ Parallel compilation failed: {e}")
            return False

    def compile_python_file(self, file_path: Path) -> bool:
        """Compile a single Python file."""
        try:
            # This is a placeholder - in practice you'd run actual compilation
            # For now, just update the manifest
            self.update_file_manifest(file_path)
            return True
        except Exception as e:
            print(f"❌ Failed to compile {file_path}: {e}")
            return False

    def optimize_frontend_build(self) -> bool:
        """Optimize frontend build with caching and parallel processing."""
        print("⚛️  Optimizing frontend build...")

        frontend_dir = Path("frontend")
        if not frontend_dir.exists():
            print("❌ Frontend directory not found")
            return False

        # Check for changes in frontend files
        frontend_files = self.get_changed_files("frontend/src", [".ts", ".tsx", ".js", ".jsx"])

        if not frontend_files:
            print("✅ No frontend files changed, skipping build")
            return True

        print(f"📝 Found {len(frontend_files)} changed frontend files")

        # Use Vite's built-in optimization
        try:
            result = subprocess.run(
                ["yarn", "build"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ Frontend build completed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Frontend build failed: {e}")
            print(f"Error output: {e.stderr}")
            return False

    def optimize_docker_build(self) -> bool:
        """Optimize Docker builds with layer caching."""
        print("🐳 Optimizing Docker builds...")

        dockerfiles = [
            "apps/api/Dockerfile",
            "frontend/Dockerfile",
            "services/feedback_api/Dockerfile",
            "services/oracle_api/Dockerfile"
        ]

        success = True
        for dockerfile in dockerfiles:
            if not Path(dockerfile).exists():
                continue

            print(f"🔨 Building {dockerfile}...")

            # Use BuildKit for better caching
            env = os.environ.copy()
            env["DOCKER_BUILDKIT"] = "1"

            try:
                result = subprocess.run([
                    "docker", "build",
                    "--cache-from", f"liquid-hive-{Path(dockerfile).stem}:latest",
                    "-t", f"liquid-hive-{Path(dockerfile).stem}:latest",
                    "-f", dockerfile,
                    "."
                ], env=env, capture_output=True, text=True, check=True)

                print(f"✅ {dockerfile} built successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ {dockerfile} build failed: {e}")
                success = False

        return success

    def setup_build_cache(self):
        """Set up build cache for better performance."""
        print("💾 Setting up build cache...")

        # Create cache directories
        cache_dirs = [
            self.cache_dir / "python",
            self.cache_dir / "node",
            self.cache_dir / "docker",
            self.cache_dir / "reports"
        ]

        for cache_dir in cache_dirs:
            cache_dir.mkdir(exist_ok=True)

        # Set up Python cache
        self.setup_python_cache()

        # Set up Node cache
        self.setup_node_cache()

        print("✅ Build cache setup complete")

    def setup_python_cache(self):
        """Set up Python build cache."""
        # Set PYTHONPYCACHEPREFIX for centralized cache
        os.environ["PYTHONPYCACHEPREFIX"] = str(self.cache_dir / "python")

        # Create .pth file for cache
        pth_file = Path("python_cache.pth")
        with open(pth_file, 'w') as f:
            f.write(str(self.cache_dir / "python"))

    def setup_node_cache(self):
        """Set up Node.js build cache."""
        # Configure Yarn cache
        try:
            subprocess.run([
                "yarn", "config", "set", "cache-folder",
                str(self.cache_dir / "node")
            ], check=True)
        except subprocess.CalledProcessError:
            pass

    def clean_cache(self, older_than_days: int = 7):
        """Clean old cache files."""
        print(f"🧹 Cleaning cache older than {older_than_days} days...")

        cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
        cleaned_count = 0

        for cache_file in self.cache_dir.rglob("*"):
            if cache_file.is_file() and cache_file.stat().st_mtime < cutoff_time:
                cache_file.unlink()
                cleaned_count += 1

        print(f"✅ Cleaned {cleaned_count} cache files")

    def generate_build_report(self) -> Dict[str, Any]:
        """Generate build optimization report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "cache_stats": {
                "cache_hits": self.manifest.get("cache_hits", 0),
                "cache_misses": self.manifest.get("cache_misses", 0),
                "hit_rate": 0
            },
            "build_stats": {
                "total_files": len(self.manifest.get("files", {})),
                "changed_files": 0,
                "parallel_jobs": self.parallel_jobs
            },
            "optimizations": {
                "incremental_build": True,
                "parallel_processing": True,
                "layer_caching": True,
                "dependency_tracking": True
            }
        }

        # Calculate hit rate
        total_requests = report["cache_stats"]["cache_hits"] + report["cache_stats"]["cache_misses"]
        if total_requests > 0:
            report["cache_stats"]["hit_rate"] = (
                report["cache_stats"]["cache_hits"] / total_requests * 100
            )

        return report

    def run_optimized_build(self, components: List[str] = None) -> bool:
        """Run optimized build for specified components."""
        if components is None:
            components = ["python", "frontend", "docker"]

        print("🚀 Starting optimized build...")
        start_time = time.time()

        # Set up cache
        self.setup_build_cache()

        success = True

        if "python" in components:
            if not self.optimize_python_build():
                success = False

        if "frontend" in components:
            if not self.optimize_frontend_build():
                success = False

        if "docker" in components:
            if not self.optimize_docker_build():
                success = False

        # Update manifest
        self.manifest["last_build"] = datetime.utcnow().isoformat()
        self.save_manifest()

        # Generate report
        report = self.generate_build_report()
        report["build_time"] = time.time() - start_time

        # Save report
        report_file = self.cache_dir / "reports" / f"build_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"⏱️  Build completed in {report['build_time']:.2f} seconds")
        print(f"📊 Report saved to {report_file}")

        return success


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Liquid Hive Build Optimizer")
    parser.add_argument("--components", nargs="+",
                       choices=["python", "frontend", "docker"],
                       default=["python", "frontend", "docker"],
                       help="Components to build")
    parser.add_argument("--cache-dir", default=".build_cache",
                       help="Cache directory path")
    parser.add_argument("--clean-cache", type=int, metavar="DAYS",
                       help="Clean cache older than specified days")
    parser.add_argument("--report-only", action="store_true",
                       help="Generate report only, don't build")

    args = parser.parse_args()

    optimizer = BuildOptimizer(args.cache_dir)

    if args.clean_cache:
        optimizer.clean_cache(args.clean_cache)
        return

    if args.report_only:
        report = optimizer.generate_build_report()
        print(json.dumps(report, indent=2))
        return

    success = optimizer.run_optimized_build(args.components)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
