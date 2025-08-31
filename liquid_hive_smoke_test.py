#!/usr/bin/env python3
"""
LIQUID-HIVE Backend E2E Smoke Tests
Tests the FastAPI app running under supervisor at 0.0.0.0:8001
All routes are prefixed with /api

Specific tests requested:
1) GET /api/healthz (expect JSON with ok, engine_ready, router_ready keys)
2) GET /api/metrics (expect Prometheus text from capsule_brain)
3) GET /api/internet-agent-metrics (expect Prometheus text from internet_agent_advanced)
4) POST /api/tools/internet_fetch with NASA URL
5) POST /api/tools/internet_ingest with NASA URL
6) Complex consent flow with JS rendering
"""

import requests
import json
import sys
from datetime import datetime

class LiquidHiveSmokeTest:
    def __init__(self, base_url="http://127.0.0.1:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failures = []

    def log_result(self, test_name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            self.failures.append(f"{test_name}: {details}")
            print(f"❌ {test_name}: FAILED")
        
        if details:
            print(f"   Details: {details}")
        print()

    def test_1_healthz(self):
        """Test 1: GET /api/healthz"""
        print("🔍 Test 1: GET /api/healthz...")
        try:
            response = requests.get(f"{self.base_url}/api/healthz", timeout=10)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("Response (first 30 lines):")
                response_text = json.dumps(data, indent=2)
                lines = response_text.split('\n')[:30]
                print('\n'.join(lines))
                
                # Check for required keys
                required_keys = ['ok', 'engine_ready', 'router_ready']
                has_keys = all(key in data for key in required_keys)
                
                self.log_result("GET /api/healthz", has_keys, 
                              f"Required keys present: {has_keys}")
                return has_keys
            else:
                self.log_result("GET /api/healthz", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("GET /api/healthz", False, f"Error: {str(e)}")
            return False

    def test_2_metrics(self):
        """Test 2: GET /api/metrics"""
        print("🔍 Test 2: GET /api/metrics...")
        try:
            response = requests.get(f"{self.base_url}/api/metrics", timeout=10)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("Response (first 10 lines):")
                lines = response.text.split('\n')[:10]
                print('\n'.join(lines))
                
                # Check if it's Prometheus format
                is_prometheus = any('# HELP' in line or '# TYPE' in line for line in lines)
                
                self.log_result("GET /api/metrics", is_prometheus, 
                              f"Prometheus format detected: {is_prometheus}")
                return is_prometheus
            else:
                self.log_result("GET /api/metrics", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("GET /api/metrics", False, f"Error: {str(e)}")
            return False

    def test_3_internet_agent_metrics(self):
        """Test 3: GET /api/internet-agent-metrics"""
        print("🔍 Test 3: GET /api/internet-agent-metrics...")
        try:
            response = requests.get(f"{self.base_url}/api/internet-agent-metrics", timeout=10)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("Response (first 10 lines):")
                lines = response.text.split('\n')[:10]
                print('\n'.join(lines))
                
                # Check if it's Prometheus format
                is_prometheus = any('# HELP' in line or '# TYPE' in line for line in lines)
                
                self.log_result("GET /api/internet-agent-metrics", is_prometheus, 
                              f"Prometheus format detected: {is_prometheus}")
                return is_prometheus
            else:
                self.log_result("GET /api/internet-agent-metrics", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("GET /api/internet-agent-metrics", False, f"Error: {str(e)}")
            return False

    def test_4_internet_fetch(self):
        """Test 4: POST /api/tools/internet_fetch"""
        print("🔍 Test 4: POST /api/tools/internet_fetch...")
        try:
            payload = {
                "urls": ["https://nasa.gov"],
                "render_js": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/tools/internet_fetch",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("Response (first 30 lines):")
                response_text = json.dumps(data, indent=2)
                lines = response_text.split('\n')[:30]
                print('\n'.join(lines))
                
                # Check for trusted or unverified entries, no errors
                has_trusted = len(data.get('trusted', [])) > 0
                has_unverified = len(data.get('unverified', [])) > 0
                has_entries = has_trusted or has_unverified
                errors_list = data.get('errors', [])
                no_errors = len(errors_list) == 0
                
                success = has_entries and no_errors
                self.log_result("POST /api/tools/internet_fetch", success, 
                              f"Has entries: {has_entries}, No errors: {no_errors}")
                return success
            else:
                self.log_result("POST /api/tools/internet_fetch", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("POST /api/tools/internet_fetch", False, f"Error: {str(e)}")
            return False

    def test_5_internet_ingest(self):
        """Test 5: POST /api/tools/internet_ingest"""
        print("🔍 Test 5: POST /api/tools/internet_ingest...")
        try:
            payload = {
                "url": "https://nasa.gov",
                "render_js": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/tools/internet_ingest",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("Response (first 30 lines):")
                response_text = json.dumps(data, indent=2)
                lines = response_text.split('\n')[:30]
                print('\n'.join(lines))
                
                # Check for chunks_count > 0
                chunks_count = data.get('chunks_count', 0)
                success = chunks_count > 0
                
                self.log_result("POST /api/tools/internet_ingest", success, 
                              f"Chunks count: {chunks_count}")
                return success
            else:
                self.log_result("POST /api/tools/internet_ingest", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("POST /api/tools/internet_ingest", False, f"Error: {str(e)}")
            return False

    def test_6_consent_flow(self):
        """Test 6: Complex consent flow with JS rendering"""
        print("🔍 Test 6: Consent Flow with JS Rendering...")
        
        # Step 1: Request consent
        print("Step 1: Requesting consent...")
        try:
            consent_payload = {
                "scope": "render_js",
                "target": "127.0.0.1",
                "ttl": 600
            }
            
            response = requests.post(
                f"{self.base_url}/api/tools/consent/request",
                json=consent_payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            print(f"Consent request status: {response.status_code}")
            
            if response.status_code != 200:
                self.log_result("Consent Request", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Consent Request", False, f"Error: {str(e)}")
            return False
        
        # Step 2: Approve consent
        print("Step 2: Approving consent...")
        try:
            response = requests.post(
                f"{self.base_url}/api/tools/consent/approve",
                json=consent_payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            print(f"Consent approval status: {response.status_code}")
            
            if response.status_code != 200:
                self.log_result("Consent Approval", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Consent Approval", False, f"Error: {str(e)}")
            return False
        
        # Step 3: Test JS rendering with approved consent
        print("Step 3: Testing JS rendering with consent...")
        try:
            js_payload = {
                "urls": ["http://127.0.0.1:8001/api/test/challenge"],
                "render_js": True
            }
            
            response = requests.post(
                f"{self.base_url}/api/tools/internet_fetch",
                json=js_payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"JS rendering status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("Response (first 30 lines):")
                response_text = json.dumps(data, indent=2)
                lines = response_text.split('\n')[:30]
                print('\n'.join(lines))
                
                # Check for unverified with status_code 200 and challenge_detected
                response_str = str(data)
                has_unverified = 'unverified' in response_str
                has_status_200 = '200' in response_str
                has_challenge = 'challenge_detected' in response_str
                
                success = has_unverified and has_status_200 and has_challenge
                self.log_result("JS Rendering with Consent", success, 
                              f"Unverified: {has_unverified}, Status 200: {has_status_200}, Challenge detected: {has_challenge}")
                return success
            else:
                self.log_result("JS Rendering with Consent", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("JS Rendering with Consent", False, f"Error: {str(e)}")
            return False

    def check_router_mounting(self):
        """Check router mounting if any endpoint is 404"""
        print("🔍 Checking router mounting in unified_runtime/server.py...")
        try:
            with open('/app/liquid_hive_src/LIQUID-HIVE-main/unified_runtime/server.py', 'r') as f:
                lines = f.readlines()
                print("Lines 110-140 from unified_runtime/server.py:")
                for i, line in enumerate(lines[109:140], 110):  # Lines 110-140
                    print(f"{i:3d}| {line.rstrip()}")
        except Exception as e:
            print(f"Error reading server.py: {str(e)}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting LIQUID-HIVE Backend E2E Smoke Tests")
        print("=" * 60)
        
        # Run tests in order
        test_results = []
        test_results.append(self.test_1_healthz())
        test_results.append(self.test_2_metrics())
        test_results.append(self.test_3_internet_agent_metrics())
        test_results.append(self.test_4_internet_fetch())
        test_results.append(self.test_5_internet_ingest())
        test_results.append(self.test_6_consent_flow())
        
        # Check if any test had 404 errors
        if any(failure for failure in self.failures if '404' in failure):
            print("\n⚠️  Found 404 errors, checking router mounting...")
            self.check_router_mounting()
        
        # Print summary
        print("=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.failures:
            print("\n❌ Failures:")
            for failure in self.failures:
                print(f"  - {failure}")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed. Check logs above for details.")
            return 1

def main():
    """Main test runner"""
    tester = LiquidHiveSmokeTest()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())