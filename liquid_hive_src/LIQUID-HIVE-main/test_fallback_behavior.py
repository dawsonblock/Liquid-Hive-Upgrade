#!/usr/bin/env python3
"""
Fallback Behavior Test
=====================

Test that the DS-Router provides resilient fallback behavior when external API keys are not available.
This verifies that the system fails gracefully and provides meaningful responses rather than exceptions.
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/app/liquid_hive_src/LIQUID-HIVE-main')

try:
    from fastapi.testclient import TestClient
    from unified_runtime.server import app
except ImportError as e:
    print(f"❌ Failed to import required modules: {e}")
    sys.exit(1)

def log(message: str, level: str = "INFO"):
    """Log with timestamp"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def test_chat_fallback_scenarios():
    """Test various chat scenarios to ensure resilient fallback behavior"""
    log("Testing chat fallback scenarios")
    
    test_queries = [
        "Hello, how are you?",
        "What is machine learning?", 
        "Explain quantum computing",
        "Write a Python function to sort a list",
        "What is 2 + 2?",
        "Tell me about artificial intelligence",
    ]
    
    with TestClient(app) as client:
        for i, query in enumerate(test_queries, 1):
            log(f"   Test {i}: {query}")
            
            response = client.post("/api/chat", params={"q": query})
            
            # Should always return 200, never 500
            assert response.status_code == 200, f"Query '{query}' returned {response.status_code}: {response.text}"
            
            data = response.json()
            
            # Should always have an answer
            assert "answer" in data, f"Query '{query}' missing answer: {data}"
            assert isinstance(data["answer"], str), f"Answer not string: {type(data['answer'])}"
            assert len(data["answer"]) > 0, f"Empty answer for query: {query}"
            
            # Should not contain error indicators
            answer_lower = data["answer"].lower()
            error_indicators = ["exception", "traceback", "error occurred", "failed to"]
            for indicator in error_indicators:
                assert indicator not in answer_lower, f"Answer contains error indicator '{indicator}': {data['answer']}"
            
            # Log the provider used if available
            if "provider" in data:
                log(f"      Provider: {data['provider']}")
            
            log(f"      Answer: {data['answer'][:60]}...")
    
    log("   ✓ All queries handled gracefully with fallback")
    return True

def test_provider_health_without_keys():
    """Test that provider status endpoint works even without external API keys"""
    log("Testing provider health without external API keys")
    
    with TestClient(app) as client:
        response = client.get("/api/providers")
        
        assert response.status_code == 200, f"Providers endpoint failed: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, dict), f"Providers response not dict: {type(data)}"
        
        # Should have provider information
        if "providers" in data:
            providers = data["providers"]
            log(f"   Found {len(providers)} providers")
            
            for provider_name, provider_info in providers.items():
                log(f"      {provider_name}: {provider_info.get('status', 'unknown')}")
                
                # Even if unhealthy due to missing keys, should not crash
                assert isinstance(provider_info, dict), f"Provider info not dict: {provider_name}"
        
        log("   ✓ Provider status endpoint resilient")
        return True

def test_multiple_concurrent_requests():
    """Test that multiple concurrent requests don't cause issues"""
    log("Testing multiple concurrent requests")
    
    import threading
    import time
    
    results = []
    errors = []
    
    def make_request(query_id):
        try:
            with TestClient(app) as client:
                response = client.post("/api/chat", params={"q": f"Test query {query_id}"})
                
                if response.status_code == 200:
                    data = response.json()
                    if "answer" in data and len(data["answer"]) > 0:
                        results.append(f"Query {query_id}: Success")
                    else:
                        errors.append(f"Query {query_id}: Invalid response format")
                else:
                    errors.append(f"Query {query_id}: HTTP {response.status_code}")
        except Exception as e:
            errors.append(f"Query {query_id}: Exception {e}")
    
    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=make_request, args=(i,))
        threads.append(thread)
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    log(f"   Successful requests: {len(results)}")
    log(f"   Failed requests: {len(errors)}")
    
    if errors:
        for error in errors:
            log(f"      Error: {error}")
    
    # At least some requests should succeed
    assert len(results) > 0, "No requests succeeded"
    
    log("   ✓ Concurrent requests handled")
    return True

def main():
    """Main test runner"""
    log("🚀 Starting Fallback Behavior Tests")
    log("=" * 60)
    
    tests = [
        ("Chat Fallback Scenarios", test_chat_fallback_scenarios),
        ("Provider Health Without Keys", test_provider_health_without_keys),
        ("Multiple Concurrent Requests", test_multiple_concurrent_requests),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        log(f"\n🔍 Testing {test_name}")
        try:
            test_func()
            passed += 1
            log(f"   ✅ PASSED")
        except AssertionError as e:
            log(f"   ❌ FAILED: {e}")
        except Exception as e:
            log(f"   💥 EXCEPTION: {e}")
    
    log("\n" + "=" * 60)
    log("📊 FALLBACK BEHAVIOR TEST RESULTS")
    log("=" * 60)
    log(f"🎯 OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        log("🎉 All fallback behavior tests passed!")
        log("✓ System provides resilient responses without external API keys")
        log("✓ No exceptions raised during fallback scenarios")
        log("✓ Graceful degradation works as expected")
        return 0
    else:
        failed = total - passed
        log(f"❌ {failed} test(s) failed. Fallback behavior needs review.")
        return 1

if __name__ == "__main__":
    sys.exit(main())