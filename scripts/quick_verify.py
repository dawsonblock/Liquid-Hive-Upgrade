#!/usr/bin/env python3
"""
Quick build verification script for Liquid Hive.
Checks code quality without building Docker images.
Enhanced with better error handling and cross-platform support.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import time


class BuildVerifier:
    """Enhanced build verification with cross-platform support."""

    def __init__(self):
        self.platform = platform.system().lower()
        self.results = {
            "timestamp": time.time(),
            "platform": self.platform,
            "python_version": sys.version,
            "checks": {}
        }
        self.errors = []
        self.warnings = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp and level."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.log(f"❌ {message}", "ERROR")

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
        self.log(f"⚠️  {message}", "WARN")

    def add_success(self, message: str):
        """Add a success message."""
        self.log(f"✅ {message}", "SUCCESS")

def check_python_environment() -> bool:
    """Check Python environment with enhanced error handling."""
    print("🔍 Checking Python environment...")
    verifier = BuildVerifier()

    try:
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 11):
            verifier.add_error(f"Python {python_version.major}.{python_version.minor} is below required 3.11+")
            return False
        else:
            verifier.add_success(f"Python {python_version.major}.{python_version.minor}.{python_version.micro}")

        # Check critical imports with detailed error reporting
        critical_modules = [
            'fastapi', 'uvicorn', 'pydantic', 'redis',
            'sqlalchemy', 'psutil', 'structlog', 'httpx'
        ]
        missing_modules = []
        import_errors = {}

        for module in critical_modules:
            try:
                __import__(module)
            except ImportError as e:
                missing_modules.append(module)
                import_errors[module] = str(e)
            except Exception as e:
                missing_modules.append(module)
                import_errors[module] = f"Unexpected error: {str(e)}"

        if missing_modules:
            verifier.add_error(f"Missing modules: {', '.join(missing_modules)}")
            for module, error in import_errors.items():
                verifier.log(f"  {module}: {error}", "DEBUG")
            return False
        else:
            verifier.add_success(f"All {len(critical_modules)} critical modules available")

        return True

    except Exception as e:
        verifier.add_error(f"Failed to check Python environment: {str(e)}")
        return False


def find_command(command: str) -> Optional[str]:
    """Find command in PATH with cross-platform support."""
    if platform.system().lower() == "windows":
        # On Windows, try .exe and .cmd extensions
        for ext in ['', '.exe', '.cmd', '.bat']:
            cmd_path = shutil.which(f"{command}{ext}")
            if cmd_path:
                return cmd_path
    else:
        return shutil.which(command)
    return None

def run_command_safe(command: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
    """Run command safely with timeout and error handling."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return False, "", f"Command not found: {command[0]}"
    except Exception as e:
        return False, "", str(e)

def check_node_environment() -> bool:
    """Check Node.js environment with enhanced cross-platform support."""
    print("🔍 Checking Node.js environment...")
    verifier = BuildVerifier()

    try:
        # Check Node.js
        node_cmd = find_command("node")
        if not node_cmd:
            verifier.add_error("Node.js not found in PATH")
            return False

        success, stdout, stderr = run_command_safe([node_cmd, "--version"])
        if not success:
            verifier.add_error(f"Node.js version check failed: {stderr}")
            return False

        verifier.add_success(f"Node.js {stdout}")

        # Check Yarn
        yarn_cmd = find_command("yarn")
        if not yarn_cmd:
            verifier.add_error("Yarn not found in PATH")
            return False

        success, stdout, stderr = run_command_safe([yarn_cmd, "--version"])
        if not success:
            verifier.add_error(f"Yarn version check failed: {stderr}")
            return False

        verifier.add_success(f"Yarn {stdout}")

        # Check frontend dependencies
        frontend_dir = Path("frontend")
        if not frontend_dir.exists():
            verifier.add_error("Frontend directory not found")
            return False

        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            verifier.add_error("node_modules not found, run 'yarn install'")
            return False

        # Check package.json
        package_json = frontend_dir / "package.json"
        if not package_json.exists():
            verifier.add_error("package.json not found in frontend directory")
            return False

        verifier.add_success("Frontend dependencies installed")
        return True

    except Exception as e:
        verifier.add_error(f"Failed to check Node.js environment: {str(e)}")
        return False


def check_code_quality():
    """Check code quality."""
    print("🔍 Checking code quality...")

    # Check for print statements using Python-native search
    print_count = 0
    exclude_dirs = {'__pycache__'}

    for root, dirs, files in os.walk('src/'):
        # Remove excluded directories from dirs list to prevent os.walk from descending into them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if 'print(' in line:
                                print_count += 1
                except (IOError, UnicodeDecodeError):
                    # Skip files that can't be read
                    continue

    if print_count > 0:
        print(f"⚠️  Found {print_count} print statements (consider using logger)")
    else:
        print("✅ No print statements found")

    # Check for console.log using Python-native search
    console_count = 0
    exclude_dirs = {'node_modules'}

    for root, dirs, files in os.walk('frontend/src/'):
        # Remove excluded directories from dirs list to prevent os.walk from descending into them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(('.js', '.ts', '.tsx', '.jsx')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if 'console.log' in line:
                                console_count += 1
                except (IOError, UnicodeDecodeError):
                    # Skip files that can't be read
                    continue

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

    # Check for generated JS files in src/ (exclude legitimate GUI files)
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith('.js') and not file.startswith('.'):
                # Exclude legitimate GUI files
                if not (root.endswith('capsule_brain/gui/static') and file == 'app.js'):
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
