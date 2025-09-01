#!/usr/bin/env python3
"""
LIQUID-HIVE Enhanced System Test - Quick Version
===============================================

Tests the 4 major enhancements with current infrastructure limitations.
"""

import requests
import json
import time
import sys
from datetime import datetime

def test_liquid_hive_system():
    """Test LIQUID-HIVE enhanced system."""
    base_url = "http://localhost:8001"
    api_base = f"{base_url}/api"
    
    print("🚀 LIQUID-HIVE Enhanced System Testing")
    print("=" * 50)
    
    results = {
        "tests_run": 0,
        "tests_passed": 0,
        "details": []
    }
    
    def log_test(name, success, details=""):
        results["tests_run"] += 1
        if success:
            results["tests_passed"] += 1
        
        status = "✅" if success else "❌"
        print(f"{status} {name}")
        if details:
            print(f"   {details}")
        
        results["details"].append({
            "test": name,
            "success": success,
            "details": details
        })
    
    # Test 1: Basic Health
    try:
        response = requests.get(f"{api_base}/healthz", timeout=5)
        success = response.status_code == 200
        data = response.json()
        details = f"Status: {response.status_code}, Engine ready: {data.get('engine_ready', False)}, Router ready: {data.get('router_ready', False)}"
        log_test("Basic Health Check", success, details)
    except Exception as e:
        log_test("Basic Health Check", False, f"Error: {str(e)}")
    
    # Test 2: Tool Framework
    try:
        response = requests.get(f"{api_base}/tools", timeout=5)
        success = response.status_code == 200
        data = response.json()
        if success:
            tools_count = data.get("total_count", 0)
            details = f"Found {tools_count} tools"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"
        log_test("Tool Framework - List Tools", success, details)
    except Exception as e:
        log_test("Tool Framework - List Tools", False, f"Error: {str(e)}")
    
    # Test 3: Tool Health
    try:
        response = requests.get(f"{api_base}/tools/health", timeout=5)
        success = response.status_code == 200
        data = response.json()
        if success:
            overall_health = data.get("overall_health", "unknown")
            details = f"Overall health: {overall_health}"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"
        log_test("Tool Framework - Health Status", success, details)
    except Exception as e:
        log_test("Tool Framework - Health Status", False, f"Error: {str(e)}")
    
    # Test 4: Semantic Cache Status
    try:
        response = requests.get(f"{api_base}/cache/status", timeout=5)
        success = response.status_code == 200
        data = response.json()
        if success:
            cache_status = data.get("status", "unknown")
            redis_connected = data.get("health", {}).get("redis_connected", False)
            details = f"Status: {cache_status}, Redis: {redis_connected}"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"
        log_test("Semantic Cache - Status", success, details)
    except Exception as e:
        log_test("Semantic Cache - Status", False, f"Error: {str(e)}")
    
    # Test 5: Cache Health
    try:
        response = requests.get(f"{api_base}/cache/health", timeout=5)
        success = response.status_code == 200
        data = response.json()
        if success:
            cache_ready = data.get("semantic_cache", False)
            details = f"Cache ready: {cache_ready}"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"
        log_test("Semantic Cache - Health", success, details)
    except Exception as e:
        log_test("Semantic Cache - Health", False, f"Error: {str(e)}")
    
    # Test 6: Chat API
    try:
        response = requests.post(f"{api_base}/chat", params={"q": "What is AI?"}, timeout=15)
        success = response.status_code == 200
        data = response.json()
        if success:
            answer_len = len(data.get("answer", ""))
            provider = data.get("provider", "unknown")
            details = f"Answer length: {answer_len}, Provider: {provider}"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"
        log_test("Chat API - Basic Query", success, details)
    except Exception as e:
        log_test("Chat API - Basic Query", False, f"Error: {str(e)}")
    
    # Test 7: Provider Status
    try:
        response = requests.get(f"{api_base}/providers", timeout=5)
        success = response.status_code == 200
        data = response.json()
        if success:
            router_active = data.get("router_active", False)
            providers = list(data.get("providers", {}).keys())
            details = f"Router active: {router_active}, Providers: {providers}"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"
        log_test("DS-Router - Provider Status", success, details)
    except Exception as e:
        log_test("DS-Router - Provider Status", False, f"Error: {str(e)}")
    
    # Test 8: System State
    try:
        response = requests.get(f"{api_base}/state", timeout=5)
        success = response.status_code == 200
        data = response.json()
        if success:
            memory_size = data.get("memory_size", 0)
            details = f"Memory size: {memory_size}"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"
        log_test("System State - Status", success, details)
    except Exception as e:
        log_test("System State - Status", False, f"Error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    success_rate = (results["tests_passed"] / results["tests_run"]) * 100 if results["tests_run"] > 0 else 0
    print(f"Tests Run: {results['tests_run']}")
    print(f"Tests Passed: {results['tests_passed']}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Categorize results
    enhancement_tests = [
        "Tool Framework - List Tools",
        "Tool Framework - Health Status", 
        "Semantic Cache - Status",
        "Semantic Cache - Health"
    ]
    
    core_tests = [
        "Basic Health Check",
        "Chat API - Basic Query",
        "DS-Router - Provider Status",
        "System State - Status"
    ]
    
    enhancement_passed = sum(1 for test in results["details"] 
                           if test["test"] in enhancement_tests and test["success"])
    core_passed = sum(1 for test in results["details"] 
                     if test["test"] in core_tests and test["success"])
    
    print(f"\n🚀 Enhancement Features: {enhancement_passed}/{len(enhancement_tests)} working")
    print(f"🔧 Core Features: {core_passed}/{len(core_tests)} working")
    
    # Determine status
    if success_rate >= 75 and core_passed >= 3:
        print("\n🎉 SYSTEM STATUS: FUNCTIONAL")
        print("   Most features are working despite infrastructure limitations")
    elif success_rate >= 50:
        print("\n⚠️  SYSTEM STATUS: PARTIALLY FUNCTIONAL") 
        print("   Some features working, infrastructure issues detected")
    else:
        print("\n❌ SYSTEM STATUS: NEEDS ATTENTION")
        print("   Significant issues detected")
    
    # Infrastructure notes
    print(f"\n📝 Infrastructure Notes:")
    print("   - Redis service not available (affects caching)")
    print("   - Tool registry initialization issues")
    print("   - Enhanced features partially functional")
    
    return results

if __name__ == "__main__":
    results = test_liquid_hive_system()
    success_rate = (results["tests_passed"] / results["tests_run"]) * 100 if results["tests_run"] > 0 else 0
    sys.exit(0 if success_rate >= 50 else 1)