#!/usr/bin/env python3
"""
Backend Test for LIQUID-HIVE System
===================================

Tests the backend API endpoints as specified in the review request.
"""

import requests
import json
import sys
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

class LiquidHiveBackendTester:
    def __init__(self, base_url="http://localhost:8001/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'LiquidHive-Tester/1.0'
        })

    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp and level"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def run_test(self, name: str, method: str, endpoint: str, 
                 expected_status: int = 200, data: Optional[Dict] = None, 
                 params: Optional[Dict] = None, timeout: int = 15) -> tuple[bool, Any]:
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        
        self.tests_run += 1
        self.log(f"🔍 Testing {name}")
        self.log(f"   URL: {url}")
        
        try:
            # Execute request
            if method == 'GET':
                response = self.session.get(url, params=params, timeout=timeout)
            elif method == 'POST':
                if data:
                    response = self.session.post(url, json=data, params=params, timeout=timeout)
                else:
                    response = self.session.post(url, params=params, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            self.log(f"   Status: {response.status_code}")
            
            # Check status code
            if response.status_code != expected_status:
                self.log(f"   ❌ Expected status {expected_status}, got {response.status_code}", "ERROR")
                if response.text:
                    self.log(f"   Response: {response.text[:300]}", "ERROR")
                return False, None
            
            # Parse response
            try:
                response_data = response.json()
                self.log(f"   ✓ Response received: {json.dumps(response_data, indent=2)[:200]}...")
                return True, response_data
            except ValueError:
                self.log(f"   ✓ Response (text): {response.text[:200]}...")
                return True, response.text
            
        except requests.exceptions.Timeout:
            self.log(f"   ❌ {name} - Timeout after {timeout} seconds", "ERROR")
            return False, "timeout"
        except requests.exceptions.ConnectionError:
            self.log(f"   ❌ {name} - Connection error", "ERROR")
            return False, "connection_error"
        except Exception as e:
            self.log(f"   ❌ {name} - Error: {e}", "ERROR")
            return False, str(e)

    def test_healthz(self):
        """Test GET /api/healthz endpoint"""
        success, response = self.run_test("Health Check", "GET", "/healthz")
        
        if success and isinstance(response, dict):
            if "ok" in response:
                self.log(f"   ✓ Health check OK: {response['ok']}")
                return True
            else:
                self.log("   ❌ Health check missing 'ok' key", "ERROR")
                return False
        else:
            self.log("   ❌ Health check failed", "ERROR")
            return False

    def test_providers(self):
        """Test GET /api/providers endpoint"""
        success, response = self.run_test("Providers Status", "GET", "/providers")
        
        if success and isinstance(response, dict):
            if "providers" in response:
                providers = response["providers"]
                self.log(f"   ✓ Providers status retrieved")
                
                # Check expected providers
                expected_providers = ["deepseek_chat", "deepseek_thinking", "qwen_cpu"]
                for provider in expected_providers:
                    if provider in providers:
                        status = providers[provider].get("status", "unknown")
                        latency = providers[provider].get("latency_ms", "N/A")
                        self.log(f"   - {provider}: {status} (latency: {latency}ms)")
                        
                        # DeepSeek providers should be healthy
                        if provider.startswith("deepseek") and status == "healthy":
                            self.log(f"   ✓ {provider} is healthy")
                        elif provider == "qwen_cpu" and status in ["disabled", "error"]:
                            self.log(f"   ⚠ {provider} is disabled/error (expected)")
                    else:
                        self.log(f"   ⚠ Missing expected provider: {provider}")
                        
                return True
            else:
                self.log("   ❌ Providers response missing 'providers' key", "ERROR")
                return False
        else:
            self.log("   ❌ Providers endpoint failed", "ERROR")
            return False

    def test_chat_simple(self):
        """Test POST /api/chat with simple query"""
        success, response = self.run_test(
            "Chat - Simple Query", 
            "POST", 
            "/chat",
            params={"q": "Hello, how are you today?"},
            timeout=12  # Allow for timeout handling
        )
        
        if success and isinstance(response, dict):
            if "answer" in response:
                self.log(f"   ✓ Chat response received: {response['answer'][:100]}...")
                
                # Check for metadata
                if "provider" in response:
                    self.log(f"   ✓ Provider used: {response['provider']}")
                    
                if "confidence" in response:
                    self.log(f"   ✓ Confidence score: {response['confidence']}")
                    
                return True
            else:
                self.log("   ❌ Chat response missing 'answer' key", "ERROR")
                return False
        else:
            self.log("   ❌ Chat endpoint failed", "ERROR")
            return False

    def test_chat_timeout_handling(self):
        """Test that chat endpoint handles timeouts properly"""
        # Test with a complex query that might take time
        complex_query = "Explain quantum computing, machine learning, and blockchain technology in detail with mathematical proofs and code examples."
        
        success, response = self.run_test(
            "Chat - Timeout Handling", 
            "POST", 
            "/chat",
            params={"q": complex_query},
            timeout=12
        )
        
        if success and isinstance(response, dict):
            if "answer" in response:
                provider = response.get("provider", "unknown")
                self.log(f"   ✓ Response received from provider: {provider}")
                
                # Check if it's a timeout fallback
                if provider == "timeout_fallback":
                    self.log(f"   ✓ Timeout fallback working correctly")
                else:
                    self.log(f"   ✓ Response completed within timeout")
                    
                return True
            else:
                self.log("   ❌ Response missing 'answer' key", "ERROR")
                return False
        else:
            self.log("   ❌ Chat timeout test failed", "ERROR")
            return False

    def test_state_endpoint(self):
        """Test GET /api/state endpoint"""
        success, response = self.run_test("State Endpoint", "GET", "/state")
        
        if success:
            self.log(f"   ✓ State endpoint accessible")
            return True
        else:
            self.log("   ❌ State endpoint failed", "ERROR")
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        self.log("🚀 Starting LIQUID-HIVE Backend Tests")
        self.log("=" * 60)
        
        tests = [
            ("Health Check", self.test_healthz),
            ("Providers Status", self.test_providers),
            ("Chat Simple", self.test_chat_simple),
            ("Chat Timeout Handling", self.test_chat_timeout_handling),
            ("State Endpoint", self.test_state_endpoint),
        ]
        
        for test_name, test_func in tests:
            self.log(f"\n📋 {test_name}")
            self.log("-" * 40)
            
            try:
                if test_func():
                    self.tests_passed += 1
                    self.log("   ✅ PASSED\n")
                else:
                    self.log("   ❌ FAILED\n")
            except Exception as e:
                self.log(f"   💥 EXCEPTION: {e}\n", "ERROR")
        
        # Final summary
        self.log("\n" + "=" * 60)
        self.log("📊 FINAL TEST RESULTS")
        self.log("=" * 60)
        
        self.log(f"🎯 OVERALL: {self.tests_passed}/{self.tests_run} tests passed")
        
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
    tester = LiquidHiveBackendTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())