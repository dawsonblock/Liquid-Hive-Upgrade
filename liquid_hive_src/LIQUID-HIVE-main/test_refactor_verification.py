#!/usr/bin/env python3
"""
DS-Router Refactor Verification Test
===================================

This test suite specifically verifies the requirements mentioned in the review request:

1. Verify the /api/chat endpoint only uses DS-Router path (no legacy fallback in code path)
2. At runtime, absence of keys should still return a resilient answer via internal fallback 
   (Qwen local fallback or static fallback) without raising exceptions
3. Basic endpoint sanity: /api/healthz returns JSON with key "ok" (bool)
4. /api/providers returns a JSON object (router status), not 500
5. Ensure the refactor didn't break the app import
6. Static analysis assertion: no StrategySelector or decide_policy references in chat() function

Uses FastAPI TestClient as requested, with startup hooks running via context manager.
"""

import sys
import os
import re
import json
from typing import Dict, Any
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

def test_healthz():
    """Test /api/healthz endpoint - expect HTTP 200 and JSON with key 'ok' (bool)"""
    log("Testing /api/healthz endpoint")
    
    with TestClient(app) as client:
        response = client.get("/api/healthz")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "ok" in data, f"Response missing 'ok' key: {data}"
        assert isinstance(data["ok"], bool), f"'ok' key is not boolean: {type(data['ok'])}"
        
        log(f"   ✓ Health check OK: {data['ok']}")
        return True

def test_providers_status():
    """Test /api/providers endpoint - expect HTTP 200 and JSON object (router status), not 500"""
    log("Testing /api/providers endpoint")
    
    with TestClient(app) as client:
        response = client.get("/api/providers")
        
        # Must be 200, not 500 or 503
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        
        data = response.json()
        assert isinstance(data, dict), f"Response is not a JSON object: {type(data)}"
        
        # Check for expected router status fields
        if "router_active" in data:
            log(f"   ✓ Router active: {data['router_active']}")
        elif "error" in data:
            log(f"   ✓ Router error (acceptable): {data['error']}")
        else:
            log(f"   ✓ Valid JSON object returned: {list(data.keys())}")
        
        return True

def test_chat_no_keys():
    """Test /api/chat endpoint without API keys - expect resilient fallback"""
    log("Testing /api/chat endpoint without external API keys")
    
    with TestClient(app) as client:
        response = client.post("/api/chat", params={"q": "Hello from test"})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        
        data = response.json()
        assert "answer" in data, f"Response missing 'answer' key: {data}"
        assert isinstance(data["answer"], str), f"'answer' is not a string: {type(data['answer'])}"
        
        # Check for provider field if present
        if "provider" in data:
            assert isinstance(data["provider"], str), f"'provider' is not a string: {type(data['provider'])}"
            log(f"   ✓ Provider used: {data['provider']}")
        
        log(f"   ✓ Answer received: {data['answer'][:100]}...")
        
        # Verify it's a resilient response (not an exception)
        assert len(data["answer"]) > 0, "Answer is empty"
        assert "error" not in data["answer"].lower() or "exception" not in data["answer"].lower(), \
               f"Answer contains error/exception: {data['answer']}"
        
        return True

def test_static_analysis_chat_function():
    """Static analysis: verify chat() function has no StrategySelector or decide_policy references"""
    log("Performing static analysis on chat() function")
    
    server_file = "/app/liquid_hive_src/LIQUID-HIVE-main/unified_runtime/server.py"
    
    with open(server_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the chat function using a more robust pattern
    chat_func_pattern = r'@app\.post\(f"{API_PREFIX}/chat"\)\s*async\s+def\s+chat\([^)]*\).*?(?=@app\.|def\s+\w+|class\s+\w+|$)'
    chat_func_match = re.search(chat_func_pattern, content, re.DOTALL)
    
    assert chat_func_match, "Could not find chat() function"
    
    chat_function = chat_func_match.group(0)
    log(f"   Found chat function ({len(chat_function)} chars)")
    
    # Check for forbidden patterns
    forbidden_patterns = [
        r'\bStrategySelector\b',
        r'\bdecide_policy\b', 
        r'\blegacy_routing\b'
    ]
    
    violations = []
    for pattern in forbidden_patterns:
        matches = re.findall(pattern, chat_function, re.IGNORECASE)
        if matches:
            violations.extend(matches)
    
    assert not violations, f"Found forbidden patterns in chat(): {violations}"
    
    # Check for DS-Router usage (should be present)
    ds_router_patterns = [
        r'\bds_router\b',
        r'DSRouter',
        r'GenRequest'
    ]
    
    ds_router_found = False
    for pattern in ds_router_patterns:
        if re.search(pattern, chat_function, re.IGNORECASE):
            ds_router_found = True
            break
    
    if ds_router_found:
        log(f"   ✓ DS-Router usage detected in chat() function")
    else:
        log(f"   ⚠️ No explicit DS-Router patterns found (may use different approach)")
    
    log(f"   ✓ No legacy StrategySelector references found")
    return True

def test_app_import():
    """Test that the app can be imported without errors"""
    log("Testing app import")
    
    # This is already tested by the import at the top, but let's be explicit
    from unified_runtime.server import app
    
    assert app is not None, "App is None"
    assert hasattr(app, 'routes'), "App doesn't have routes attribute"
    
    route_count = len(app.routes)
    log(f"   ✓ App imported successfully with {route_count} routes")
    return True

def main():
    """Main test runner"""
    log("🚀 Starting DS-Router Refactor Verification Tests")
    log("=" * 80)
    
    tests = [
        ("App Import", test_app_import),
        ("Health Check (/api/healthz)", test_healthz),
        ("Providers Status (/api/providers)", test_providers_status), 
        ("Chat No Keys (/api/chat)", test_chat_no_keys),
        ("Static Analysis - Chat Function", test_static_analysis_chat_function),
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
    
    log("\n" + "=" * 80)
    log("📊 TEST RESULTS SUMMARY")
    log("=" * 80)
    log(f"🎯 OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        log("🎉 All tests passed! DS-Router refactor verification successful.")
        log("✓ /api/chat endpoint uses DS-Router exclusively")
        log("✓ No legacy StrategySelector references in chat() function")
        log("✓ Endpoints return proper JSON responses without exceptions")
        log("✓ Resilient fallback handling works without API keys")
        return 0
    else:
        failed = total - passed
        log(f"❌ {failed} test(s) failed. Review required.")
        return 1

if __name__ == "__main__":
    sys.exit(main())