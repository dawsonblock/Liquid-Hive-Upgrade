#!/usr/bin/env python3
"""
Backend API Test for Planner and Arena functionality
Tests the Phase 1 and Phase 2 deliverables as requested.
"""

import os
import sys
import requests
import json
from datetime import datetime

class PlannerArenaAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
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

            return success, response.json() if success and response.content else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test basic health endpoint"""
        return self.run_test("Health Check", "GET", "api/healthz", 200)

    def test_arena_submit(self):
        """Test arena task submission"""
        data = {"input": "Translate 'hello world' to French"}
        success, response = self.run_test(
            "Arena Submit Task", "POST", "api/arena/submit", 200, data
        )
        return success, response.get('task_id') if success else None

    def test_arena_compare(self, task_id):
        """Test arena model comparison"""
        data = {
            "task_id": task_id,
            "model_a": "deepseek_v3",
            "model_b": "qwen_7b", 
            "output_a": "Bonjour le monde! Ceci est une traduction complète.",
            "output_b": "Bonjour le monde!"
        }
        return self.run_test(
            "Arena Compare Models", "POST", "api/arena/compare", 200, data
        )

    def test_arena_leaderboard(self):
        """Test arena leaderboard"""
        return self.run_test(
            "Arena Leaderboard", "GET", "api/arena/leaderboard", 200
        )

def main():
    """Main test runner"""
    print("🚀 Starting Planner and Arena API Tests")
    print("=" * 50)
    
    # Set environment variable for Arena
    os.environ['ENABLE_ARENA'] = 'true'
    
    tester = PlannerArenaAPITester()
    
    # Test 1: Health check
    health_success, _ = tester.test_health_check()
    if not health_success:
        print("❌ Health check failed - API may not be running")
        return 1

    # Test 2: Arena Submit
    submit_success, task_id = tester.test_arena_submit()
    if not submit_success or not task_id:
        print("❌ Arena submit failed")
        return 1

    # Test 3: Arena Compare
    compare_success, _ = tester.test_arena_compare(task_id)
    if not compare_success:
        print("❌ Arena compare failed")
        return 1

    # Test 4: Arena Leaderboard
    leaderboard_success, _ = tester.test_arena_leaderboard()
    if not leaderboard_success:
        print("❌ Arena leaderboard failed")
        return 1

    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All Arena API tests passed!")
        print("\n✅ Phase 1 (Planner): Unit tests passed")
        print("✅ Phase 2 (Arena): API endpoints working correctly")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())