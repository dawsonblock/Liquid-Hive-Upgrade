#!/usr/bin/env python3
"""Enhanced build script with better error handling and optimization."""

import subprocess
import sys
import time
from pathlib import Path
import argparse
import shutil


def run_command(
    cmd: list[str], cwd: str | None = None, check: bool = True
) -> subprocess.CompletedProcess | None:
    """Run a command with better error handling."""
    print(f"🔧 Running: {' '.join(cmd)}")
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        elapsed = time.time() - start_time
        print(f"✅ Completed in {elapsed:.1f}s")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return None


def check_prerequisites() -> bool:
    """Check if all prerequisites are available."""
    print("🔍 Checking prerequisites...")

    # Check Node.js
    node_result = run_command(["node", "--version"], check=False)
    if not node_result or node_result.returncode != 0:
        print("❌ Node.js not found")
        return False

    # Check Yarn
    yarn_result = run_command(["yarn", "--version"], check=False)
    if not yarn_result or yarn_result.returncode != 0:
        print("❌ Yarn not found")
        return False

    # Check Python
    python_result = run_command(["python3", "--version"], check=False)
    if not python_result or python_result.returncode != 0:
        print("❌ Python3 not found")
        return False

    # Check Docker
    docker_result = run_command(["docker", "--version"], check=False)
    if not docker_result or docker_result.returncode != 0:
        print("❌ Docker not found")
        return False

    print("✅ All prerequisites found")
    return True


def clean_build() -> None:
    """Clean build artifacts."""
    print("🧹 Cleaning build artifacts...")

    # Clean frontend
    frontend_clean = run_command(
        ["yarn", "clean"], cwd="frontend", check=False
    )
    if frontend_clean and frontend_clean.returncode != 0:
        print("⚠️ Frontend clean had issues, continuing...")

    # Clean Python __pycache__ directories using Python-native approach
    print("🧹 Cleaning Python __pycache__ directories...")
    project_root = Path(".")
    pycache_dirs = list(project_root.rglob("__pycache__"))

    for pycache_dir in pycache_dirs:
        if pycache_dir.is_dir():
            try:
                shutil.rmtree(pycache_dir)
                print(f"✅ Removed: {pycache_dir}")
            except OSError as e:
                print(f"⚠️ Failed to remove {pycache_dir}: {e}")

    print("✅ Cleanup completed")


def build_frontend() -> bool:
    """Build frontend with optimizations."""
    print("🏗️ Building frontend...")

    # Install dependencies
    install_result = run_command(
        ["yarn", "install", "--frozen-lockfile"], cwd="frontend"
    )
    if not install_result:
        return False

    # Build
    build_result = run_command(["yarn", "build"], cwd="frontend")
    if not build_result:
        return False

    print("✅ Frontend build completed")
    return True


def build_backend() -> bool:
    """Build backend Docker image."""
    print("🐳 Building backend Docker image...")

    build_result = run_command([
        "docker", "build",
        "-f", "apps/api/Dockerfile",
        "-t", "liquid-hive-api",
        "."
    ])

    if not build_result:
        return False

    print("✅ Backend build completed")
    return True


def run_tests() -> None:
    """Run tests if requested."""
    print("🧪 Running tests...")

    # Frontend tests
    frontend_tests = run_command(
        ["yarn", "test", "--ci"], cwd="frontend", check=False
    )
    if frontend_tests and frontend_tests.returncode != 0:
        print("⚠️ Frontend tests had issues")

    # Python tests
    python_tests = run_command(
        ["python3", "-m", "pytest", "tests/", "-v"], check=False
    )
    if python_tests and python_tests.returncode != 0:
        print("⚠️ Python tests had issues")

    print("✅ Tests completed")


def main() -> None:
    """Main build function."""
    parser = argparse.ArgumentParser(description="Enhanced Build Script")
    parser.add_argument(
        "--clean", action="store_true", help="Clean before building"
    )
    parser.add_argument("--test", action="store_true", help="Run tests")
    parser.add_argument(
        "--frontend-only", action="store_true", help="Build only frontend"
    )
    parser.add_argument(
        "--backend-only", action="store_true", help="Build only backend"
    )
    parser.add_argument(
        "--optimize", action="store_true", help="Run build optimization"
    )

    args = parser.parse_args()

    print("🚀 Starting enhanced build process...")
    start_time = time.time()

    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites check failed")
        sys.exit(1)

    # Clean if requested
    if args.clean:
        clean_build()

    success = True

    # Build frontend
    if not args.backend_only:
        if not build_frontend():
            success = False

    # Build backend
    if not args.frontend_only:
        if not build_backend():
            success = False

    # Run tests
    if args.test:
        run_tests()

    # Run optimization analysis
    if args.optimize:
        print("🔍 Running build optimization analysis...")
        opt_result = run_command(
            ["python3", "scripts/build_optimizer.py"], check=False
        )
        if opt_result:
            # Always print stdout if present
            if opt_result.stdout:
                print(opt_result.stdout)
            # Always print stderr if present
            if opt_result.stderr:
                print(f"STDERR: {opt_result.stderr}")
            # Check return code and handle failures
            if opt_result.returncode != 0:
                print(
                    f"❌ Build optimization failed with exit code "
                    f"{opt_result.returncode}"
                )
                success = False

    elapsed = time.time() - start_time

    if success:
        print(f"\n🎉 Build completed successfully in {elapsed:.1f}s")
    else:
        print(f"\n❌ Build failed after {elapsed:.1f}s")
        sys.exit(1)


if __name__ == "__main__":
    main()
