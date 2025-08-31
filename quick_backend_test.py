#!/usr/bin/env python3
"""
Quick Backend Test for LIQUID-HIVE System
"""

import requests
import json
import sys
import time
from datetime import datetime

class QuickTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp and level"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def run_test(self, name: str, method: str, endpoint: str, 
                 expected_status: int = 200, data: dict = None, 
                 params: dict = None, timeout: int = 10) -> tuple[bool, any]:
        """Run a single API test"""
        url = f"{self.api_base}{endpoint}"
        
        self.tests_run += 1
        self.log(f"🔍 Testing {name}")
        self.log(f"   URL: {url}")
        
        try:
            headers = {'Content-Type': 'application/json'}
            
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=timeout)
            elif method == 'POST':
                if data:
                    response = requests.post(url, json=data, params=params, headers=headers, timeout=timeout)
                else:
                    response = requests.post(url, params=params, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            self.log(f"   Status: {response.status_code}")
            
            if response.status_code != expected_status:
                self.log(f"   ❌ Expected status {expected_status}, got {response.status_code}", "ERROR")
                if response.text:
                    self.log(f"   Response: {response.text[:200]}", "ERROR")
                self.failed_tests.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                return False, None
            
            try:
                response_data = response.json()
                self.log(f"   ✅ Success - Response preview: {str(response_data)[:100]}...")
                self.tests_passed += 1
                return True, response_data
            except ValueError:
                self.log(f"   ✅ Success - Response (text): {response.text[:100]}...")
                self.tests_passed += 1
                return True, response.text
            
        except requests.exceptions.Timeout:
            self.log(f"   ❌ {name} - Timeout after {timeout} seconds", "ERROR")
            self.failed_tests.append(f"{name}: Timeout")
            return False, "timeout"
        except requests.exceptions.ConnectionError:
            self.log(f"   ❌ {name} - Connection error", "ERROR")
            self.failed_tests.append(f"{name}: Connection error")
            return False, "connection_error"
        except Exception as e:
            self.log(f"   ❌ {name} - Error: {e}", "ERROR")
            self.failed_tests.append(f"{name}: {str(e)}")
            return False, str(e)

    def test_healthz(self):
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "/healthz")

    def test_providers(self):
        """Test providers endpoint"""
        return self.run_test("Providers Status", "GET", "/providers")

    def test_chat_simple(self):
        """Test simple chat"""
        return self.run_test(
            "Simple Chat", 
            "POST", 
            "/chat",
            params={"q": "Hello, what is 2+2?"},
            timeout=15
        )

    def test_state(self):
        """Test state endpoint"""
        return self.run_test("State", "GET", "/state")

    def test_adapters_state(self):
        """Test adapters state"""
        return self.run_test("Adapters State", "GET", "/adapters/state")

    def run_quick_tests(self):
        """Run essential tests quickly"""
        self.log("🚀 Starting Quick LIQUID-HIVE Backend Tests")
        self.log("=" * 60)
        
        tests = [
            ("Health Check", self.test_healthz),
            ("Providers Status", self.test_providers),
            ("Simple Chat", self.test_chat_simple),
            ("State Endpoint", self.test_state),
            ("Adapters State", self.test_adapters_state),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
                self.log("")
            except Exception as e:
                self.log(f"   💥 EXCEPTION: {e}\n", "ERROR")
                self.failed_tests.append(f"{test_name}: Exception - {str(e)}")
        
        # Summary
        self.log("=" * 60)
        self.log("📊 QUICK TEST RESULTS")
        self.log("=" * 60)
        self.log(f"🎯 OVERALL: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for failure in self.failed_tests:
                self.log(f"   - {failure}")
        
        if self.tests_passed == self.tests_run:
            self.log("🎉 All quick tests passed!")
            return 0
        else:
            self.log("⚠️ Some tests failed. Check details above.")
            return 1

def main():
    tester = QuickTester()
    return tester.run_quick_tests()

if __name__ == "__main__":
    sys.exit(main())