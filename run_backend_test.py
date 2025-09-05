#!/usr/bin/env python3
"""
Simple test runner for backend APIs
"""

import requests
import json
import time
from datetime import datetime

def test_api_endpoint(name, url, expected_status=200):
    """Test a single API endpoint"""
    print(f"\n🔍 Testing {name}: {url}")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == expected_status:
            print(f"✅ {name} - Status: {response.status_code}")
            try:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
            except:
                print(f"   Response: {response.text[:200]}")
            return True
        else:
            print(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ {name} - Error: {str(e)}")
        return False

def test_post_endpoint(name, url, data, expected_status=200):
    """Test a POST endpoint"""
    print(f"\n🔍 Testing {name}: {url}")
    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == expected_status:
            print(f"✅ {name} - Status: {response.status_code}")
            try:
                resp_data = response.json()
                print(f"   Response: {json.dumps(resp_data, indent=2)}")
            except:
                print(f"   Response: {response.text[:200]}")
            return True, response.json() if response.status_code == 200 else {}
        else:
            print(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False, {}
    except Exception as e:
        print(f"❌ {name} - Error: {str(e)}")
        return False, {}

def main():
    print("🚀 Starting Liquid Hive Backend API Testing")
    
    tests_passed = 0
    tests_total = 0
    
    # Test Main API endpoints
    print("\n" + "="*50)
    print("TESTING MAIN API (Port 8001)")
    print("="*50)
    
    tests_total += 1
    if test_api_endpoint("Main API Root", "http://localhost:8001/"):
        tests_passed += 1
    
    tests_total += 1
    if test_api_endpoint("Main API Health", "http://localhost:8001/health"):
        tests_passed += 1
    
    tests_total += 1
    if test_api_endpoint("Main API Version", "http://localhost:8001/version"):
        tests_passed += 1
    
    tests_total += 1
    if test_api_endpoint("Main API Config", "http://localhost:8001/config"):
        tests_passed += 1
    
    # Test Feedback API endpoints
    print("\n" + "="*50)
    print("TESTING FEEDBACK API (Port 8091)")
    print("="*50)
    
    tests_total += 1
    if test_api_endpoint("Feedback API Root", "http://localhost:8091/"):
        tests_passed += 1
    
    tests_total += 1
    if test_api_endpoint("Feedback API Health", "http://localhost:8091/health"):
        tests_passed += 1
    
    tests_total += 1
    if test_api_endpoint("Feedback API Metrics", "http://localhost:8091/api/v1/feedback/metrics"):
        tests_passed += 1
    
    # Test feedback collection
    feedback_data = {
        "agent_id": "test_agent_001",
        "session_id": f"test_session_{int(time.time())}",
        "context": {
            "query": "Test query for feedback collection",
            "response": "Test response"
        },
        "explicit": {
            "rating": 4,
            "feedback_text": "Good response, but could be improved"
        },
        "implicit": {
            "response_time_ms": 250.5,
            "success_rate": 0.95
        },
        "artifacts": {
            "log_reference": "test_log_001"
        },
        "metadata": {
            "test_run": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    tests_total += 1
    success, response = test_post_endpoint("Feedback Collection", "http://localhost:8091/api/v1/feedback/collect", feedback_data)
    if success:
        tests_passed += 1
    
    # Test Oracle API endpoints
    print("\n" + "="*50)
    print("TESTING ORACLE API (Port 8092)")
    print("="*50)
    
    tests_total += 1
    if test_api_endpoint("Oracle API Root", "http://localhost:8092/"):
        tests_passed += 1
    
    tests_total += 1
    if test_api_endpoint("Oracle API Health", "http://localhost:8092/health"):
        tests_passed += 1
    
    tests_total += 1
    if test_api_endpoint("Oracle API Status", "http://localhost:8092/api/v1/oracle/status"):
        tests_passed += 1
    
    # Test Oracle analysis
    analysis_request = {
        "time_window_hours": 24,
        "event_limit": 100,
        "force_analysis": True
    }
    
    tests_total += 1
    success, analysis_response = test_post_endpoint("Oracle Analysis", "http://localhost:8092/api/v1/oracle/analyze", analysis_request)
    if success:
        tests_passed += 1
        
        # Test Oracle planning if analysis succeeded
        if "analysis" in analysis_response:
            plan_request = {
                "findings": analysis_response["analysis"],
                "force_planning": True
            }
            
            tests_total += 1
            success, plan_response = test_post_endpoint("Oracle Planning", "http://localhost:8092/api/v1/oracle/plan", plan_request)
            if success:
                tests_passed += 1
    
    # Print final results
    print("\n" + "="*50)
    print("FINAL RESULTS")
    print("="*50)
    print(f"📊 Tests passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("🎉 All backend tests passed!")
        return 0
    else:
        print(f"❌ {tests_total - tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)