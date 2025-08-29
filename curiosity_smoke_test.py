#!/usr/bin/env python3
"""
Backend API Smoke Test for CuriosityEngine and Decorator Fixes
==============================================================

This script tests the specific endpoints mentioned in the review request:
1) GET http://127.0.0.1:8001/api/healthz -> expect 200 JSON with key ok
2) GET http://127.0.0.1:8001/api/approvals -> expect 200 JSON list
3) POST http://127.0.0.1:8001/api/chat with form field q="trigger curiosity" -> expect 200 JSON with key answer (string)
4) Validate adapters endpoints still OK: GET /api/adapters and /api/adapters/state
"""

import requests
import json
import sys
from datetime import datetime

class CuriosityEngineAPITester:
    def __init__(self, base_url="http://127.0.0.1:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()

    def log(self, message):
        """Log with timestamp"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status=200, data=None, form_data=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        
        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        self.log(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, timeout=15)
            elif method == 'POST':
                if form_data:
                    response = self.session.post(url, data=form_data, timeout=15)
                elif data:
                    response = self.session.post(url, json=data, timeout=15)
                else:
                    response = self.session.post(url, timeout=15)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    json_response = response.json()
                    # Show brief snippet for concise output
                    snippet = str(json_response)[:150] + "..." if len(str(json_response)) > 150 else str(json_response)
                    self.log(f"   Response: {snippet}")
                    return True, json_response
                except:
                    self.log(f"   Response text: {response.text[:100]}...")
                    return True, response.text
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            return False, {}

    def test_healthz(self):
        """Test 1: GET /api/healthz -> expect 200 JSON with key ok"""
        success, response = self.run_test("Health Check", "GET", "/api/healthz")
        if success and isinstance(response, dict) and "ok" in response:
            self.log(f"   ✓ Contains 'ok' key with value: {response['ok']}")
            return True
        else:
            self.log("   ✗ Missing 'ok' key or wrong format")
            return False

    def test_approvals(self):
        """Test 2: GET /api/approvals -> expect 200 JSON list"""
        success, response = self.run_test("Approvals List", "GET", "/api/approvals")
        if success and isinstance(response, list):
            self.log(f"   ✓ Returns list with {len(response)} items")
            return True
        else:
            self.log("   ✗ Response format incorrect (expected list)")
            return False

    def test_chat_curiosity(self):
        """Test 3: POST /api/chat with form field q="trigger curiosity" -> expect 200 JSON with key answer"""
        success, response = self.run_test("Chat Curiosity Trigger", "POST", "/api/chat?q=trigger%20curiosity")
        if success and isinstance(response, dict):
            if "answer" in response and isinstance(response["answer"], str):
                self.log(f"   ✓ Contains 'answer' key (string)")
                answer_preview = response["answer"][:100] + "..." if len(response["answer"]) > 100 else response["answer"]
                self.log(f"   Answer: {answer_preview}")
                return True
            else:
                self.log("   ✗ Missing 'answer' key or not a string")
                return False
        else:
            self.log("   ✗ Response format incorrect (expected dict)")
            return False

    def test_adapters(self):
        """Test 4a: GET /api/adapters -> validate still OK"""
        success, response = self.run_test("Adapters List", "GET", "/api/adapters")
        if success and isinstance(response, list):
            self.log(f"   ✓ Adapters endpoint still OK - {len(response)} items")
            return True
        else:
            self.log("   ✗ Adapters endpoint issue")
            return False

    def test_adapters_state(self):
        """Test 4b: GET /api/adapters/state -> validate still OK"""
        success, response = self.run_test("Adapters State", "GET", "/api/adapters/state")
        if success and isinstance(response, dict):
            if "state" in response or "error" in response:
                self.log(f"   ✓ Adapters state endpoint still OK")
                return True
            else:
                self.log("   ✗ Adapters state unexpected format")
                return False
        else:
            self.log("   ✗ Adapters state endpoint issue")
            return False

    def run_smoke_tests(self):
        """Run the specific smoke tests for CuriosityEngine"""
        self.log("🚀 CuriosityEngine & Decorator Fixes - Smoke Test")
        self.log("=" * 60)
        
        # Test 1: Health check
        self.test_healthz()
        
        # Test 2: Approvals list
        self.test_approvals()
        
        # Test 3: Chat with curiosity trigger
        self.test_chat_curiosity()
        
        # Test 4: Validate adapters endpoints still work
        self.test_adapters()
        self.test_adapters_state()
        
        # Print summary
        self.log("=" * 60)
        self.log(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            self.log("🎉 All smoke tests passed!")
            return 0
        else:
            self.log("⚠️  Some tests failed")
            return 1

def main():
    """Main test runner"""
    tester = CuriosityEngineAPITester()
    return tester.run_smoke_tests()

if __name__ == "__main__":
    sys.exit(main())