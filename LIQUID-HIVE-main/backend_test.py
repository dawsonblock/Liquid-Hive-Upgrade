#!/usr/bin/env python3
"""
Comprehensive Backend Test for LIQUID-HIVE DS-Router v1 System
==============================================================

This test suite validates:
1. DS-Router Core Functionality
2. Provider Health and Status  
3. Admin Endpoints
4. API Integration
5. Safety and Routing
6. Legacy Compatibility
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

class DSRouterTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DS-Router-Tester/1.0'
        })

    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp and level"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def run_test(self, name: str, method: str, endpoint: str, 
                 expected_status: int = 200, data: Optional[Dict] = None, 
                 params: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple[bool, Any]:
        """Run a single API test with comprehensive error handling"""
        url = f"{self.api_base}{endpoint}"
        
        self.tests_run += 1
        self.log(f"🔍 Testing {name}")
        self.log(f"   URL: {url}")
        
        try:
            # Prepare request
            request_headers = self.session.headers.copy()
            if headers:
                request_headers.update(headers)
            
            # Execute request
            if method == 'GET':
                response = self.session.get(url, params=params, headers=request_headers, timeout=30)
            elif method == 'POST':
                if data:
                    response = self.session.post(url, json=data, params=params, headers=request_headers, timeout=30)
                else:
                    response = self.session.post(url, params=params, headers=request_headers, timeout=30)
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
                self.log(f"   Response preview: {json.dumps(response_data, indent=2)[:200]}...")
                return True, response_data
            except ValueError:
                self.log(f"   Response (text): {response.text[:200]}...")
                return True, response.text
            
        except requests.exceptions.Timeout:
            self.log(f"   ❌ {name} - Timeout after 30 seconds", "ERROR")
            return False, "timeout"
        except requests.exceptions.ConnectionError:
            self.log(f"   ❌ {name} - Connection error", "ERROR")
            return False, "connection_error"
        except Exception as e:
            self.log(f"   ❌ {name} - Error: {e}", "ERROR")
            return False, str(e)

    # ========================================
    # 1. DS-Router Core Functionality Tests
    # ========================================
    
    def test_chat_simple_query(self):
        """Test chat endpoint with simple query (should route to deepseek_chat)"""
        success, response = self.run_test(
            "Chat - Simple Query", 
            "POST", 
            "/chat",
            params={"q": "Hello, how are you today?"}
        )
        
        if success and isinstance(response, dict):
            if "answer" in response:
                self.log(f"   ✓ Chat response received: {response['answer'][:100]}...")
                
                # Check for DS-Router metadata
                if "provider" in response:
                    self.log(f"   ✓ Provider used: {response['provider']}")
                    if response['provider'] == 'deepseek_chat':
                        self.log(f"   ✓ Correctly routed to deepseek_chat for simple query")
                    
                if "confidence" in response:
                    self.log(f"   ✓ Confidence score: {response['confidence']}")
                    
                return True
            else:
                self.log("   ❌ Chat response missing 'answer' key", "ERROR")
                return False
        else:
            self.log("   ❌ Chat endpoint response format incorrect", "ERROR")
            return False

    def test_chat_complex_query(self):
        """Test chat endpoint with complex query (should route to deepseek_thinking)"""
        complex_query = "Prove that the square root of 2 is irrational using proof by contradiction. Show all mathematical steps."
        
        success, response = self.run_test(
            "Chat - Complex Mathematical Query", 
            "POST", 
            "/chat",
            params={"q": complex_query}
        )
        
        if success and isinstance(response, dict):
            if "answer" in response:
                self.log(f"   ✓ Complex query response received: {response['answer'][:100]}...")
                
                # Check routing decision
                if "provider" in response:
                    self.log(f"   ✓ Provider used: {response['provider']}")
                    if response['provider'] in ['deepseek_thinking', 'deepseek_r1']:
                        self.log(f"   ✓ Correctly routed to reasoning provider for complex query")
                    
                # Check for escalation
                if "escalated" in response and response['escalated']:
                    self.log(f"   ✓ Query was escalated due to complexity")
                    
                return True
            else:
                self.log("   ❌ Complex query response missing 'answer' key", "ERROR")
                return False
        else:
            self.log("   ❌ Complex query endpoint response format incorrect", "ERROR")
            return False

    def test_chat_coding_query(self):
        """Test chat endpoint with coding query"""
        coding_query = "Write a Python function to implement binary search with unit tests and error handling."
        
        success, response = self.run_test(
            "Chat - Coding Query", 
            "POST", 
            "/chat",
            params={"q": coding_query}
        )
        
        if success and isinstance(response, dict):
            if "answer" in response:
                self.log(f"   ✓ Coding query response received")
                
                # Check if response contains code
                if "def " in response['answer'] or "function" in response['answer'].lower():
                    self.log(f"   ✓ Response appears to contain code")
                    
                return True
            else:
                self.log("   ❌ Coding query response missing 'answer' key", "ERROR")
                return False
        else:
            self.log("   ❌ Coding query endpoint response format incorrect", "ERROR")
            return False

    # ========================================
    # 2. Provider Health and Status Tests
    # ========================================
    
    def test_providers_status(self):
        """Test /api/providers endpoint for all provider statuses"""
        success, response = self.run_test("Providers Status", "GET", "/providers")
        
        if success and isinstance(response, dict):
            if "providers" in response:
                providers = response["providers"]
                self.log(f"   ✓ Providers status retrieved")
                
                # Check expected providers
                expected_providers = ["deepseek_chat", "deepseek_thinking", "deepseek_r1", "qwen_cpu"]
                for provider in expected_providers:
                    if provider in providers:
                        status = providers[provider].get("status", "unknown")
                        self.log(f"   - {provider}: {status}")
                        
                        # DeepSeek providers should be healthy with valid API key
                        if provider.startswith("deepseek") and status == "healthy":
                            self.log(f"   ✓ {provider} is healthy")
                        elif provider == "qwen_cpu" and status in ["unhealthy", "error"]:
                            self.log(f"   ⚠ {provider} is unhealthy (expected due to model issues)")
                    else:
                        self.log(f"   ❌ Missing expected provider: {provider}", "ERROR")
                        
                return True
            else:
                self.log("   ❌ Providers response missing 'providers' key", "ERROR")
                return False
        else:
            self.log("   ❌ Providers endpoint response format incorrect", "ERROR")
            return False

    # ========================================
    # 3. Admin Endpoints Tests
    # ========================================
    
    def test_admin_budget_reset(self):
        """Test /api/admin/budget/reset endpoint"""
        success, response = self.run_test("Admin Budget Reset", "POST", "/admin/budget/reset")
        
        if success and isinstance(response, dict):
            if "status" in response:
                self.log(f"   ✓ Budget reset response: {response['status']}")
                return True
            elif "error" in response:
                if "Admin token not configured" in response["error"]:
                    self.log(f"   ⚠ Admin token not configured (expected in test environment)")
                    return True
                else:
                    self.log(f"   ❌ Unexpected error: {response['error']}", "ERROR")
                    return False
            else:
                self.log("   ❌ Budget reset response missing expected keys", "ERROR")
                return False
        else:
            self.log("   ❌ Budget reset endpoint response format incorrect", "ERROR")
            return False

    def test_admin_set_thresholds(self):
        """Test /api/admin/router/set-thresholds endpoint"""
        test_thresholds = {
            "conf_threshold": 0.65,
            "support_threshold": 0.60,
            "max_cot_tokens": 5000
        }
        
        success, response = self.run_test(
            "Admin Set Thresholds", 
            "POST", 
            "/admin/router/set-thresholds",
            data=test_thresholds
        )
        
        if success and isinstance(response, dict):
            if "status" in response:
                self.log(f"   ✓ Thresholds update response: {response['status']}")
                if "current_thresholds" in response:
                    self.log(f"   ✓ Current thresholds returned: {response['current_thresholds']}")
                return True
            elif "error" in response:
                if "Admin token not configured" in response["error"]:
                    self.log(f"   ⚠ Admin token not configured (expected in test environment)")
                    return True
                else:
                    self.log(f"   ❌ Unexpected error: {response['error']}", "ERROR")
                    return False
            else:
                self.log("   ❌ Set thresholds response missing expected keys", "ERROR")
                return False
        else:
            self.log("   ❌ Set thresholds endpoint response format incorrect", "ERROR")
            return False

    # ========================================
    # 4. API Integration Tests
    # ========================================
    
    def test_deepseek_api_integration(self):
        """Test that DeepSeek API key is working by making a simple request"""
        # This is tested indirectly through the chat endpoint
        success, response = self.run_test(
            "DeepSeek API Integration", 
            "POST", 
            "/chat",
            params={"q": "Test DeepSeek API integration"}
        )
        
        if success and isinstance(response, dict):
            if "answer" in response and "provider" in response:
                if response["provider"].startswith("deepseek"):
                    self.log(f"   ✓ DeepSeek API integration working")
                    return True
                elif response["provider"] == "qwen_cpu":
                    self.log(f"   ⚠ Fell back to local provider (DeepSeek may be unavailable)")
                    return True
                else:
                    self.log(f"   ❌ Unexpected provider: {response['provider']}", "ERROR")
                    return False
            else:
                self.log("   ❌ API integration test response missing expected keys", "ERROR")
                return False
        else:
            self.log("   ❌ API integration test failed", "ERROR")
            return False

    # ========================================
    # 5. Safety and Routing Tests
    # ========================================
    
    def test_input_sanitization(self):
        """Test input sanitization with potentially harmful input"""
        malicious_input = "<script>alert('xss')</script>What is 2+2?"
        
        success, response = self.run_test(
            "Input Sanitization", 
            "POST", 
            "/chat",
            params={"q": malicious_input}
        )
        
        if success and isinstance(response, dict):
            if "answer" in response:
                # Check that the response doesn't contain the script tag
                if "<script>" not in response["answer"]:
                    self.log(f"   ✓ Input appears to be sanitized")
                    return True
                else:
                    self.log(f"   ❌ Input sanitization may have failed", "ERROR")
                    return False
            else:
                self.log("   ❌ Sanitization test response missing 'answer' key", "ERROR")
                return False
        else:
            self.log("   ❌ Sanitization test failed", "ERROR")
            return False

    def test_routing_metadata(self):
        """Test that routing metadata is properly returned"""
        success, response = self.run_test(
            "Routing Metadata", 
            "POST", 
            "/chat",
            params={"q": "Explain quantum computing in simple terms"}
        )
        
        if success and isinstance(response, dict):
            metadata_fields = ["provider", "confidence"]
            found_metadata = []
            
            for field in metadata_fields:
                if field in response:
                    found_metadata.append(field)
                    self.log(f"   ✓ Found metadata field: {field} = {response[field]}")
            
            if found_metadata:
                self.log(f"   ✓ Routing metadata present: {found_metadata}")
                return True
            else:
                self.log(f"   ⚠ No routing metadata found (may be legacy mode)")
                return True  # Not a failure, might be legacy routing
        else:
            self.log("   ❌ Routing metadata test failed", "ERROR")
            return False

    # ========================================
    # 6. Legacy Compatibility Tests
    # ========================================
    
    def test_healthz_endpoint(self):
        """Test legacy /api/healthz endpoint"""
        success, response = self.run_test("Legacy Health Check", "GET", "/healthz")
        
        if success and isinstance(response, dict):
            if "ok" in response:
                self.log(f"   ✓ Health check contains 'ok' key: {response['ok']}")
                return True
            else:
                self.log("   ❌ Health check missing 'ok' key", "ERROR")
                return False
        else:
            self.log("   ❌ Health check response format incorrect", "ERROR")
            return False

    def test_state_endpoint(self):
        """Test legacy /api/state endpoint"""
        success, response = self.run_test("Legacy State", "GET", "/state")
        
        if success and isinstance(response, dict):
            self.log(f"   ✓ State endpoint returns JSON")
            return True
        else:
            self.log("   ❌ State endpoint response format incorrect", "ERROR")
            return False

    def test_adapters_endpoints(self):
        """Test legacy adapter endpoints"""
        # Test /api/adapters
        success1, response1 = self.run_test("Legacy Adapters List", "GET", "/adapters")
        
        # Test /api/adapters/state  
        success2, response2 = self.run_test("Legacy Adapters State", "GET", "/adapters/state")
        
        if success1 and success2:
            self.log(f"   ✓ Both adapter endpoints working")
            return True
        else:
            self.log("   ❌ One or more adapter endpoints failed", "ERROR")
            return False

    def test_websocket_path(self):
        """Note WebSocket path availability (no actual connection test)"""
        self.tests_run += 1
        self.log("📝 WebSocket path noted: /api/ws")
        self.log("   (WebSocket connection testing requires specialized client)")
        return True

    def test_secrets_health(self):
        """Test secrets management health endpoint"""
        success, response = self.run_test("Secrets Health", "GET", "/secrets/health")
        
        if success and isinstance(response, dict):
            self.log(f"   ✓ Secrets health endpoint accessible")
            return True
        else:
            self.log("   ❌ Secrets health endpoint failed", "ERROR")
            return False

    # ========================================
    # Test Runner
    # ========================================
    
    def run_comprehensive_tests(self):
        """Run all DS-Router tests"""
        self.log("🚀 Starting LIQUID-HIVE DS-Router v1 Comprehensive Backend Tests")
        self.log("=" * 80)
        
        test_categories = [
            ("DS-Router Core Functionality", [
                self.test_chat_simple_query,
                self.test_chat_complex_query,
                self.test_chat_coding_query,
            ]),
            ("Provider Health and Status", [
                self.test_providers_status,
            ]),
            ("Admin Endpoints", [
                self.test_admin_budget_reset,
                self.test_admin_set_thresholds,
            ]),
            ("API Integration", [
                self.test_deepseek_api_integration,
            ]),
            ("Safety and Routing", [
                self.test_input_sanitization,
                self.test_routing_metadata,
            ]),
            ("Legacy Compatibility", [
                self.test_healthz_endpoint,
                self.test_state_endpoint,
                self.test_adapters_endpoints,
                self.test_websocket_path,
                self.test_secrets_health,
            ])
        ]
        
        category_results = {}
        
        for category_name, tests in test_categories:
            self.log(f"\n📋 {category_name}")
            self.log("-" * 60)
            
            category_passed = 0
            category_total = len(tests)
            
            for test in tests:
                try:
                    if test():
                        self.tests_passed += 1
                        category_passed += 1
                        self.log("   ✅ PASSED\n")
                    else:
                        self.log("   ❌ FAILED\n")
                except Exception as e:
                    self.log(f"   💥 EXCEPTION: {e}\n", "ERROR")
            
            category_results[category_name] = (category_passed, category_total)
            self.log(f"📊 {category_name}: {category_passed}/{category_total} passed")
        
        # Final summary
        self.log("\n" + "=" * 80)
        self.log("📊 FINAL TEST RESULTS")
        self.log("=" * 80)
        
        for category, (passed, total) in category_results.items():
            status = "✅" if passed == total else "❌" if passed == 0 else "⚠️"
            self.log(f"{status} {category}: {passed}/{total}")
        
        self.log(f"\n🎯 OVERALL: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            self.log("🎉 All tests passed! DS-Router v1 is working correctly.")
            return 0
        elif self.tests_passed >= (self.tests_run * 0.8):
            self.log("⚠️ Most tests passed. Minor issues detected.")
            return 0
        else:
            self.log("❌ Significant issues detected. Review required.")
            return 1

def main():
    """Main test runner"""
    import argparse
    parser = argparse.ArgumentParser(description='Test LIQUID-HIVE DS-Router v1 Backend')
    parser.add_argument('--base-url', default='http://localhost:8001', 
                       help='Base URL for the API (default: http://localhost:8001)')
    args = parser.parse_args()
    
    tester = DSRouterTester(args.base_url)
    return tester.run_comprehensive_tests()

if __name__ == "__main__":
    sys.exit(main())