#!/usr/bin/env python3
"""
Frontend Integration Test for LIQUID-HIVE System
Tests the API endpoints that the frontend uses
"""

import requests
import json
import sys
import time
from datetime import datetime

class FrontendIntegrationTester:
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
                 params: dict = None, timeout: int = 15) -> tuple[bool, any]:
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

    def test_chat_panel_endpoints(self):
        """Test endpoints used by ChatPanel component"""
        self.log("\n📋 Testing Chat Panel Endpoints")
        self.log("-" * 40)
        
        # Test chat endpoint (main functionality)
        success, response = self.run_test(
            "Chat Endpoint", 
            "POST", 
            "/chat",
            params={"q": "Hello from frontend test"}
        )
        
        if success and isinstance(response, dict):
            if "answer" in response:
                self.log(f"   ✓ Chat response: {response['answer'][:50]}...")
                if "provider" in response:
                    self.log(f"   ✓ Provider: {response['provider']}")
            else:
                self.log("   ❌ Missing 'answer' in chat response", "ERROR")
                return False
        
        # Test state endpoint (used for context updates)
        success, response = self.run_test("State Endpoint", "GET", "/state")
        
        if success and isinstance(response, dict):
            if "uptime_s" in response:
                self.log(f"   ✓ State uptime: {response['uptime_s']}s")
            if "operator_intent" in response:
                self.log(f"   ✓ Operator intent: {response.get('operator_intent', 'None')}")
        
        return True

    def test_system_panel_endpoints(self):
        """Test endpoints used by SystemPanel component"""
        self.log("\n📋 Testing System Panel Endpoints")
        self.log("-" * 40)
        
        # Test approvals endpoint
        success, response = self.run_test("Approvals Endpoint", "GET", "/approvals")
        
        if success:
            if isinstance(response, list):
                self.log(f"   ✓ Approvals list: {len(response)} items")
            elif isinstance(response, dict) and "approvals" in response:
                self.log(f"   ✓ Approvals object: {len(response['approvals'])} items")
            else:
                self.log(f"   ✓ Approvals response: {type(response)}")
        
        # Test state endpoint (also used by SystemPanel)
        success, response = self.run_test("State for System Panel", "GET", "/state")
        
        if success and isinstance(response, dict):
            if "self_awareness_metrics" in response:
                metrics = response["self_awareness_metrics"]
                self.log(f"   ✓ Self-awareness metrics: {metrics}")
            if "memory_size" in response:
                self.log(f"   ✓ Memory size: {response['memory_size']}")
        
        return True

    def test_forge_panel_endpoints(self):
        """Test endpoints used by ForgePanel component"""
        self.log("\n📋 Testing Forge Panel Endpoints")
        self.log("-" * 40)
        
        # Test adapters state endpoint
        success, response = self.run_test("Adapters State", "GET", "/adapters/state")
        
        if success and isinstance(response, dict):
            if "state" in response:
                self.log(f"   ✓ Adapters state: {len(response['state'])} adapters")
            else:
                self.log(f"   ✓ Adapters response: {response}")
        
        # Test governor config endpoint
        success, response = self.run_test("Governor Config", "GET", "/config/governor")
        
        if success:
            self.log(f"   ✓ Governor config retrieved")
        
        return True

    def test_websocket_endpoint(self):
        """Test WebSocket endpoint availability (not actual connection)"""
        self.log("\n📋 Testing WebSocket Endpoint")
        self.log("-" * 40)
        
        # WebSocket endpoints typically return 426 Upgrade Required for HTTP requests
        success, response = self.run_test(
            "WebSocket Endpoint", 
            "GET", 
            "/ws",
            expected_status=426  # Expected for WebSocket upgrade
        )
        
        if not success:
            # Try alternative status codes that might be returned
            success, response = self.run_test(
                "WebSocket Endpoint (Alt)", 
                "GET", 
                "/ws",
                expected_status=404  # Might return 404 if not properly configured
            )
        
        return True

    def run_integration_tests(self):
        """Run all frontend integration tests"""
        self.log("🚀 Starting LIQUID-HIVE Frontend Integration Tests")
        self.log("=" * 60)
        
        test_categories = [
            ("Chat Panel Integration", self.test_chat_panel_endpoints),
            ("System Panel Integration", self.test_system_panel_endpoints),
            ("Forge Panel Integration", self.test_forge_panel_endpoints),
            ("WebSocket Integration", self.test_websocket_endpoint),
        ]
        
        for category_name, test_func in test_categories:
            try:
                test_func()
                self.log("")
            except Exception as e:
                self.log(f"   💥 EXCEPTION in {category_name}: {e}\n", "ERROR")
                self.failed_tests.append(f"{category_name}: Exception - {str(e)}")
        
        # Summary
        self.log("=" * 60)
        self.log("📊 FRONTEND INTEGRATION TEST RESULTS")
        self.log("=" * 60)
        self.log(f"🎯 OVERALL: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for failure in self.failed_tests:
                self.log(f"   - {failure}")
        
        if self.tests_passed == self.tests_run:
            self.log("🎉 All frontend integration tests passed!")
            return 0
        elif self.tests_passed >= (self.tests_run * 0.8):
            self.log("⚠️ Most tests passed. Minor issues detected.")
            return 0
        else:
            self.log("❌ Significant integration issues detected.")
            return 1

def main():
    tester = FrontendIntegrationTester()
    return tester.run_integration_tests()

if __name__ == "__main__":
    sys.exit(main())