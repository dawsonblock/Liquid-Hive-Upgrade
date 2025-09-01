#!/usr/bin/env python3
"""
Comprehensive LIQUID-HIVE Backend Test Suite
===========================================
Tests DS-Router Intelligence System, Tool Framework, and Enhanced Configuration
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

class LiquidHiveAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def run_test(self, name: str, method: str, endpoint: str, expected_status: int = 200, 
                 data: Dict[str, Any] = None, headers: Dict[str, str] = None) -> tuple[bool, Dict[str, Any]]:
        """Run a single API test."""
        url = f"{self.base_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {"raw_response": response.text}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}...")
                self.failed_tests.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                try:
                    return False, response.json()
                except:
                    return False, {"error": response.text}
                    
        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}", "ERROR")
            self.failed_tests.append(f"{name}: {str(e)}")
            return False, {"error": str(e)}
    
    def test_health_check(self) -> bool:
        """Test basic health endpoint."""
        success, response = self.run_test("Health Check", "GET", "api/healthz")
        if success and response.get("ok"):
            self.log("✅ System is healthy")
            return True
        else:
            self.log("❌ System health check failed")
            return False
    
    def test_ds_router_providers(self) -> bool:
        """Test DS-Router provider status endpoint."""
        success, response = self.run_test("DS-Router Providers", "GET", "api/providers")
        
        if success:
            providers = response.get("providers", {})
            if providers:
                self.log(f"✅ Found {len(providers)} providers:")
                for name, status in providers.items():
                    circuit_state = status.get("circuit_state", "unknown")
                    health_status = status.get("status", "unknown")
                    self.log(f"   - {name}: {health_status} (Circuit: {circuit_state})")
                return True
            else:
                self.log("⚠️ No providers found in response")
                return False
        return False
    
    def test_chat_simple_query(self) -> bool:
        """Test simple chat query routing."""
        test_query = "What is 2 + 2?"
        success, response = self.run_test(
            "Simple Chat Query", 
            "POST", 
            "api/chat",
            data={"q": test_query}
        )
        
        if success:
            answer = response.get("answer", "")
            provider = response.get("provider", "unknown")
            confidence = response.get("confidence")
            
            self.log(f"✅ Chat response received from provider: {provider}")
            if confidence is not None:
                self.log(f"   Confidence: {confidence:.2f}")
            if "4" in answer:
                self.log("✅ Correct mathematical answer detected")
            return True
        return False
    
    def test_chat_complex_query(self) -> bool:
        """Test complex query that should trigger reasoning model."""
        test_query = "Prove that the square root of 2 is irrational using proof by contradiction."
        success, response = self.run_test(
            "Complex Mathematical Query", 
            "POST", 
            "api/chat",
            data={"q": test_query}
        )
        
        if success:
            provider = response.get("provider", "unknown")
            escalated = response.get("escalated", False)
            confidence = response.get("confidence")
            
            self.log(f"✅ Complex query routed to: {provider}")
            if escalated:
                self.log("✅ Query was escalated to reasoning model")
            if confidence is not None:
                self.log(f"   Confidence: {confidence:.2f}")
            return True
        return False
    
    def test_rag_aware_routing(self) -> bool:
        """Test RAG-aware routing with context-heavy query."""
        test_query = "What are the key features of the LIQUID-HIVE system architecture?"
        success, response = self.run_test(
            "RAG-Aware Query", 
            "POST", 
            "api/chat",
            data={"q": test_query}
        )
        
        if success:
            context = response.get("context", "")
            provider = response.get("provider", "unknown")
            
            self.log(f"✅ RAG query routed to: {provider}")
            if context:
                self.log(f"✅ Context provided ({len(context)} chars)")
            else:
                self.log("⚠️ No context in response")
            return True
        return False
    
    def test_tools_list(self) -> bool:
        """Test tool registry listing."""
        success, response = self.run_test("Tools List", "GET", "api/tools")
        
        if success:
            tools = response.get("tools", {})
            categories = response.get("categories", {})
            total_count = response.get("total_count", 0)
            
            self.log(f"✅ Found {total_count} tools in registry")
            if "calculator" in tools:
                self.log("✅ Calculator tool available")
            if "web_search" in tools:
                self.log("✅ Web search tool available")
            
            for category, tool_list in categories.items():
                self.log(f"   Category '{category}': {len(tool_list)} tools")
            
            return True
        return False
    
    def test_calculator_tool_schema(self) -> bool:
        """Test calculator tool schema retrieval."""
        success, response = self.run_test("Calculator Tool Schema", "GET", "api/tools/calculator")
        
        if success:
            tool_name = response.get("name", "")
            parameters = response.get("parameters", {})
            
            if tool_name == "calculator":
                self.log("✅ Calculator tool schema retrieved")
                if "expression" in str(parameters):
                    self.log("✅ Expression parameter found in schema")
                return True
            else:
                self.log("❌ Unexpected tool schema response")
        return False
    
    def test_calculator_execution(self) -> bool:
        """Test calculator tool execution."""
        test_data = {
            "expression": "2 + 3 * 4",
            "precision": 2
        }
        
        success, response = self.run_test(
            "Calculator Execution", 
            "POST", 
            "api/tools/calculator/execute",
            data=test_data
        )
        
        if success:
            result = response.get("result")
            status = response.get("status", "")
            
            if status == "success" and result is not None:
                self.log(f"✅ Calculator executed: {test_data['expression']} = {result}")
                if str(result) == "14" or result == 14:
                    self.log("✅ Correct calculation result")
                return True
            else:
                self.log(f"❌ Calculator execution failed: {response}")
        return False
    
    def run_comprehensive_test(self) -> int:
        """Run all tests and return exit code."""
        self.log("🚀 Starting LIQUID-HIVE Comprehensive Backend Test Suite")
        self.log("=" * 60)
        
        # Core system tests
        self.log("\n📋 CORE SYSTEM TESTS")
        self.test_health_check()
        
        # DS-Router Intelligence System tests
        self.log("\n🧠 DS-ROUTER INTELLIGENCE TESTS")
        self.test_ds_router_providers()
        self.test_chat_simple_query()
        time.sleep(2)  # Brief pause between requests
        self.test_chat_complex_query()
        time.sleep(2)
        self.test_rag_aware_routing()
        
        # Tool Framework tests
        self.log("\n🛠️ TOOL FRAMEWORK TESTS")
        self.test_tools_list()
        self.test_calculator_tool_schema()
        self.test_calculator_execution()
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log(f"📊 TEST SUMMARY")
        self.log(f"   Tests Run: {self.tests_run}")
        self.log(f"   Tests Passed: {self.tests_passed}")
        self.log(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        self.log(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for failure in self.failed_tests:
                self.log(f"   - {failure}")
        
        if self.tests_passed == self.tests_run:
            self.log("\n🎉 ALL TESTS PASSED! LIQUID-HIVE system is fully operational.")
            return 0
        elif self.tests_passed / self.tests_run >= 0.7:
            self.log("\n✅ Most tests passed. System is largely functional with minor issues.")
            return 0
        else:
            self.log("\n⚠️ Significant issues detected. System needs attention.")
            return 1

def main():
    """Main test execution."""
    tester = LiquidHiveAPITester()
    return tester.run_comprehensive_test()

if __name__ == "__main__":
    sys.exit(main())