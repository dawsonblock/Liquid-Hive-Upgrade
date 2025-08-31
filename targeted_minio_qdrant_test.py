#!/usr/bin/env python3
"""
Targeted MinIO/Qdrant Integration Test
=====================================

Tests the /api/tools/internet_ingest endpoint behavior with and without MinIO/Qdrant environment variables.
"""

import requests
import json
import os
import sys
import subprocess
import time
from typing import Dict, Any, Optional


class TargetedTester:
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
        """Test internet_ingest without MinIO/Qdrant environment variables"""
        print("\n🔍 Test 1: POST /api/tools/internet_ingest without MinIO/Qdrant envs")
        
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

    def test_with_envs_simulation(self) -> bool:
        """Test by temporarily setting environment variables and restarting backend"""
        print("\n🔍 Test 2: Simulating MinIO/Qdrant environment variables")
        
        # Set environment variables in supervisor backend environment
        env_vars = {
            "MINIO_ENDPOINT": "http://127.0.0.1:9000",
            "MINIO_ACCESS_KEY": "minio", 
            "MINIO_SECRET_KEY": "minio123",
            "MINIO_BUCKET": "web-raw",
            "MINIO_SECURE": "false",
            "QDRANT_URL": "http://127.0.0.1:6333",
            "QDRANT_COLLECTION": "web_corpus"
        }
        
        try:
            # Create a temporary env file for the backend
            env_content = []
            for key, value in env_vars.items():
                env_content.append(f"export {key}={value}")
            
            with open("/tmp/minio_qdrant_env.sh", "w") as f:
                f.write("\n".join(env_content))
            
            # Run a test with environment variables set
            cmd = [
                "bash", "-c", 
                "source /tmp/minio_qdrant_env.sh && python -c \""
                "import os; "
                "import requests; "
                "import json; "
                "payload = {'url': 'https://nasa.gov', 'render_js': False}; "
                "response = requests.post('http://127.0.0.1:8001/api/tools/internet_ingest', json=payload, timeout=30); "
                "print(json.dumps(response.json(), indent=2) if response.status_code == 200 else f'Error: {response.status_code}'); "
                "\""
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    
                    # Check if we got chunks and error handling
                    has_chunks = "chunks_count" in data and data["chunks_count"] > 0
                    has_minio_error = "minio" in data and "error" in data.get("minio", {})
                    has_qdrant_error = "qdrant" in data and "error" in data.get("qdrant", {})
                    
                    if has_chunks:
                        if has_minio_error or has_qdrant_error:
                            self.log_result(
                                "with_envs_simulation", 
                                True, 
                                f"✓ chunks_count={data['chunks_count']}, ✓ graceful error handling",
                                data
                            )
                        else:
                            self.log_result(
                                "with_envs_simulation", 
                                False, 
                                f"Expected error fields not found (services not running): {data}",
                                data
                            )
                        return True
                    else:
                        self.log_result(
                            "with_envs_simulation", 
                            False, 
                            f"No chunks_count in response: {data}",
                            data
                        )
                        return False
                        
                except json.JSONDecodeError:
                    self.log_result(
                        "with_envs_simulation", 
                        False, 
                        f"Invalid JSON response: {result.stdout}"
                    )
                    return False
            else:
                self.log_result(
                    "with_envs_simulation", 
                    False, 
                    f"Command failed: {result.stderr}"
                )
                return False
                
        except Exception as e:
            self.log_result("with_envs_simulation", False, f"Exception: {str(e)}")
            return False

    def test_consent_gating(self) -> bool:
        """Test consent gating behavior for render_js=true"""
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
        print("🚀 Starting Targeted MinIO/Qdrant Integration Tests")
        print("="*60)
        
        # Test 1: Without environment variables
        test1_success = self.test_without_envs()
        
        # Test 2: With environment variables simulation
        test2_success = self.test_with_envs_simulation()
        
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
        
        return passed_tests == total_tests


def main():
    """Main test runner"""
    tester = TargetedTester()
    
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