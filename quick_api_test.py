#!/usr/bin/env python3
"""
Quick API Test for LIQUID-HIVE Backend
=====================================
"""

import requests
import json
import urllib.parse

def test_api():
    base_url = "http://localhost:8001"
    
    print("🔍 Testing LIQUID-HIVE API Endpoints")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1. Health Check")
    try:
        response = requests.get(f"{base_url}/api/healthz")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Provider Status
    print("\n2. Provider Status")
    try:
        response = requests.get(f"{base_url}/api/providers")
        print(f"   Status: {response.status_code}")
        data = response.json()
        providers = data.get("providers", {})
        print(f"   Found {len(providers)} providers:")
        for name, status in providers.items():
            print(f"     - {name}: {status.get('status', 'unknown')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Chat with Query Parameter
    print("\n3. Chat API (Query Parameter)")
    try:
        query = "What is 2 + 2?"
        encoded_query = urllib.parse.quote(query)
        response = requests.post(f"{base_url}/api/chat?q={encoded_query}")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Answer: {data.get('answer', 'No answer')[:100]}...")
        print(f"   Provider: {data.get('provider', 'unknown')}")
        if 'confidence' in data:
            print(f"   Confidence: {data['confidence']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Check available endpoints
    print("\n4. Available Endpoints Check")
    endpoints_to_test = [
        "/api/tools",
        "/api/tools/calculator", 
        "/api/swarm/status",
        "/api/state",
        "/api/adapters"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}")
            print(f"   {endpoint}: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and len(data) > 0:
                    print(f"     Keys: {list(data.keys())[:3]}...")
        except Exception as e:
            print(f"   {endpoint}: Error - {e}")
    
    print("\n" + "=" * 50)
    print("✅ API Test Complete")

if __name__ == "__main__":
    test_api()