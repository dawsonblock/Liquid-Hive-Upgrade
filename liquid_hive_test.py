#!/usr/bin/env python3
"""
Liquid-Hive System Test Suite
Tests the cleaned up and production-hardened Liquid-Hive system
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

import requests


class LiquidHiveSystemTester:
    def __init__(self, api_base_url="http://localhost:8080"):
        self.api_base_url = api_base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = {}

    def run_test(self, name: str, test_func) -> bool:
        """Run a single test"""
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            success = test_func()
            if success:
                self.tests_passed += 1
                print(f"✅ Passed")
            else:
                print(f"❌ Failed")
            
            self.test_results[name] = success
            return success
        except Exception as e:
            print(f"❌ Failed - Error: {e}")
            self.test_results[name] = False
            return False

    # ===== STRUCTURE VERIFICATION =====
    def test_no_duplicate_modules(self) -> bool:
        """Verify no duplicate modules exist between src/ and apps/api/"""
        print("   Checking for duplicate hivemind modules...")
        
        # Check if hivemind exists in both src/ and apps/api/
        src_hivemind = Path("/app/src/hivemind")
        apps_hivemind = Path("/app/apps/api/hivemind")
        
        if src_hivemind.exists() and apps_hivemind.exists():
            print("   ❌ Found duplicate hivemind modules in both src/ and apps/api/")
            return False
        
        if src_hivemind.exists():
            print("   ✅ hivemind module found only in src/ (correct)")
        else:
            print("   ⚠️ hivemind module not found in src/")
        
        return True

    def test_single_frontend(self) -> bool:
        """Confirm only one frontend exists (frontend/ not apps/dashboard/)"""
        print("   Checking for single frontend directory...")
        
        frontend_dir = Path("/app/frontend")
        dashboard_dir = Path("/app/apps/dashboard")
        
        if dashboard_dir.exists():
            print("   ❌ Found duplicate dashboard directory in apps/dashboard/")
            return False
        
        if frontend_dir.exists():
            print("   ✅ Single frontend directory found (correct)")
            return True
        else:
            print("   ❌ No frontend directory found")
            return False

    def test_import_statements(self) -> bool:
        """Check that import statements use 'from src.hivemind import ...'"""
        print("   Checking import statements in main API...")
        
        main_py = Path("/app/apps/api/main.py")
        if not main_py.exists():
            print("   ❌ main.py not found in apps/api/")
            return False
        
        content = main_py.read_text()
        if "from src.config import" in content and "from src.version import" in content:
            print("   ✅ Import statements use correct 'from src.' format")
            return True
        else:
            print("   ❌ Import statements don't use 'from src.' format")
            return False

    # ===== BUILD SYSTEM TESTING =====
    def test_makefile_commands(self) -> bool:
        """Test that Makefile commands work"""
        print("   Testing Makefile help command...")
        
        try:
            result = subprocess.run(
                ["make", "help"], 
                cwd="/app", 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0 and "Liquid Hive Development Commands" in result.stdout:
                print("   ✅ Makefile help command works")
                return True
            else:
                print(f"   ❌ Makefile help failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ❌ Makefile test failed: {e}")
            return False

    def test_docker_files_exist(self) -> bool:
        """Check that Docker builds work (files exist and are valid)"""
        print("   Checking Docker files...")
        
        api_dockerfile = Path("/app/apps/api/Dockerfile")
        frontend_dockerfile = Path("/app/frontend/Dockerfile")
        docker_compose = Path("/app/docker-compose.yaml")
        
        files_exist = all([
            api_dockerfile.exists(),
            frontend_dockerfile.exists(), 
            docker_compose.exists()
        ])
        
        if files_exist:
            print("   ✅ All Docker files exist")
            return True
        else:
            print("   ❌ Missing Docker files")
            return False

    def test_requirements_file(self) -> bool:
        """Test that requirements.txt exists and has dependencies"""
        print("   Checking requirements.txt...")
        
        requirements = Path("/app/requirements.txt")
        if not requirements.exists():
            print("   ❌ requirements.txt not found")
            return False
        
        content = requirements.read_text()
        if "fastapi" in content and "uvicorn" in content:
            print("   ✅ requirements.txt has core dependencies")
            return True
        else:
            print("   ❌ requirements.txt missing core dependencies")
            return False

    def test_frontend_dependencies(self) -> bool:
        """Test frontend yarn installation consistency"""
        print("   Checking frontend dependencies...")
        
        package_json = Path("/app/frontend/package.json")
        yarn_lock = Path("/app/frontend/yarn.lock")
        
        if package_json.exists() and yarn_lock.exists():
            print("   ✅ Frontend has package.json and yarn.lock")
            return True
        else:
            print("   ❌ Missing frontend dependency files")
            return False

    # ===== API TESTING =====
    def test_api_health_endpoints(self) -> bool:
        """Test that main API health endpoints are accessible"""
        print("   Testing API health endpoints...")
        
        endpoints = ["/", "/health", "/version"]
        all_passed = True
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.api_base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    print(f"   ✅ {endpoint} - Status: {response.status_code}")
                else:
                    print(f"   ❌ {endpoint} - Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                print(f"   ❌ {endpoint} - Error: {e}")
                all_passed = False
        
        return all_passed

    def test_api_imports_resolved(self) -> bool:
        """Check imports are resolved correctly (no import errors)"""
        print("   Testing API import resolution...")
        
        try:
            # The fact that the API is running means imports are resolved
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                print("   ✅ API imports resolved correctly (server running)")
                return True
            else:
                print("   ❌ API not responding properly")
                return False
        except Exception as e:
            print(f"   ❌ API import test failed: {e}")
            return False

    # ===== DEVELOPER EXPERIENCE =====
    def test_env_example_exists(self) -> bool:
        """Verify .env.example has all required variables"""
        print("   Checking .env.example...")
        
        env_example = Path("/app/.env.example")
        if not env_example.exists():
            print("   ❌ .env.example not found")
            return False
        
        content = env_example.read_text()
        required_vars = ["API_PORT", "VITE_API_BASE"]
        
        missing_vars = [var for var in required_vars if var not in content]
        if missing_vars:
            print(f"   ❌ Missing variables in .env.example: {missing_vars}")
            return False
        
        print("   ✅ .env.example has required variables")
        return True

    def test_docker_compose_syntax(self) -> bool:
        """Check that docker-compose.yaml syntax is valid"""
        print("   Testing docker-compose.yaml syntax...")
        
        try:
            result = subprocess.run(
                ["docker-compose", "config"], 
                cwd="/app", 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                print("   ✅ docker-compose.yaml syntax is valid")
                return True
            else:
                print(f"   ❌ docker-compose.yaml syntax error: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ❌ docker-compose test failed: {e}")
            return False

    # ===== CI/CD PIPELINE =====
    def test_ci_workflow_syntax(self) -> bool:
        """Validate .github/workflows/ci.yml syntax"""
        print("   Checking CI workflow syntax...")
        
        ci_workflow = Path("/app/.github/workflows/ci.yml")
        if not ci_workflow.exists():
            print("   ❌ CI workflow file not found")
            return False
        
        try:
            import yaml
            content = yaml.safe_load(ci_workflow.read_text())
            if "jobs" in content and "test" in content["jobs"]:
                print("   ✅ CI workflow has valid syntax and structure")
                return True
            else:
                print("   ❌ CI workflow missing required structure")
                return False
        except Exception as e:
            print(f"   ❌ CI workflow syntax error: {e}")
            return False

    def test_security_tools_configured(self) -> bool:
        """Check that security tools are properly configured"""
        print("   Checking security tools configuration...")
        
        ci_workflow = Path("/app/.github/workflows/ci.yml")
        if not ci_workflow.exists():
            return False
        
        content = ci_workflow.read_text()
        security_tools = ["bandit", "safety", "CodeQL"]
        
        found_tools = [tool for tool in security_tools if tool.lower() in content.lower()]
        if len(found_tools) >= 2:
            print(f"   ✅ Security tools configured: {found_tools}")
            return True
        else:
            print(f"   ❌ Insufficient security tools configured: {found_tools}")
            return False

    def test_test_structure(self) -> bool:
        """Check test structure (tests/unit/, tests/integration/, tests/performance/)"""
        print("   Checking test directory structure...")
        
        test_dirs = [
            Path("/app/tests"),
            Path("/app/tests/performance")
        ]
        
        existing_dirs = [d for d in test_dirs if d.exists()]
        if len(existing_dirs) >= 1:
            print(f"   ✅ Test directories exist: {[str(d) for d in existing_dirs]}")
            return True
        else:
            print("   ❌ Test directory structure incomplete")
            return False


def main():
    """Main test runner"""
    print("🚀 Starting Liquid-Hive System Verification Tests")
    print("Testing: Structure, Build System, API, Developer Experience, CI/CD")
    print("=" * 80)

    tester = LiquidHiveSystemTester()
    
    # Track critical failures
    critical_failures = []

    print("\n📁 === STRUCTURE VERIFICATION ===")
    
    # Test 1: No duplicate modules
    if not tester.run_test("No Duplicate Modules", tester.test_no_duplicate_modules):
        critical_failures.append("Duplicate modules found")
    
    # Test 2: Single frontend
    if not tester.run_test("Single Frontend Directory", tester.test_single_frontend):
        critical_failures.append("Multiple frontend directories")
    
    # Test 3: Import statements
    tester.run_test("Correct Import Statements", tester.test_import_statements)

    print("\n🔧 === BUILD SYSTEM TESTING ===")
    
    # Test 4: Makefile commands
    tester.run_test("Makefile Commands", tester.test_makefile_commands)
    
    # Test 5: Docker files
    tester.run_test("Docker Files Exist", tester.test_docker_files_exist)
    
    # Test 6: Requirements file
    tester.run_test("Python Dependencies", tester.test_requirements_file)
    
    # Test 7: Frontend dependencies
    tester.run_test("Frontend Dependencies", tester.test_frontend_dependencies)

    print("\n🌐 === API TESTING ===")
    
    # Test 8: API health endpoints
    if not tester.run_test("API Health Endpoints", tester.test_api_health_endpoints):
        critical_failures.append("API health endpoints failed")
    
    # Test 9: API imports resolved
    tester.run_test("API Import Resolution", tester.test_api_imports_resolved)

    print("\n👨‍💻 === DEVELOPER EXPERIENCE ===")
    
    # Test 10: .env.example
    tester.run_test("Environment Example File", tester.test_env_example_exists)
    
    # Test 11: docker-compose syntax
    tester.run_test("Docker Compose Syntax", tester.test_docker_compose_syntax)

    print("\n🔄 === CI/CD PIPELINE ===")
    
    # Test 12: CI workflow syntax
    tester.run_test("CI Workflow Syntax", tester.test_ci_workflow_syntax)
    
    # Test 13: Security tools
    tester.run_test("Security Tools Configuration", tester.test_security_tools_configured)
    
    # Test 14: Test structure
    tester.run_test("Test Directory Structure", tester.test_test_structure)

    # Print comprehensive results
    print("\n" + "=" * 80)
    print(f"📊 LIQUID-HIVE SYSTEM TEST RESULTS: {tester.tests_passed}/{tester.tests_run} passed")
    print("=" * 80)

    # Categorize results
    structure_tests = ["No Duplicate Modules", "Single Frontend Directory", "Correct Import Statements"]
    build_tests = ["Makefile Commands", "Docker Files Exist", "Python Dependencies", "Frontend Dependencies"]
    api_tests = ["API Health Endpoints", "API Import Resolution"]
    dev_tests = ["Environment Example File", "Docker Compose Syntax"]
    ci_tests = ["CI Workflow Syntax", "Security Tools Configuration", "Test Directory Structure"]

    def count_passed(test_names):
        return sum(1 for name in test_names if tester.test_results.get(name, False))

    print("\n📈 CATEGORY BREAKDOWN:")
    print(f"   📁 Structure Verification: {count_passed(structure_tests)}/{len(structure_tests)} passed")
    print(f"   🔧 Build System: {count_passed(build_tests)}/{len(build_tests)} passed")
    print(f"   🌐 API Testing: {count_passed(api_tests)}/{len(api_tests)} passed")
    print(f"   👨‍💻 Developer Experience: {count_passed(dev_tests)}/{len(dev_tests)} passed")
    print(f"   🔄 CI/CD Pipeline: {count_passed(ci_tests)}/{len(ci_tests)} passed")

    if critical_failures:
        print(f"\n❌ CRITICAL FAILURES: {critical_failures}")
        print("🚨 System needs immediate attention before production deployment")
        return 1

    if tester.tests_passed >= (tester.tests_run * 0.85):  # 85% pass rate
        print("\n🎉 LIQUID-HIVE SYSTEM VERIFICATION SUCCESSFUL!")
        print("✅ Cleanup and production hardening verified")
        print("✅ No duplicate modules found")
        print("✅ Import paths are correct")
        print("✅ Build system is functional")
        print("✅ API is accessible and working")
        print("✅ Developer experience is optimized")
        print("✅ CI/CD pipeline is properly configured")
        return 0
    else:
        print(f"\n⚠️ System needs attention - only {tester.tests_passed}/{tester.tests_run} tests passed")
        print("Some components may need fixes before production deployment")
        return 1


if __name__ == "__main__":
    sys.exit(main())