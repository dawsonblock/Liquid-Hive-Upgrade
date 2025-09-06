#!/usr/bin/env python3
"""
Comprehensive build verification script for Liquid Hive.
Verifies all components are working correctly.
"""

import os
import sys
import subprocess
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class BuildVerifier:
    """Comprehensive build verification system."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "tests": []
        }
        self.services = {
            "api": {"port": 8001, "health_endpoint": "/health"},
            "frontend": {"port": 3000, "health_endpoint": "/"},
            "feedback": {"port": 8091, "health_endpoint": "/health"},
            "oracle": {"port": 8092, "health_endpoint": "/health"}
        }

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def add_test_result(self, name: str, passed: bool, message: str, warning: bool = False):
        """Add a test result."""
        self.results["tests"].append({
            "name": name,
            "passed": passed,
            "message": message,
            "warning": warning
        })

        if passed:
            self.results["passed"] += 1
            self.log(f"✅ {name}: {message}", "PASS")
        elif warning:
            self.results["warnings"] += 1
            self.log(f"⚠️  {name}: {message}", "WARN")
        else:
            self.results["failed"] += 1
            self.log(f"❌ {name}: {message}", "FAIL")

    def check_python_environment(self) -> bool:
        """Check Python environment and dependencies."""
        try:
            # Check Python version
            python_version = sys.version_info
            if python_version < (3, 11):
                self.add_test_result(
                    "Python Version",
                    False,
                    f"Python {python_version.major}.{python_version.minor} is below required 3.11+"
                )
                return False
            else:
                self.add_test_result(
                    "Python Version",
                    True,
                    f"Python {python_version.major}.{python_version.minor}.{python_version.micro}"
                )

            # Check critical imports
            critical_modules = [
                'fastapi', 'uvicorn', 'pydantic', 'redis', 'sqlalchemy',
                'psutil', 'structlog', 'httpx'
            ]

            missing_modules = []
            for module in critical_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)

            if missing_modules:
                self.add_test_result(
                    "Python Dependencies",
                    False,
                    f"Missing modules: {', '.join(missing_modules)}"
                )
                return False
            else:
                self.add_test_result(
                    "Python Dependencies",
                    True,
                    f"All {len(critical_modules)} critical modules available"
                )

            return True

        except Exception as e:
            self.add_test_result("Python Environment", False, f"Error: {str(e)}")
            return False

    def check_node_environment(self) -> bool:
        """Check Node.js environment and dependencies."""
        try:
            # Check Node version
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                self.add_test_result("Node.js", False, "Node.js not installed")
                return False

            node_version = result.stdout.strip()
            self.add_test_result("Node.js", True, f"Version {node_version}")

            # Check Yarn
            result = subprocess.run(['yarn', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                self.add_test_result("Yarn", False, "Yarn not installed")
                return False

            yarn_version = result.stdout.strip()
            self.add_test_result("Yarn", True, f"Version {yarn_version}")

            # Check frontend dependencies
            frontend_dir = self.project_root / "frontend"
            if not frontend_dir.exists():
                self.add_test_result("Frontend Directory", False, "Frontend directory not found")
                return False

            # Check if node_modules exists
            node_modules = frontend_dir / "node_modules"
            if not node_modules.exists():
                self.add_test_result("Frontend Dependencies", False, "node_modules not found, run 'yarn install'")
                return False

            self.add_test_result("Frontend Dependencies", True, "Dependencies installed")
            return True

        except Exception as e:
            self.add_test_result("Node Environment", False, f"Error: {str(e)}")
            return False

    def check_docker_environment(self) -> bool:
        """Check Docker environment."""
        try:
            # Check Docker
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                self.add_test_result("Docker", False, "Docker not installed")
                return False

            docker_version = result.stdout.strip()
            self.add_test_result("Docker", True, f"Version {docker_version}")

            # Check Docker Compose
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                self.add_test_result("Docker Compose", False, "Docker Compose not installed")
                return False

            compose_version = result.stdout.strip()
            self.add_test_result("Docker Compose", True, f"Version {compose_version}")

            return True

        except Exception as e:
            self.add_test_result("Docker Environment", False, f"Error: {str(e)}")
            return False

    def check_file_structure(self) -> bool:
        """Check project file structure."""
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
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if missing_files:
            self.add_test_result(
                "File Structure",
                False,
                f"Missing files: {', '.join(missing_files)}"
            )
            return False
        else:
            self.add_test_result(
                "File Structure",
                True,
                f"All {len(required_files)} required files present"
            )
            return True

    def check_build_artifacts(self) -> bool:
        """Check for unwanted build artifacts."""
        artifacts = []

        # Check for Python cache files
        for root, dirs, files in os.walk(self.project_root):
            if '__pycache__' in dirs:
                artifacts.append(f"{root}/__pycache__")
            if '.pytest_cache' in dirs:
                artifacts.append(f"{root}/.pytest_cache")
            if '.mypy_cache' in dirs:
                artifacts.append(f"{root}/.mypy_cache")

        # Check for generated JS files in src/
        for root, dirs, files in os.walk(self.project_root / "src"):
            for file in files:
                if file.endswith('.js') and not file.startswith('.'):
                    artifacts.append(f"{root}/{file}")

        if artifacts:
            self.add_test_result(
                "Build Artifacts",
                True,
                f"Found {len(artifacts)} artifacts (run cleanup to remove)",
                warning=True
            )
        else:
            self.add_test_result("Build Artifacts", True, "No unwanted artifacts found")

        return True

    def check_docker_builds(self) -> bool:
        """Check if Docker images can be built."""
        dockerfiles = [
            "apps/api/Dockerfile",
            "frontend/Dockerfile",
            "services/feedback_api/Dockerfile",
            "services/oracle_api/Dockerfile"
        ]

        all_built = True
        for dockerfile in dockerfiles:
            dockerfile_path = self.project_root / dockerfile
            if not dockerfile_path.exists():
                self.add_test_result(f"Dockerfile {dockerfile}", False, "File not found")
                all_built = False
                continue

            # Try to validate Dockerfile syntax
            try:
                result = subprocess.run([
                    'docker', 'build', '--no-cache', '--progress=plain', '-f', str(dockerfile_path), str(self.project_root)
                ], capture_output=True, text=True, timeout=60, cwd=str(self.project_root))

                if result.returncode == 0:
                    self.add_test_result(f"Dockerfile {dockerfile}", True, "Build validation passed")
                else:
                    self.add_test_result(f"Dockerfile {dockerfile}", False, f"Build failed: {result.stderr}")
                    all_built = False

            except subprocess.TimeoutExpired:
                self.add_test_result(f"Dockerfile {dockerfile}", False, "Build timeout")
                all_built = False
            except Exception as e:
                self.add_test_result(f"Dockerfile {dockerfile}", False, f"Error: {str(e)}")
                all_built = False

        return all_built

    def check_services_health(self) -> bool:
        """Check if services are healthy."""
        healthy_services = 0
        total_services = len(self.services)

        for service_name, config in self.services.items():
            try:
                url = f"http://localhost:{config['port']}{config['health_endpoint']}"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    self.add_test_result(f"Service {service_name}", True, f"Healthy on port {config['port']}")
                    healthy_services += 1
                else:
                    self.add_test_result(f"Service {service_name}", False, f"Unhealthy: HTTP {response.status_code}")

            except requests.exceptions.RequestException as e:
                self.add_test_result(f"Service {service_name}", False, f"Not running (expected if not started): {str(e)}", warning=True)

        return healthy_services > 0

    def search_pattern_in_files(self, directory: str, pattern: str, file_extensions: tuple, exclude_dirs: set) -> int:
        """Search for a pattern in files using Python-native traversal."""
        count = 0

        for root, dirs, files in os.walk(directory):
            # Remove excluded directories from dirs list to prevent os.walk from descending into them
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file.endswith(file_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if pattern in line:
                                    count += 1
                    except (IOError, UnicodeDecodeError):
                        # Skip files that can't be read
                        continue

        return count

    def check_code_quality(self) -> bool:
        """Check code quality metrics."""
        try:
            # Check for print statements using Python-native search
            print_count = self.search_pattern_in_files(
                'src/', 'print(', ('.py',), {'__pycache__'}
            )

            if print_count > 0:
                self.add_test_result(
                    "Code Quality",
                    True,
                    f"Found {print_count} print statements (consider using logger)",
                    warning=True
                )
            else:
                self.add_test_result("Code Quality", True, "No print statements found")

            # Check for console.log using Python-native search
            console_count = self.search_pattern_in_files(
                'frontend/src/', 'console.log', ('.js', '.ts', '.tsx', '.jsx'), {'node_modules'}
            )

            if console_count > 0:
                self.add_test_result(
                    "Frontend Code Quality",
                    True,
                    f"Found {console_count} console.log statements (consider using proper logging)",
                    warning=True
                )
            else:
                self.add_test_result("Frontend Code Quality", True, "No console.log statements found")

            return True

        except Exception as e:
            self.add_test_result("Code Quality", False, f"Error: {str(e)}")
            return False

    def run_verification(self) -> bool:
        """Run complete verification suite."""
        self.log("Starting Liquid Hive Build Verification", "INFO")
        self.log("=" * 50, "INFO")

        # Run all checks
        checks = [
            ("Python Environment", self.check_python_environment),
            ("Node Environment", self.check_node_environment),
            ("Docker Environment", self.check_docker_environment),
            ("File Structure", self.check_file_structure),
            ("Build Artifacts", self.check_build_artifacts),
            ("Docker Builds", self.check_docker_builds),
            ("Services Health", self.check_services_health),
            ("Code Quality", self.check_code_quality)
        ]

        for check_name, check_func in checks:
            self.log(f"Running {check_name} check...", "INFO")
            try:
                check_func()
            except Exception as e:
                self.add_test_result(check_name, False, f"Check failed: {str(e)}")

        # Print summary
        self.log("=" * 50, "INFO")
        self.log("VERIFICATION SUMMARY", "INFO")
        self.log(f"Passed: {self.results['passed']}", "INFO")
        self.log(f"Failed: {self.results['failed']}", "INFO")
        self.log(f"Warnings: {self.results['warnings']}", "INFO")

        # Overall status
        if self.results['failed'] == 0:
            self.log("🎉 BUILD VERIFICATION PASSED", "PASS")
            return True
        else:
            self.log("❌ BUILD VERIFICATION FAILED", "FAIL")
            return False

    def save_report(self, filename: str = "build_verification_report.json"):
        """Save verification report to file."""
        report_path = self.project_root / filename
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        self.log(f"Report saved to {report_path}", "INFO")


def main():
    """Main function."""
    verifier = BuildVerifier()

    try:
        success = verifier.run_verification()
        verifier.save_report()

        if success:
            print("\n🎉 All checks passed! Your build is ready for production.")
            sys.exit(0)
        else:
            print("\n❌ Some checks failed. Please review the issues above.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Verification failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
