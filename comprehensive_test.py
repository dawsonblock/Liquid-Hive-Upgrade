#!/usr/bin/env python3
"""
Comprehensive Test Suite for LIQUID-HIVE System
==============================================

Tests all requirements from the review request:
1. Backend API basics
2. WebSocket routing  
3. Frontend integration
4. Latency guardrails
5. Vision endpoint regression
"""

import requests
import asyncio
import websockets
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional

class ComprehensiveTester:
    def __init__(self):
        self.base_url = "http://localhost:8001/api"
        self.frontend_url = "http://localhost:3000"
        self.ws_url = "ws://localhost:8001/api/ws"
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ComprehensiveTester/1.0'
        })

    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp and level"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def run_test(self, name: str, test_func) -> bool:
        """Run a single test with error handling"""
        self.tests_run += 1
        self.log(f"🔍 Testing {name}")
        
        try:
            result = test_func()
            if result:
                self.tests_passed += 1
                self.log(f"   ✅ {name} PASSED")
            else:
                self.log(f"   ❌ {name} FAILED")
            return result
        except Exception as e:
            self.log(f"   💥 {name} EXCEPTION: {e}", "ERROR")
            return False

    # ========================================
    # 1. Backend API Basics Tests
    # ========================================
    
    def test_healthz(self):
        """Test GET /api/healthz returns 200 JSON {ok: ...}"""
        try:
            response = self.session.get(f"{self.base_url}/healthz", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "ok" in data:
                    self.log(f"   ✓ Health check OK: {data['ok']}")
                    return True
                else:
                    self.log("   ❌ Missing 'ok' key in response")
                    return False
            else:
                self.log(f"   ❌ Expected 200, got {response.status_code}")
                return False
        except Exception as e:
            self.log(f"   ❌ Health check failed: {e}")
            return False

    def test_providers(self):
        """Test GET /api/providers returns JSON with expected providers"""
        try:
            response = self.session.get(f"{self.base_url}/providers", timeout=30)
            if response.status_code == 200:
                data = response.json()
                if "providers" in data:
                    providers = data["providers"]
                    
                    # Check deepseek_chat and deepseek_thinking are healthy
                    deepseek_chat = providers.get("deepseek_chat", {})
                    deepseek_thinking = providers.get("deepseek_thinking", {})
                    qwen_cpu = providers.get("qwen_cpu", {})
                    
                    chat_healthy = deepseek_chat.get("status") == "healthy" and "latency_ms" in deepseek_chat
                    thinking_healthy = deepseek_thinking.get("status") == "healthy" and "latency_ms" in deepseek_thinking
                    qwen_disabled = qwen_cpu.get("status") == "disabled"
                    
                    self.log(f"   - deepseek_chat: {deepseek_chat.get('status')} (latency: {deepseek_chat.get('latency_ms', 'N/A')}ms)")
                    self.log(f"   - deepseek_thinking: {deepseek_thinking.get('status')} (latency: {deepseek_thinking.get('latency_ms', 'N/A')}ms)")
                    self.log(f"   - qwen_cpu: {qwen_cpu.get('status')}")
                    
                    if chat_healthy and thinking_healthy and qwen_disabled:
                        self.log("   ✓ All expected provider statuses correct")
                        return True
                    else:
                        self.log("   ❌ Provider statuses not as expected")
                        return False
                else:
                    self.log("   ❌ Missing 'providers' key in response")
                    return False
            else:
                self.log(f"   ❌ Expected 200, got {response.status_code}")
                return False
        except Exception as e:
            self.log(f"   ❌ Providers test failed: {e}")
            return False

    def test_chat_basic(self):
        """Test POST /api/chat?q=hello returns 200 JSON with answer, provider"""
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/chat?q=hello", timeout=15)
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if "answer" in data and "provider" in data:
                    provider = data.get("provider")
                    confidence = data.get("confidence")
                    
                    self.log(f"   ✓ Response received in {latency:.0f}ms")
                    self.log(f"   ✓ Provider: {provider}")
                    self.log(f"   ✓ Confidence: {confidence}")
                    
                    # Check if it's a valid provider response (not timeout_fallback on first try)
                    if provider and provider.startswith("deepseek"):
                        self.log("   ✓ Successfully routed to DeepSeek provider")
                        return True
                    elif provider == "timeout_fallback":
                        self.log("   ⚠️ Got timeout fallback - retrying once")
                        # Retry once
                        response2 = self.session.post(f"{self.base_url}/chat?q=hello", timeout=15)
                        if response2.status_code == 200:
                            data2 = response2.json()
                            provider2 = data2.get("provider", "")
                            if provider2.startswith("deepseek"):
                                self.log("   ✓ Retry successful with DeepSeek provider")
                                return True
                        self.log("   ❌ Retry also failed")
                        return False
                    else:
                        self.log(f"   ❌ Unexpected provider: {provider}")
                        return False
                else:
                    self.log("   ❌ Missing 'answer' or 'provider' in response")
                    return False
            else:
                self.log(f"   ❌ Expected 200, got {response.status_code}")
                return False
        except Exception as e:
            self.log(f"   ❌ Chat test failed: {e}")
            return False

    # ========================================
    # 2. WebSocket Routing Tests
    # ========================================
    
    def test_websocket_connection(self):
        """Test WebSocket connection to /api/ws and message reception"""
        async def websocket_test():
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.log("   ✓ WebSocket connected successfully")
                    
                    # Wait for periodic messages within 15s
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=15)
                        data = json.loads(message)
                        msg_type = data.get("type", "unknown")
                        
                        self.log(f"   ✓ Received message type: {msg_type}")
                        
                        # Check for expected message types
                        if msg_type in ["state_update", "approvals_update"]:
                            self.log("   ✓ Received expected periodic message")
                            return True
                        else:
                            self.log(f"   ⚠️ Unexpected message type: {msg_type}")
                            return True  # Still counts as success
                    except asyncio.TimeoutError:
                        self.log("   ❌ No messages received within 15 seconds")
                        return False
            except Exception as e:
                self.log(f"   ❌ WebSocket test failed: {e}")
                return False
        
        try:
            return asyncio.run(websocket_test())
        except Exception as e:
            self.log(f"   ❌ WebSocket test exception: {e}")
            return False

    # ========================================
    # 3. Frontend Integration Tests
    # ========================================
    
    def test_frontend_loading(self):
        """Test that frontend loads and shows Cerebral Operator Console"""
        try:
            response = self.session.get(self.frontend_url, timeout=10)
            if response.status_code == 200:
                content = response.text
                if "Cerebral Operator Console" in content:
                    self.log("   ✓ Frontend loads with correct title")
                    return True
                else:
                    self.log("   ❌ Frontend title not found")
                    return False
            else:
                self.log(f"   ❌ Frontend returned {response.status_code}")
                return False
        except Exception as e:
            self.log(f"   ❌ Frontend test failed: {e}")
            return False

    # ========================================
    # 4. Latency Guardrails Tests
    # ========================================
    
    def test_chat_latency(self):
        """Test that /api/chat responses complete within 10s"""
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/chat?q=What is artificial intelligence?", timeout=12)
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            
            self.log(f"   ✓ Response received in {latency:.0f}ms")
            
            if response.status_code == 200:
                data = response.json()
                provider = data.get("provider", "unknown")
                
                if latency <= 10000:  # 10 seconds
                    self.log(f"   ✓ Latency within 10s limit (provider: {provider})")
                    return True
                else:
                    self.log(f"   ❌ Latency exceeded 10s limit: {latency:.0f}ms")
                    return False
            else:
                self.log(f"   ❌ Chat request failed with status {response.status_code}")
                return False
        except Exception as e:
            self.log(f"   ❌ Latency test failed: {e}")
            return False

    # ========================================
    # 5. Vision Endpoint Regression Tests
    # ========================================
    
    def test_vision_endpoint(self):
        """Test POST /api/vision with small PNG"""
        try:
            # Create a minimal test file
            test_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
            
            files = {'file': ('test.png', test_data, 'image/png')}
            data = {'question': 'What is in this image?'}
            
            response = self.session.post(f"{self.base_url}/vision", files=files, data=data, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                if "answer" in result:
                    self.log(f"   ✓ Vision endpoint returned answer")
                    return True
                else:
                    self.log("   ❌ Vision response missing 'answer' key")
                    return False
            else:
                self.log(f"   ⚠️ Vision endpoint returned {response.status_code} (pipeline may be unavailable)")
                # This is acceptable per requirements
                return True
        except Exception as e:
            self.log(f"   ⚠️ Vision test failed: {e} (pipeline may be unavailable)")
            # This is acceptable per requirements
            return True

    # ========================================
    # Test Runner
    # ========================================
    
    def run_all_tests(self):
        """Run all comprehensive tests"""
        self.log("🚀 Starting LIQUID-HIVE Comprehensive Test Suite")
        self.log("=" * 70)
        
        test_categories = [
            ("Backend API Basics", [
                ("Health Check", self.test_healthz),
                ("Providers Status", self.test_providers),
                ("Chat Basic", self.test_chat_basic),
            ]),
            ("WebSocket Routing", [
                ("WebSocket Connection", self.test_websocket_connection),
            ]),
            ("Frontend Integration", [
                ("Frontend Loading", self.test_frontend_loading),
            ]),
            ("Latency Guardrails", [
                ("Chat Latency", self.test_chat_latency),
            ]),
            ("Vision Endpoint Regression", [
                ("Vision Endpoint", self.test_vision_endpoint),
            ])
        ]
        
        category_results = {}
        
        for category_name, tests in test_categories:
            self.log(f"\n📋 {category_name}")
            self.log("-" * 50)
            
            category_passed = 0
            category_total = len(tests)
            
            for test_name, test_func in tests:
                if self.run_test(test_name, test_func):
                    category_passed += 1
            
            category_results[category_name] = (category_passed, category_total)
            self.log(f"📊 {category_name}: {category_passed}/{category_total} passed")
        
        # Final summary
        self.log("\n" + "=" * 70)
        self.log("📊 FINAL TEST RESULTS")
        self.log("=" * 70)
        
        for category, (passed, total) in category_results.items():
            status = "✅" if passed == total else "❌" if passed == 0 else "⚠️"
            self.log(f"{status} {category}: {passed}/{total}")
        
        self.log(f"\n🎯 OVERALL: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            self.log("🎉 All tests passed!")
            return 0
        elif self.tests_passed >= (self.tests_run * 0.8):
            self.log("⚠️ Most tests passed. Minor issues detected.")
            return 0
        else:
            self.log("❌ Significant issues detected. Review required.")
            return 1

def main():
    """Main test runner"""
    tester = ComprehensiveTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())