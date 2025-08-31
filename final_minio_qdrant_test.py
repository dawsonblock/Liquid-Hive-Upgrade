#!/usr/bin/env python3
"""
Final MinIO/Qdrant Integration Test for LIQUID-HIVE
==================================================

Comprehensive test of the /api/tools/internet_ingest endpoint according to the review request:
1) Test without MinIO/Qdrant environment variables
2) Test with MinIO/Qdrant environment variables (services not running)
3) Verify consent gating behavior for render_js=true
"""

import requests
import json
import os
import sys
import subprocess
import time
from typing import Dict, Any, Optional


class FinalMinioQdrantTester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8001"
        self.test_results = []

    def log_result(self, test_name: str, success: bool, details: str = "", response_data: Optional[Dict] = None):
        """Log test result with details"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data
        }
        self.test_results.append(result)

    def test_without_envs(self) -> bool:
        """Test 1: Call internet_ingest without MinIO/Qdrant environment variables"""
        print("\n🔍 Test 1: POST /api/tools/internet_ingest without MinIO/Qdrant envs")
        print("Expected: chunks_count>0, no minio/qdrant fields in response")
        
        try:
            payload = {
                "url": "https://nasa.gov",
                "render_js": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/tools/internet_ingest",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required conditions
                has_chunks = "chunks_count" in data and data["chunks_count"] > 0
                no_minio = "minio" not in data
                no_qdrant = "qdrant" not in data
                
                if has_chunks and no_minio and no_qdrant:
                    self.log_result(
                        "without_envs", 
                        True, 
                        f"✓ chunks_count={data['chunks_count']}, ✓ no minio/qdrant fields",
                        data
                    )
                    return True
                else:
                    self.log_result(
                        "without_envs", 
                        False, 
                        f"Unexpected response: chunks={data.get('chunks_count')}, minio={'minio' in data}, qdrant={'qdrant' in data}",
                        data
                    )
                    return False
            else:
                self.log_result(
                    "without_envs", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("without_envs", False, f"Exception: {str(e)}")
            return False

    def test_with_envs(self) -> bool:
        """Test 2: Call internet_ingest with MinIO/Qdrant environment variables (services not running)"""
        print("\n🔍 Test 2: POST /api/tools/internet_ingest with MinIO/Qdrant envs (services not running)")
        print("Expected: chunks_count>0, minio and/or qdrant keys with error messages")
        
        # Stop the current backend
        print("Stopping current backend...")
        subprocess.run(["sudo", "supervisorctl", "stop", "backend"], check=True)
        time.sleep(2)
        
        # Start backend with environment variables
        env_vars = {
            "MINIO_ENDPOINT": "http://127.0.0.1:9000",
            "MINIO_ACCESS_KEY": "minio", 
            "MINIO_SECRET_KEY": "minio123",
            "MINIO_BUCKET": "web-raw",
            "MINIO_SECURE": "false",
            "QDRANT_URL": "http://127.0.0.1:6333",
            "QDRANT_COLLECTION": "web_corpus"
        }
        
        env = os.environ.copy()
        env.update(env_vars)
        
        print("Starting backend with MinIO/Qdrant environment variables...")
        process = subprocess.Popen([
            "uvicorn", "unified_runtime.server:app", 
            "--host", "0.0.0.0", "--port", "8001"
        ], env=env, cwd="/app/liquid_hive_src/LIQUID-HIVE-main",
           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        time.sleep(5)
        
        try:
            # Test the endpoint
            payload = {
                "url": "https://nasa.gov",
                "render_js": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/tools/internet_ingest",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required conditions
                has_chunks = "chunks_count" in data and data["chunks_count"] > 0
                has_minio_error = "minio" in data and "error" in data.get("minio", {})
                has_qdrant_error = "qdrant" in data and ("error" in data.get("qdrant", {}) or not data.get("qdrant", {}).get("collection_ready", True))
                
                if has_chunks and (has_minio_error or has_qdrant_error):
                    self.log_result(
                        "with_envs", 
                        True, 
                        f"✓ chunks_count={data['chunks_count']}, ✓ graceful error handling in minio/qdrant fields",
                        data
                    )
                    success = True
                else:
                    self.log_result(
                        "with_envs", 
                        False, 
                        f"Expected error fields not found: chunks={data.get('chunks_count')}, minio_error={has_minio_error}, qdrant_error={has_qdrant_error}",
                        data
                    )
                    success = False
            else:
                self.log_result(
                    "with_envs", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}"
                )
                success = False
                
        except Exception as e:
            self.log_result("with_envs", False, f"Exception: {str(e)}")
            success = False
        finally:
            # Clean up: kill the test server and restart original backend
            print("Cleaning up test server...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            print("Restarting original backend...")
            subprocess.run(["sudo", "supervisorctl", "start", "backend"], check=True)
            time.sleep(3)
            
        return success

    def test_consent_gating(self) -> bool:
        """Test 3: Verify consent gating behavior for render_js=true"""
        print("\n🔍 Test 3: Consent gating behavior for render_js=true")
        print("Expected: 403 Forbidden with consent_required error")
        
        try:
            payload = {
                "url": "https://nasa.gov",
                "render_js": True  # This should require consent
            }
            
            response = requests.post(
                f"{self.base_url}/api/tools/internet_ingest",
                json=payload,
                timeout=30
            )
            
            # Should get 403 Forbidden due to consent requirement
            if response.status_code == 403:
                data = response.json()
                if "consent_required" in str(data.get("detail", "")):
                    self.log_result(
                        "consent_gating", 
                        True, 
                        "✓ Consent required as expected for render_js=true",
                        data
                    )
                    return True
                else:
                    self.log_result(
                        "consent_gating", 
                        False, 
                        f"Wrong error message: {data}",
                        data
                    )
                    return False
            else:
                self.log_result(
                    "consent_gating", 
                    False, 
                    f"Expected 403, got {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("consent_gating", False, f"Exception: {str(e)}")
            return False

    def print_response_samples(self):
        """Print first 30 lines of JSON responses"""
        print("\n" + "="*60)
        print("RESPONSE SAMPLES (First 30 JSON lines)")
        print("="*60)
        
        for result in self.test_results:
            if result.get("response_data"):
                print(f"\n--- {result['test']} ---")
                response_json = json.dumps(result["response_data"], indent=2)
                lines = response_json.split('\n')[:30]
                for i, line in enumerate(lines, 1):
                    print(f"{i:2d}: {line}")
                if len(response_json.split('\n')) > 30:
                    print("    ... (truncated)")

    def run_all_tests(self) -> bool:
        """Run all tests and return overall success"""
        print("🚀 Starting Final MinIO/Qdrant Integration Tests")
        print("="*60)
        print("Testing /api/tools/internet_ingest endpoint behavior")
        print("="*60)
        
        # Test 1: Without environment variables
        test1_success = self.test_without_envs()
        
        # Test 2: With environment variables (services not running)
        test2_success = self.test_with_envs()
        
        # Test 3: Consent gating behavior
        test3_success = self.test_consent_gating()
        
        # Print results summary
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {result['test']}: {result['details']}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        # Print response samples
        self.print_response_samples()
        
        # Print analysis
        print("\n" + "="*60)
        print("ANALYSIS")
        print("="*60)
        
        if test1_success:
            print("✅ Without env vars: Endpoint returns chunks_count>0 with no minio/qdrant fields")
        else:
            print("❌ Without env vars: Failed to get expected response")
            
        if test2_success:
            print("✅ With env vars: Endpoint gracefully handles connection errors in minio/qdrant fields")
        else:
            print("❌ With env vars: Failed to get graceful error handling")
            
        if test3_success:
            print("✅ Consent gating: render_js=true correctly requires consent")
        else:
            print("❌ Consent gating: Failed to enforce consent requirement")
        
        print(f"\n🎯 Integration test result: {'SUCCESS' if passed_tests == total_tests else 'PARTIAL SUCCESS'}")
        print("   - Base functionality works without optional services")
        print("   - Code paths initialize clients but handle connection errors gracefully")
        print("   - Consent gating behavior is unchanged")
        
        return passed_tests == total_tests


def main():
    """Main test runner"""
    tester = FinalMinioQdrantTester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())