#!/usr/bin/env python3
"""
Comprehensive Backend Test for LIQUID-HIVE
==========================================
Tests all API endpoints and functionality as specified in the review request.
"""

import requests
import asyncio
import websockets
import json
import time
import sys
from typing import Dict, Any, Optional

class LiquidHiveAPITester:
    def __init__(self, base_url: str = "/api"):
        # Use the frontend environment variable for consistency
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.tests_run = 0
        self.tests_passed = 0
        self.failures = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            self.failures.append(f"{name}: {details}")
            print(f"❌ {name}: FAILED {details}")

    def test_providers_endpoint(self) -> bool:
        """Test 1: Backend providers endpoint"""
        print("\n🔍 Testing Backend Providers...")
        try:
            response = self.session.get(f"{self.base_url}/providers", timeout=10)
            
            if response.status_code != 200:
                self.log_test("Providers Status Code", False, f"Expected 200, got {response.status_code}")
                return False
            
            data = response.json()
            print(f"Providers response: {json.dumps(data, indent=2)}")
            
            if "error" in data:
                self.log_test("Providers Error Check", False, f"API returned error: {data['error']}")
                return False
            
            providers = data.get("providers", {})
            
            # Check deepseek_chat
            deepseek_chat = providers.get("deepseek_chat", {})
            if deepseek_chat.get("status") == "healthy" and deepseek_chat.get("latency_ms", 0) > 0:
                self.log_test("DeepSeek Chat Provider", True, f"Healthy with {deepseek_chat.get('latency_ms')}ms latency")
            else:
                self.log_test("DeepSeek Chat Provider", False, f"Status: {deepseek_chat.get('status')}, Latency: {deepseek_chat.get('latency_ms')}")
            
            # Check deepseek_thinking
            deepseek_thinking = providers.get("deepseek_thinking", {})
            if deepseek_thinking.get("status") == "healthy" and deepseek_thinking.get("latency_ms", 0) > 0:
                self.log_test("DeepSeek Thinking Provider", True, f"Healthy with {deepseek_thinking.get('latency_ms')}ms latency")
            else:
                self.log_test("DeepSeek Thinking Provider", False, f"Status: {deepseek_thinking.get('status')}, Latency: {deepseek_thinking.get('latency_ms')}")
            
            # Check qwen_cpu (should be disabled)
            qwen_cpu = providers.get("qwen_cpu", {})
            if qwen_cpu.get("status") == "disabled":
                self.log_test("Qwen CPU Provider", True, "Correctly disabled")
            else:
                self.log_test("Qwen CPU Provider", False, f"Expected disabled, got: {qwen_cpu.get('status')}")
            
            # Check deepseek_r1 (may be error, which is ok)
            deepseek_r1 = providers.get("deepseek_r1", {})
            if deepseek_r1.get("status") in ["error", "disabled", "healthy"]:
                self.log_test("DeepSeek R1 Provider", True, f"Status: {deepseek_r1.get('status')} (acceptable)")
            else:
                self.log_test("DeepSeek R1 Provider", False, f"Unexpected status: {deepseek_r1.get('status')}")
            
            return True
            
        except Exception as e:
            self.log_test("Providers Endpoint", False, f"Exception: {str(e)}")
            return False

    def test_chat_hello(self) -> bool:
        """Test 2: Chat flow with hello"""
        print("\n🔍 Testing Chat Flow - Hello...")
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/chat?q=hello", timeout=15)
            end_time = time.time()
            
            duration = end_time - start_time
            
            if response.status_code != 200:
                self.log_test("Chat Hello Status", False, f"Expected 200, got {response.status_code}")
                return False
            
            data = response.json()
            print(f"Chat hello response: {json.dumps(data, indent=2)}")
            
            # Check answer is non-empty
            answer = data.get("answer", "")
            if not answer or answer.strip() == "":
                self.log_test("Chat Hello Answer", False, "Answer is empty")
                return False
            
            self.log_test("Chat Hello Answer", True, f"Non-empty answer received: '{answer[:50]}...'")
            
            # Check provider is not timeout_fallback
            provider = data.get("provider", "")
            if provider == "timeout_fallback":
                self.log_test("Chat Hello Provider", False, f"Got timeout_fallback provider")
                return False
            elif provider.startswith("deepseek"):
                self.log_test("Chat Hello Provider", True, f"Used provider: {provider}")
            else:
                self.log_test("Chat Hello Provider", False, f"Unexpected provider: {provider}")
            
            # Check latency < 12s
            if duration < 12.0:
                self.log_test("Chat Hello Latency", True, f"Response time: {duration:.2f}s")
            else:
                self.log_test("Chat Hello Latency", False, f"Response time: {duration:.2f}s (> 12s)")
            
            return True
            
        except Exception as e:
            self.log_test("Chat Hello", False, f"Exception: {str(e)}")
            return False

    def test_chat_liquid_hive(self) -> bool:
        """Test 3: Chat flow with LIQUID-HIVE question"""
        print("\n🔍 Testing Chat Flow - LIQUID-HIVE...")
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/chat?q=Explain%20the%20purpose%20of%20LIQUID-HIVE", timeout=15)
            end_time = time.time()
            
            duration = end_time - start_time
            
            if response.status_code != 200:
                self.log_test("Chat LIQUID-HIVE Status", False, f"Expected 200, got {response.status_code}")
                return False
            
            data = response.json()
            print(f"Chat LIQUID-HIVE response: {json.dumps(data, indent=2)}")
            
            # Check answer is non-empty
            answer = data.get("answer", "")
            if not answer or answer.strip() == "":
                self.log_test("Chat LIQUID-HIVE Answer", False, "Answer is empty")
                return False
            
            self.log_test("Chat LIQUID-HIVE Answer", True, f"Non-empty answer received: '{answer[:100]}...'")
            
            # Check provider is deepseek_*
            provider = data.get("provider", "")
            if provider.startswith("deepseek"):
                self.log_test("Chat LIQUID-HIVE Provider", True, f"Used provider: {provider}")
            else:
                self.log_test("Chat LIQUID-HIVE Provider", False, f"Expected deepseek_*, got: {provider}")
            
            # Check latency
            if duration < 12.0:
                self.log_test("Chat LIQUID-HIVE Latency", True, f"Response time: {duration:.2f}s")
            else:
                self.log_test("Chat LIQUID-HIVE Latency", False, f"Response time: {duration:.2f}s (> 12s)")
            
            return True
            
        except Exception as e:
            self.log_test("Chat LIQUID-HIVE", False, f"Exception: {str(e)}")
            return False

    async def test_websocket(self) -> bool:
        """Test 4: WebSocket connection and messages"""
        print("\n🔍 Testing WebSocket Connection...")
        try:
            # Determine WebSocket URL - need to convert /api to ws://
            # Since we're testing from backend, we need to use the actual URL
            ws_url = "ws://localhost:8001/api/ws"
            
            async with websockets.connect(ws_url, timeout=10) as websocket:
                print(f"Connected to WebSocket: {ws_url}")
                
                # Wait for messages within 15 seconds
                heartbeat_received = False
                state_received = False
                start_time = time.time()
                
                while time.time() - start_time < 15:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)
                        print(f"WebSocket message: {data}")
                        
                        if data.get("type") == "heartbeat":
                            heartbeat_received = True
                            self.log_test("WebSocket Heartbeat", True, "Heartbeat message received")
                        
                        elif data.get("type") == "state_update":
                            state_received = True
                            payload = data.get("payload", {})
                            engine_ready = payload.get("engine_ready", False)
                            self.log_test("WebSocket State Update", True, f"State update received, engine_ready: {engine_ready}")
                        
                        if heartbeat_received and state_received:
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                if not heartbeat_received:
                    self.log_test("WebSocket Heartbeat", False, "No heartbeat received within 15s")
                
                if not state_received:
                    self.log_test("WebSocket State Update", False, "No state update received within 15s")
                
                return heartbeat_received and state_received
                
        except Exception as e:
            self.log_test("WebSocket Connection", False, f"Exception: {str(e)}")
            return False

    def test_health_endpoint(self) -> bool:
        """Test health endpoint"""
        print("\n🔍 Testing Health Endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/healthz", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    self.log_test("Health Endpoint", True, "Health check passed")
                    return True
                else:
                    self.log_test("Health Endpoint", False, f"Health check failed: {data}")
                    return False
            else:
                self.log_test("Health Endpoint", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Health Endpoint", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self) -> bool:
        """Run all backend tests"""
        print("🚀 Starting LIQUID-HIVE Backend Tests...")
        
        # Test health first
        self.test_health_endpoint()
        
        # Test providers
        self.test_providers_endpoint()
        
        # Test chat flows
        self.test_chat_hello()
        self.test_chat_liquid_hive()
        
        # Test WebSocket
        try:
            asyncio.run(self.test_websocket())
        except Exception as e:
            self.log_test("WebSocket Test", False, f"Failed to run WebSocket test: {str(e)}")
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failures:
            print(f"\n❌ Failures:")
            for failure in self.failures:
                print(f"  - {failure}")
        
        return len(self.failures) == 0

def main():
    """Main test runner"""
    tester = LiquidHiveAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())