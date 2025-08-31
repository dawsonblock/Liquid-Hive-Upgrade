#!/usr/bin/env python3
"""
MinIO/Qdrant Integration Test for LIQUID-HIVE
============================================

Tests the /api/tools/internet_ingest endpoint with and without MinIO/Qdrant environment variables.
Validates graceful error handling when services are not running.
"""

import requests
import json
import os
import sys
import subprocess
import time
import signal
from typing import Dict, Any, Optional


class MinioQdrantTester:
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.test_results = []
        self.uvicorn_process = None

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

    def test_internet_ingest_without_envs(self) -> bool:
        """Test 1: Call internet_ingest without MinIO/Qdrant environment variables"""
        print("\n🔍 Test 1: internet_ingest without MinIO/Qdrant environment variables")
        
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
                
                # Check required fields
                has_chunks = "chunks_count" in data and data["chunks_count"] > 0
                no_minio = "minio" not in data
                no_qdrant = "qdrant" not in data
                
                if has_chunks and no_minio and no_qdrant:
                    self.log_result(
                        "internet_ingest_without_envs", 
                        True, 
                        f"chunks_count={data['chunks_count']}, no minio/qdrant fields",
                        data
                    )
                    return True
                else:
                    self.log_result(
                        "internet_ingest_without_envs", 
                        False, 
                        f"Unexpected response structure: {data}",
                        data
                    )
                    return False
            else:
                self.log_result(
                    "internet_ingest_without_envs", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("internet_ingest_without_envs", False, f"Exception: {str(e)}")
            return False

    def start_test_server_with_envs(self) -> bool:
        """Start a test server with MinIO/Qdrant environment variables"""
        print("\n🔍 Starting test server with MinIO/Qdrant environment variables...")
        
        env = os.environ.copy()
        env.update({
            "MINIO_ENDPOINT": "http://127.0.0.1:9000",
            "MINIO_ACCESS_KEY": "minio",
            "MINIO_SECRET_KEY": "minio123",
            "MINIO_BUCKET": "web-raw",
            "MINIO_SECURE": "false",
            "QDRANT_URL": "http://127.0.0.1:6333",
            "QDRANT_COLLECTION": "web_corpus"
        })
        
        try:
            # Start uvicorn with environment variables
            cmd = [
                sys.executable, "-m", "uvicorn", 
                "unified_runtime.server:app", 
                "--host", "0.0.0.0", 
                "--port", "8082"
            ]
            
            self.uvicorn_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd="/app"
            )
            
            # Wait for server to start
            time.sleep(3)
            
            # Check if process is still running
            if self.uvicorn_process.poll() is None:
                print("✅ Test server started on port 8082")
                return True
            else:
                stdout, stderr = self.uvicorn_process.communicate()
                print(f"❌ Test server failed to start: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start test server: {str(e)}")
            return False

    def test_internet_ingest_with_envs(self) -> bool:
        """Test 2: Call internet_ingest with MinIO/Qdrant environment variables (services not running)"""
        print("\n🔍 Test 2: internet_ingest with MinIO/Qdrant environment variables")
        
        try:
            payload = {
                "url": "https://nasa.gov",
                "render_js": False
            }
            
            response = requests.post(
                "http://127.0.0.1:8082/api/tools/internet_ingest",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                has_chunks = "chunks_count" in data and data["chunks_count"] > 0
                has_minio_error = "minio" in data and "error" in data["minio"]
                has_qdrant_error = "qdrant" in data and "error" in data["qdrant"]
                
                if has_chunks and (has_minio_error or has_qdrant_error):
                    self.log_result(
                        "internet_ingest_with_envs", 
                        True, 
                        f"chunks_count={data['chunks_count']}, graceful error handling",
                        data
                    )
                    return True
                else:
                    self.log_result(
                        "internet_ingest_with_envs", 
                        False, 
                        f"Expected error fields not found: {data}",
                        data
                    )
                    return False
            else:
                self.log_result(
                    "internet_ingest_with_envs", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("internet_ingest_with_envs", False, f"Exception: {str(e)}")
            return False

    def test_consent_gating_behavior(self) -> bool:
        """Test 3: Verify consent gating behavior for render_js=true"""
        print("\n🔍 Test 3: Consent gating behavior for render_js=true")
        
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
                        "consent_gating_behavior", 
                        True, 
                        "Consent required as expected for render_js=true",
                        data
                    )
                    return True
                else:
                    self.log_result(
                        "consent_gating_behavior", 
                        False, 
                        f"Wrong error message: {data}",
                        data
                    )
                    return False
            else:
                self.log_result(
                    "consent_gating_behavior", 
                    False, 
                    f"Expected 403, got {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("consent_gating_behavior", False, f"Exception: {str(e)}")
            return False

    def cleanup(self):
        """Clean up test server"""
        if self.uvicorn_process:
            try:
                self.uvicorn_process.terminate()
                self.uvicorn_process.wait(timeout=5)
                print("✅ Test server terminated")
            except subprocess.TimeoutExpired:
                self.uvicorn_process.kill()
                print("⚠️ Test server killed (timeout)")
            except Exception as e:
                print(f"⚠️ Error terminating test server: {str(e)}")

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
        print("🚀 Starting MinIO/Qdrant Integration Tests")
        print("="*60)
        
        try:
            # Test 1: Without environment variables
            test1_success = self.test_internet_ingest_without_envs()
            
            # Test 2: With environment variables (start test server)
            test2_success = False
            if self.start_test_server_with_envs():
                test2_success = self.test_internet_ingest_with_envs()
            
            # Test 3: Consent gating behavior
            test3_success = self.test_consent_gating_behavior()
            
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
            
            return passed_tests == total_tests
            
        finally:
            self.cleanup()


def main():
    """Main test runner"""
    tester = MinioQdrantTester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())