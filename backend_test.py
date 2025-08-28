#!/usr/bin/env python3
"""
Backend API Test Suite for Cerebral GUI
========================================

This script tests all the backend endpoints mentioned in the review request:
- GET /healthz
- GET /state  
- POST /chat
- GET /config/governor
- WebSocket /ws
- Approvals endpoints
- Adapters endpoints
- POST /train
"""

import requests
import json
import sys
import time
import asyncio
import websockets
from datetime import datetime

class CerebralAPITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()

    def log(self, message):
        """Log with timestamp"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status=200, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, params=params)
            elif method == 'POST':
                if data:
                    response = self.session.post(url, json=data, headers=headers, params=params)
                else:
                    response = self.session.post(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            return False, {}

    def test_healthz(self):
        """Test health check endpoint"""
        success, response = self.run_test("Health Check", "GET", "/healthz")
        if success and isinstance(response, dict) and response.get("ok") is True:
            self.log("   ✓ Health check returned correct format")
            return True
        else:
            self.log("   ✗ Health check response format incorrect")
            return False

    def test_state(self):
        """Test state endpoint"""
        success, response = self.run_test("State Endpoint", "GET", "/state")
        if success and isinstance(response, dict):
            self.log("   ✓ State endpoint returned JSON object")
            # Check for expected fields
            if "memory_size" in response or "self_awareness_metrics" in response:
                self.log("   ✓ State contains expected fields")
            return True
        else:
            self.log("   ✗ State endpoint response format incorrect")
            return False

    def test_chat(self):
        """Test chat endpoint"""
        success, response = self.run_test("Chat Endpoint", "POST", "/chat", params={"q": "hello"})
        if success and isinstance(response, dict):
            if "answer" in response:
                self.log("   ✓ Chat response contains 'answer' field")
                if "reasoning_strategy" in response:
                    self.log("   ✓ Chat response contains 'reasoning_strategy' field")
                return True
            else:
                self.log("   ✗ Chat response missing 'answer' field")
                return False
        else:
            self.log("   ✗ Chat endpoint response format incorrect")
            return False

    def test_governor_get(self):
        """Test governor configuration GET endpoint"""
        success, response = self.run_test("Governor GET", "GET", "/config/governor")
        if success and isinstance(response, dict):
            expected_fields = ["ENABLE_ORACLE_REFINEMENT", "FORCE_GPT4O_ARBITER"]
            has_fields = all(field in response for field in expected_fields)
            if has_fields:
                self.log("   ✓ Governor config contains both boolean fields")
                return True, response
            else:
                self.log("   ✗ Governor config missing expected fields")
                return False, response
        else:
            self.log("   ✗ Governor GET response format incorrect")
            return False, {}

    def test_governor_post(self, current_config):
        """Test governor configuration POST endpoint"""
        # Toggle the current values
        new_config = {
            "ENABLE_ORACLE_REFINEMENT": not current_config.get("ENABLE_ORACLE_REFINEMENT", False),
            "FORCE_GPT4O_ARBITER": not current_config.get("FORCE_GPT4O_ARBITER", False)
        }
        
        success, response = self.run_test("Governor POST", "POST", "/config/governor", data=new_config)
        if success:
            # Verify the change took effect
            verify_success, verify_response = self.run_test("Governor POST Verify", "GET", "/config/governor")
            if verify_success:
                if (verify_response.get("ENABLE_ORACLE_REFINEMENT") == new_config["ENABLE_ORACLE_REFINEMENT"] and
                    verify_response.get("FORCE_GPT4O_ARBITER") == new_config["FORCE_GPT4O_ARBITER"]):
                    self.log("   ✓ Governor configuration updated successfully")
                    return True
                else:
                    self.log("   ✗ Governor configuration not updated properly")
                    return False
            else:
                return False
        else:
            return False

    def test_approvals(self):
        """Test approvals endpoints"""
        success, response = self.run_test("Approvals List", "GET", "/approvals")
        if success and isinstance(response, list):
            self.log("   ✓ Approvals endpoint returns list")
            return True
        else:
            self.log("   ✗ Approvals endpoint response format incorrect")
            return False

    def test_adapters(self):
        """Test adapters endpoints"""
        success, response = self.run_test("Adapters List", "GET", "/adapters")
        if success and isinstance(response, list):
            self.log("   ✓ Adapters endpoint returns list")
            
            # Test adapters state endpoint
            state_success, state_response = self.run_test("Adapters State", "GET", "/adapters/state")
            if state_success and isinstance(state_response, dict):
                self.log("   ✓ Adapters state endpoint returns dict")
                return True
            else:
                self.log("   ✗ Adapters state endpoint response format incorrect")
                return False
        else:
            self.log("   ✗ Adapters endpoint response format incorrect")
            return False

    def test_train(self):
        """Test training endpoint"""
        success, response = self.run_test("Training Endpoint", "POST", "/train")
        if success and isinstance(response, dict):
            if "status" in response:
                self.log("   ✓ Training response contains 'status' field")
                if response["status"] == "success":
                    self.log("   ✓ Training completed successfully")
                elif response["status"] == "error":
                    self.log("   ⚠ Training returned error (expected in test environment)")
                return True
            else:
                self.log("   ✗ Training response missing 'status' field")
                return False
        else:
            self.log("   ✗ Training endpoint response format incorrect")
            return False

    async def test_websocket(self):
        """Test WebSocket connectivity"""
        self.log("🔍 Testing WebSocket connectivity...")
        self.tests_run += 1
        
        try:
            ws_url = self.base_url.replace("http://", "ws://") + "/ws"
            
            async with websockets.connect(ws_url) as websocket:
                self.log("   ✓ WebSocket connection established")
                
                # Wait for messages for up to 12 seconds
                start_time = time.time()
                received_state_update = False
                
                while time.time() - start_time < 12:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)
                        
                        if data.get("type") == "state_update":
                            received_state_update = True
                            self.log("   ✓ Received state_update message")
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        self.log(f"   ⚠ WebSocket message error: {e}")
                        continue
                
                if received_state_update:
                    self.tests_passed += 1
                    self.log("✅ WebSocket test - Received state_update within 12 seconds")
                    return True
                else:
                    self.log("❌ WebSocket test - No state_update received within 12 seconds")
                    return False
                    
        except Exception as e:
            self.log(f"❌ WebSocket test - Connection error: {e}")
            return False

    def run_all_tests(self):
        """Run all backend API tests"""
        self.log("🚀 Starting Cerebral Backend API Tests")
        self.log("=" * 50)
        
        # Test 1: Health check
        self.test_healthz()
        
        # Test 2: State endpoint
        self.test_state()
        
        # Test 3: Chat endpoint
        self.test_chat()
        
        # Test 4: Governor endpoints
        gov_success, current_config = self.test_governor_get()
        if gov_success:
            self.test_governor_post(current_config)
        
        # Test 5: Approvals endpoints
        self.test_approvals()
        
        # Test 6: Adapters endpoints
        self.test_adapters()
        
        # Test 7: Training endpoint
        self.test_train()
        
        # Test 8: WebSocket (async)
        try:
            asyncio.run(self.test_websocket())
        except Exception as e:
            self.log(f"❌ WebSocket test failed to run: {e}")
        
        # Print summary
        self.log("=" * 50)
        self.log(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            self.log("🎉 All tests passed!")
            return 0
        else:
            self.log("⚠️  Some tests failed")
            return 1

def main():
    """Main test runner"""
    tester = CerebralAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())