#!/usr/bin/env python3
"""
Backend Stack Verification Test
Tests the LIQUID-HIVE backend endpoints as requested by main agent.
"""

import requests
import json
import sys
from datetime import datetime

class BackendVerificationTester:
    def __init__(self, base_url="http://127.0.0.1:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []

    def log_result(self, test_name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        result = f"{status} - {test_name}"
        if details:
            result += f": {details}"
        
        print(result)
        self.results.append(result)
        return success

    def test_healthz(self):
        """Test GET /api/healthz"""
        try:
            response = requests.get(f"{self.base_url}/api/healthz", timeout=10)
            if response.status_code == 200:
                data = response.json()
                details = f"Status: {response.status_code}, Response: {json.dumps(data)}"
                return self.log_result("GET /api/healthz", True, details)
            else:
                return self.log_result("GET /api/healthz", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_result("GET /api/healthz", False, f"Error: {str(e)}")

    def test_metrics(self):
        """Test GET /api/metrics"""
        try:
            response = requests.get(f"{self.base_url}/api/metrics", timeout=10)
            if response.status_code == 200:
                lines = response.text.split('\n')[:10]
                details = f"Status: {response.status_code}, First 10 lines: {lines}"
                return self.log_result("GET /api/metrics", True, details)
            else:
                return self.log_result("GET /api/metrics", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_result("GET /api/metrics", False, f"Error: {str(e)}")

    def test_internet_agent_metrics(self):
        """Test GET /api/internet-agent-metrics"""
        try:
            # Try with trailing slash first (as we saw 307 redirect)
            response = requests.get(f"{self.base_url}/api/internet-agent-metrics/", timeout=10)
            if response.status_code == 200:
                lines = response.text.split('\n')[:10]
                details = f"Status: {response.status_code}, First 10 lines: {lines}"
                return self.log_result("GET /api/internet-agent-metrics/", True, details)
            else:
                return self.log_result("GET /api/internet-agent-metrics/", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_result("GET /api/internet-agent-metrics/", False, f"Error: {str(e)}")

    def test_internet_fetch(self):
        """Test POST /api/tools/internet_fetch with render_js=false"""
        try:
            payload = {"urls": ["https://nasa.gov"], "render_js": False}
            response = requests.post(
                f"{self.base_url}/api/tools/internet_fetch",
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                # Get first 30 lines of JSON
                json_str = json.dumps(data, indent=2)
                lines = json_str.split('\n')[:30]
                details = f"Status: {response.status_code}, First 30 lines: {lines}"
                return self.log_result("POST /api/tools/internet_fetch (render_js=false)", True, details)
            else:
                return self.log_result("POST /api/tools/internet_fetch (render_js=false)", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_result("POST /api/tools/internet_fetch (render_js=false)", False, f"Error: {str(e)}")

    def test_internet_ingest(self):
        """Test POST /api/tools/internet_ingest with render_js=false"""
        try:
            payload = {"url": "https://nasa.gov", "render_js": False}
            response = requests.post(
                f"{self.base_url}/api/tools/internet_ingest",
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                details = f"Status: {response.status_code}, Response: {json.dumps(data)}"
                return self.log_result("POST /api/tools/internet_ingest (render_js=false)", True, details)
            else:
                return self.log_result("POST /api/tools/internet_ingest (render_js=false)", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_result("POST /api/tools/internet_ingest (render_js=false)", False, f"Error: {str(e)}")

    def test_consent_flow_and_render_js(self):
        """Test consent flow then render_js=true fetch"""
        try:
            # Step 1: Request consent for JS rendering
            consent_request = {
                "scope": "internet_fetch_js",
                "target": "https://nasa.gov"
            }
            response = requests.post(
                f"{self.base_url}/api/tools/consent/request",
                json=consent_request,
                timeout=10
            )
            
            if response.status_code != 200:
                return self.log_result("Consent Flow - Request", False, f"Status: {response.status_code}")
            
            # Step 2: Approve consent
            response = requests.post(
                f"{self.base_url}/api/tools/consent/approve",
                json=consent_request,
                timeout=10
            )
            
            if response.status_code != 200:
                return self.log_result("Consent Flow - Approve", False, f"Status: {response.status_code}")
            
            self.log_result("Consent Flow - Request & Approve", True, "Consent granted successfully")
            
            # Step 3: Test render_js=true fetch
            payload = {"urls": ["https://nasa.gov"], "render_js": True}
            response = requests.post(
                f"{self.base_url}/api/tools/internet_fetch",
                json=payload,
                timeout=60  # JS rendering takes longer
            )
            
            if response.status_code == 200:
                data = response.json()
                json_str = json.dumps(data, indent=2)
                lines = json_str.split('\n')[:30]
                details = f"Status: {response.status_code}, First 30 lines: {lines}"
                return self.log_result("POST /api/tools/internet_fetch (render_js=true)", True, details)
            else:
                return self.log_result("POST /api/tools/internet_fetch (render_js=true)", False, f"Status: {response.status_code}")
                
        except Exception as e:
            return self.log_result("Consent Flow & render_js=true", False, f"Error: {str(e)}")

    def test_challenge_endpoint(self):
        """Test GET /api/test/challenge"""
        try:
            response = requests.get(f"{self.base_url}/api/test/challenge", timeout=10)
            if response.status_code == 200:
                data = response.json()
                details = f"Status: {response.status_code}, Response: {json.dumps(data)}"
                return self.log_result("GET /api/test/challenge", True, details)
            else:
                return self.log_result("GET /api/test/challenge", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_result("GET /api/test/challenge", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all backend verification tests"""
        print("🚀 Starting Backend Stack Verification Tests")
        print("=" * 60)
        
        # Test all endpoints as requested
        self.test_healthz()
        self.test_metrics()
        self.test_internet_agent_metrics()
        self.test_internet_fetch()
        self.test_internet_ingest()
        self.test_consent_flow_and_render_js()
        self.test_challenge_endpoint()
        
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed. Check details above.")
            return 1

def main():
    tester = BackendVerificationTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())