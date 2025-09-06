#!/usr/bin/env python3
"""
Quick build verification script for Liquid Hive.
Checks code quality without building Docker images.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python_environment():
    """Check Python environment."""
    print("🔍 Checking Python environment...")

    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 11):
        print(f"❌ Python {python_version.major}.{python_version.minor} is below required 3.11+")
        return False
    else:
        print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")

    # Check critical imports
    critical_modules = ['fastapi', 'uvicorn', 'pydantic', 'redis', 'sqlalchemy', 'psutil', 'structlog']
    missing_modules = []

    for module in critical_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        print(f"❌ Missing modules: {', '.join(missing_modules)}")
        return False
    else:
        print(f"✅ All {len(critical_modules)} critical modules available")

    return True


def check_node_environment():
    """Check Node.js environment."""
    print("🔍 Checking Node.js environment...")

    # Check Node version
    result = subprocess.run(['node', '--version'], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Node.js not installed")
        return False

    print(f"✅ Node.js {result.stdout.strip()}")

    # Check Yarn
    result = subprocess.run(['yarn', '--version'], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Yarn not installed")
        return False

    print(f"✅ Yarn {result.stdout.strip()}")

    # Check frontend dependencies
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False

    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("❌ node_modules not found, run 'yarn install'")
        return False

    print("✅ Frontend dependencies installed")
    return True


def check_code_quality():
    """Check code quality."""
    print("🔍 Checking code quality...")

    # Check for print statements
    result = subprocess.run(['grep', '-r', 'print(', 'src/', '--exclude-dir=__pycache__'], capture_output=True, text=True)
    print_count = len(result.stdout.splitlines()) if result.returncode == 0 else 0

    if print_count > 0:
        print(f"⚠️  Found {print_count} print statements (consider using logger)")
    else:
        print("✅ No print statements found")

    # Check for console.log
    result = subprocess.run(['grep', '-r', 'console.log', 'frontend/src/', '--exclude-dir=node_modules'], capture_output=True, text=True)
    console_count = len(result.stdout.splitlines()) if result.returncode == 0 else 0

    if console_count > 0:
        print(f"⚠️  Found {console_count} console.log statements (consider using proper logging)")
    else:
        print("✅ No console.log statements found")

    return True


def check_file_structure():
    """Check project file structure."""
    print("🔍 Checking file structure...")

    required_files = [
        "requirements.txt",
        "docker-compose.yaml",
        "Makefile",
        ".env.example",
        "pyproject.toml",
        "src/config.py",
        "src/version.py",
        "apps/api/main.py",
        "frontend/package.json",
        "frontend/vite.config.ts"
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    else:
        print(f"✅ All {len(required_files)} required files present")
        return True


def check_build_artifacts():
    """Check for unwanted build artifacts."""
    print("🔍 Checking build artifacts...")

    artifacts = []

    # Check for Python cache files
    for root, dirs, files in os.walk("."):
        if '__pycache__' in dirs:
            artifacts.append(f"{root}/__pycache__")
        if '.pytest_cache' in dirs:
            artifacts.append(f"{root}/.pytest_cache")
        if '.mypy_cache' in dirs:
            artifacts.append(f"{root}/.mypy_cache")

    # Check for generated JS files in src/
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith('.js') and not file.startswith('.'):
                artifacts.append(f"{root}/{file}")

    if artifacts:
        print(f"⚠️  Found {len(artifacts)} artifacts (run cleanup to remove)")
    else:
        print("✅ No unwanted artifacts found")

    return True


def main():
    """Main function."""
    print("🚀 Liquid Hive Quick Build Verification")
    print("=" * 50)

    checks = [
        ("Python Environment", check_python_environment),
        ("Node Environment", check_node_environment),
        ("File Structure", check_file_structure),
        ("Build Artifacts", check_build_artifacts),
        ("Code Quality", check_code_quality)
    ]

    passed = 0
    failed = 0

    for check_name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {check_name} check failed: {e}")
            failed += 1
        print()

    print("=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL CHECKS PASSED! Your build is ready.")
        return True
    else:
        print(f"\n❌ {failed} checks failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
