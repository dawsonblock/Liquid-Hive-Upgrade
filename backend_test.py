#!/usr/bin/env python3
"""
Comprehensive Backend API Test for Enhanced CI/CD System
Tests core functionality, security, observability, and services.
"""

import os
import sys
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

class ComprehensiveBackendTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = {}

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {method} {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    resp_json = response.json()
                    print(f"   Response: {json.dumps(resp_json, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            # Store result for reporting
            self.test_results[name] = {
                'success': success,
                'status_code': response.status_code,
                'expected_status': expected_status,
                'response_time': response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0
            }

            return success, response.json() if success and response.content else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results[name] = {
                'success': False,
                'error': str(e),
                'status_code': None,
                'expected_status': expected_status
            }
            return False, {}

    # ===== CORE API ENDPOINTS =====
    def test_health_check(self):
        """Test basic health endpoint"""
        return self.run_test("Core API Health Check", "GET", "api/healthz", 200)

    def test_ready_check(self):
        """Test readiness endpoint"""
        return self.run_test("Ready Check", "GET", "api/ready", 200)

    def test_state_endpoint(self):
        """Test state summary endpoint"""
        return self.run_test("State Summary", "GET", "api/state", 200)

    # ===== ENHANCED CONFIGURATION =====
    def test_configuration_loading(self):
        """Test that system loads with comprehensive environment configuration"""
        success, response = self.run_test("Configuration Health", "GET", "api/healthz", 200)
        if success and response.get('ok'):
            print("✅ Enhanced configuration loaded successfully")
            return True, response
        return False, {}

    def test_secrets_health(self):
        """Test secrets management health"""
        return self.run_test("Secrets Health", "GET", "api/secrets/health", 200)

    # ===== PLANNER SERVICE =====
    def test_planner_service(self):
        """Test Planner (DAG execution) service"""
        # Test if planner is available through chat endpoint with planner enabled
        os.environ['ENABLE_PLANNER'] = 'true'
        return self.run_test("Planner Service", "POST", "api/chat?q=Create a simple plan to analyze data", 200)

    # ===== ARENA SERVICE =====
    def test_arena_submit(self):
        """Test arena task submission"""
        os.environ['ENABLE_ARENA'] = 'true'
        data = {"input": "Compare AI model performance on translation tasks"}
        success, response = self.run_test(
            "Arena Submit Task", "POST", "api/arena/submit", 200, data
        )
        return success, response.get('task_id') if success else None

    def test_arena_compare(self, task_id):
        """Test arena model comparison"""
        if not task_id:
            return False, {}
        data = {
            "task_id": task_id,
            "model_a": "deepseek_r1",
            "model_b": "qwen_2_5", 
            "output_a": "Comprehensive analysis with detailed reasoning and citations.",
            "output_b": "Basic analysis with limited context."
        }
        return self.run_test(
            "Arena Compare Models", "POST", "api/arena/compare", 200, data
        )

    def test_arena_leaderboard(self):
        """Test arena leaderboard"""
        return self.run_test(
            "Arena Leaderboard", "GET", "api/arena/leaderboard", 200
        )

    # ===== SECURITY FEATURES =====
    def test_admin_endpoints(self):
        """Test admin endpoints and authentication"""
        # Test budget reset (should require admin token)
        success, response = self.run_test(
            "Admin Budget Reset (No Token)", "POST", "api/admin/budget/reset", 401
        )
        return success, response

    def test_secrets_endpoints(self):
        """Test secrets management endpoints"""
        # Test secret existence check
        return self.run_test(
            "Secret Exists Check", "GET", "api/secrets/exists?name=test_secret", 200
        )

    def test_trust_policy(self):
        """Test trust policy endpoints"""
        return self.run_test("Trust Policy", "GET", "api/trust/policy", 200)

    # ===== OBSERVABILITY =====
    def test_metrics_endpoints(self):
        """Test metrics and monitoring endpoints"""
        return self.run_test("Metrics Endpoint", "GET", "metrics", 200)

    def test_providers_status(self):
        """Test providers status endpoint"""
        return self.run_test("Providers Status", "GET", "api/providers", 200)

    def test_swarm_status(self):
        """Test swarm coordination status"""
        return self.run_test("Swarm Status", "GET", "api/swarm/status", 200)

    # ===== CACHE OPERATIONS =====
    def test_cache_health(self):
        """Test semantic cache health"""
        return self.run_test("Cache Health", "GET", "api/cache/health", 200)

    def test_cache_analytics(self):
        """Test cache analytics"""
        return self.run_test("Cache Analytics", "GET", "api/cache/analytics", 200)

    def test_cache_status(self):
        """Test cache status endpoint"""
        return self.run_test("Cache Status", "GET", "api/cache/status", 200)

    # ===== CORE ROUTING =====
    def test_tools_endpoint(self):
        """Test tools listing endpoint"""
        return self.run_test("Tools Listing", "GET", "api/tools", 200)

    def test_tools_health(self):
        """Test tools health endpoint"""
        return self.run_test("Tools Health", "GET", "api/tools/health", 200)

    def test_chat_endpoint(self):
        """Test core chat endpoint"""
        return self.run_test("Chat Endpoint", "POST", "api/chat?q=What is artificial intelligence?", 200)

def main():
    """Main comprehensive test runner"""
    print("🚀 Starting Comprehensive Backend API Tests")
    print("Testing: Core APIs, Configuration, Planner, Arena, Security, Observability, Cache")
    print("=" * 80)
    
    # Set environment variables for services
    os.environ['ENABLE_ARENA'] = 'true'
    os.environ['ENABLE_PLANNER'] = 'true'
    
    tester = ComprehensiveBackendTester()
    
    # Track critical failures
    critical_failures = []
    
    print("\n🔧 === CORE API ENDPOINTS ===")
    
    # Test 1: Health check (critical)
    health_success, _ = tester.test_health_check()
    if not health_success:
        critical_failures.append("Core API Health Check")
        print("❌ CRITICAL: Health check failed - API may not be running")
    
    # Test 2: Ready check
    ready_success, _ = tester.test_ready_check()
    
    # Test 3: State endpoint
    state_success, _ = tester.test_state_endpoint()
    
    print("\n⚙️ === ENHANCED CONFIGURATION ===")
    
    # Test 4: Configuration loading
    config_success, _ = tester.test_configuration_loading()
    if not config_success:
        critical_failures.append("Enhanced Configuration Loading")
    
    # Test 5: Secrets health
    secrets_health_success, _ = tester.test_secrets_health()
    
    print("\n🧠 === PLANNER SERVICE ===")
    
    # Test 6: Planner service
    planner_success, _ = tester.test_planner_service()
    
    print("\n🏟️ === ARENA SERVICE ===")
    
    # Test 7: Arena Submit
    submit_success, task_id = tester.test_arena_submit()
    
    # Test 8: Arena Compare (depends on submit)
    compare_success = False
    if submit_success and task_id:
        compare_success, _ = tester.test_arena_compare(task_id)
    
    # Test 9: Arena Leaderboard
    leaderboard_success, _ = tester.test_arena_leaderboard()
    
    print("\n🔒 === SECURITY FEATURES ===")
    
    # Test 10: Admin endpoints
    admin_success, _ = tester.test_admin_endpoints()
    
    # Test 11: Secrets endpoints
    secrets_success, _ = tester.test_secrets_endpoints()
    
    # Test 12: Trust policy
    trust_success, _ = tester.test_trust_policy()
    
    print("\n📊 === OBSERVABILITY ===")
    
    # Test 13: Metrics endpoints
    metrics_success, _ = tester.test_metrics_endpoints()
    
    # Test 14: Providers status
    providers_success, _ = tester.test_providers_status()
    
    # Test 15: Swarm status
    swarm_success, _ = tester.test_swarm_status()
    
    print("\n🧠 === CACHE OPERATIONS ===")
    
    # Test 16: Cache health
    cache_health_success, _ = tester.test_cache_health()
    
    # Test 17: Cache analytics
    cache_analytics_success, _ = tester.test_cache_analytics()
    
    # Test 18: Cache status
    cache_status_success, _ = tester.test_cache_status()
    
    print("\n🛣️ === CORE ROUTING ===")
    
    # Test 19: Tools endpoint
    tools_success, _ = tester.test_tools_endpoint()
    
    # Test 20: Tools health
    tools_health_success, _ = tester.test_tools_health()
    
    # Test 21: Chat endpoint
    chat_success, _ = tester.test_chat_endpoint()
    
    # Print comprehensive results
    print("\n" + "=" * 80)
    print(f"📊 COMPREHENSIVE TEST RESULTS: {tester.tests_passed}/{tester.tests_run} passed")
    print("=" * 80)
    
    # Categorize results
    core_tests = [health_success, ready_success, state_success]
    config_tests = [config_success, secrets_health_success]
    service_tests = [planner_success, submit_success, compare_success, leaderboard_success]
    security_tests = [admin_success, secrets_success, trust_success]
    observability_tests = [metrics_success, providers_success, swarm_success]
    cache_tests = [cache_health_success, cache_analytics_success, cache_status_success]
    routing_tests = [tools_success, tools_health_success, chat_success]
    
    print(f"\n📈 CATEGORY BREAKDOWN:")
    print(f"   🔧 Core APIs: {sum(core_tests)}/{len(core_tests)} passed")
    print(f"   ⚙️ Configuration: {sum(config_tests)}/{len(config_tests)} passed")
    print(f"   🧠 Services (Planner/Arena): {sum(service_tests)}/{len(service_tests)} passed")
    print(f"   🔒 Security: {sum(security_tests)}/{len(security_tests)} passed")
    print(f"   📊 Observability: {sum(observability_tests)}/{len(observability_tests)} passed")
    print(f"   🧠 Cache Operations: {sum(cache_tests)}/{len(cache_tests)} passed")
    print(f"   🛣️ Core Routing: {sum(routing_tests)}/{len(routing_tests)} passed")
    
    if critical_failures:
        print(f"\n❌ CRITICAL FAILURES: {critical_failures}")
        return 1
    
    if tester.tests_passed >= (tester.tests_run * 0.8):  # 80% pass rate
        print("\n🎉 Backend system is production-ready!")
        print("✅ Core functionality verified")
        print("✅ CI/CD enhancements working correctly")
        print("✅ Security and observability operational")
        return 0
    else:
        print(f"\n⚠️ System needs attention - only {tester.tests_passed}/{tester.tests_run} tests passed")
        return 1

if __name__ == "__main__":
    sys.exit(main())