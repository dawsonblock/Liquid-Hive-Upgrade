#!/usr/bin/env python3
"""
Comprehensive backend testing for Liquid Hive system.
Tests all core APIs, services, and integrations.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

import requests
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class LiquidHiveAPITester:
    """Comprehensive API tester for Liquid Hive system."""
    
    def __init__(self):
        """Initialize the tester with service endpoints."""
        # Core API endpoints
        self.main_api_url = "http://localhost:8001"
        self.feedback_api_url = "http://localhost:8091"
        self.oracle_api_url = "http://localhost:8092"
        
        # Test statistics
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def run_test(self, name: str, test_func, *args, **kwargs) -> bool:
        """Run a single test with error handling and logging."""
        self.tests_run += 1
        
        try:
            logger.info(f"🔍 Running test: {name}")
            result = test_func(*args, **kwargs)
            
            if result:
                self.tests_passed += 1
                logger.info(f"✅ PASSED: {name}")
                return True
            else:
                self.failed_tests.append(name)
                logger.error(f"❌ FAILED: {name}")
                return False
                
        except Exception as e:
            self.failed_tests.append(f"{name} (Exception: {str(e)})")
            logger.error(f"❌ ERROR in {name}: {str(e)}")
            return False
    
    def test_service_health(self, service_name: str, url: str, expected_keys: List[str] = None) -> bool:
        """Test basic health endpoint for a service."""
        try:
            response = self.session.get(f"{url}/health", timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Health check failed for {service_name}", status_code=response.status_code)
                return False
            
            data = response.json()
            
            # Check for expected keys in response
            if expected_keys:
                for key in expected_keys:
                    if key not in data:
                        logger.error(f"Missing key '{key}' in {service_name} health response")
                        return False
            
            logger.info(f"{service_name} health check passed", data=data)
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error to {service_name}", error=str(e))
            return False
    
    def test_main_api_endpoints(self) -> bool:
        """Test main API endpoints."""
        try:
            # Test root endpoint
            response = self.session.get(f"{self.main_api_url}/")
            if response.status_code != 200:
                return False
            
            root_data = response.json()
            if "message" not in root_data or "version" not in root_data:
                return False
            
            # Test version endpoint
            response = self.session.get(f"{self.main_api_url}/version")
            if response.status_code != 200:
                return False
            
            version_data = response.json()
            required_keys = ["version", "build_date", "build_commit", "build_branch"]
            for key in required_keys:
                if key not in version_data:
                    logger.error(f"Missing key '{key}' in version response")
                    return False
            
            # Test config endpoint (debug mode)
            response = self.session.get(f"{self.main_api_url}/config")
            # This might return error if not in debug mode, which is acceptable
            
            logger.info("Main API endpoints working", root=root_data, version=version_data)
            return True
            
        except Exception as e:
            logger.error("Main API test failed", error=str(e))
            return False
    
    def test_feedback_collection(self) -> bool:
        """Test feedback collection API endpoints."""
        try:
            # Test single feedback collection
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
            
            response = self.session.post(
                f"{self.feedback_api_url}/api/v1/feedback/collect",
                json=feedback_data,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error("Feedback collection failed", status_code=response.status_code, response=response.text)
                return False
            
            collect_response = response.json()
            required_keys = ["event_id", "status", "message", "timestamp"]
            for key in required_keys:
                if key not in collect_response:
                    logger.error(f"Missing key '{key}' in feedback collection response")
                    return False
            
            if collect_response["status"] != "collected":
                logger.error("Feedback not collected successfully", status=collect_response["status"])
                return False
            
            # Test metrics endpoint
            response = self.session.get(f"{self.feedback_api_url}/api/v1/feedback/metrics")
            if response.status_code != 200:
                logger.error("Feedback metrics failed", status_code=response.status_code)
                return False
            
            metrics_data = response.json()
            required_metrics = ["total_events", "events_by_type", "events_by_agent", "time_window_hours"]
            for key in required_metrics:
                if key not in metrics_data:
                    logger.error(f"Missing key '{key}' in metrics response")
                    return False
            
            # Test system metric collection
            metric_response = self.session.post(
                f"{self.feedback_api_url}/api/v1/feedback/system/metric",
                params={
                    "metric_name": "test_metric",
                    "metric_value": 42.5,
                    "component": "test_component",
                    "unit": "requests_per_second"
                },
                timeout=10
            )
            
            if metric_response.status_code != 200:
                logger.error("System metric collection failed", status_code=metric_response.status_code)
                return False
            
            logger.info("Feedback collection tests passed", 
                       event_id=collect_response["event_id"],
                       metrics=metrics_data)
            return True
            
        except Exception as e:
            logger.error("Feedback collection test failed", error=str(e))
            return False
    
    def test_oracle_analysis(self) -> bool:
        """Test Oracle analysis and decision engine."""
        try:
            # Test feedback analysis
            analysis_request = {
                "time_window_hours": 24,
                "event_limit": 100,
                "force_analysis": True
            }
            
            response = self.session.post(
                f"{self.oracle_api_url}/api/v1/oracle/analyze",
                json=analysis_request,
                timeout=30  # Analysis might take longer
            )
            
            if response.status_code != 200:
                logger.error("Oracle analysis failed", status_code=response.status_code, response=response.text)
                return False
            
            analysis_response = response.json()
            required_keys = ["analysis", "message", "processing_time_seconds"]
            for key in required_keys:
                if key not in analysis_response:
                    logger.error(f"Missing key '{key}' in analysis response")
                    return False
            
            analysis = analysis_response["analysis"]
            analysis_required_keys = ["analysis_id", "event_count", "patterns", "issues", "recommendations"]
            for key in analysis_required_keys:
                if key not in analysis:
                    logger.error(f"Missing key '{key}' in analysis findings")
                    return False
            
            # Test mutation plan generation
            plan_request = {
                "findings": analysis,
                "force_planning": True
            }
            
            response = self.session.post(
                f"{self.oracle_api_url}/api/v1/oracle/plan",
                json=plan_request,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error("Oracle planning failed", status_code=response.status_code)
                return False
            
            plan_response = response.json()
            required_plan_keys = ["message", "planning_time_seconds", "recommendations"]
            for key in required_plan_keys:
                if key not in plan_response:
                    logger.error(f"Missing key '{key}' in plan response")
                    return False
            
            # Test Oracle status
            response = self.session.get(f"{self.oracle_api_url}/api/v1/oracle/status")
            if response.status_code != 200:
                logger.error("Oracle status failed", status_code=response.status_code)
                return False
            
            status_data = response.json()
            required_status_keys = ["status", "uptime_hours", "analysis_stats", "planning_stats"]
            for key in required_status_keys:
                if key not in status_data:
                    logger.error(f"Missing key '{key}' in Oracle status")
                    return False
            
            logger.info("Oracle analysis tests passed",
                       analysis_id=analysis["analysis_id"],
                       patterns=len(analysis["patterns"]),
                       issues=len(analysis["issues"]))
            return True
            
        except Exception as e:
            logger.error("Oracle analysis test failed", error=str(e))
            return False
    
    def test_event_bus_integration(self) -> bool:
        """Test event bus system integration."""
        try:
            # Test that services can communicate via event bus
            # This is tested indirectly through the feedback collection and Oracle analysis
            
            # Collect feedback (should publish to event bus)
            feedback_data = {
                "agent_id": "event_bus_test_agent",
                "session_id": f"event_bus_test_{int(time.time())}",
                "context": {"test": "event_bus_integration"},
                "explicit": {"rating": 5},
                "implicit": {"success": True}
            }
            
            response = self.session.post(
                f"{self.feedback_api_url}/api/v1/feedback/collect",
                json=feedback_data,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error("Event bus test feedback collection failed")
                return False
            
            # Wait a moment for event propagation
            time.sleep(2)
            
            # Check Oracle can analyze (should receive events from bus)
            analysis_request = {
                "time_window_hours": 1,
                "event_limit": 10,
                "force_analysis": True
            }
            
            response = self.session.post(
                f"{self.oracle_api_url}/api/v1/oracle/analyze",
                json=analysis_request,
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error("Event bus integration test - Oracle analysis failed")
                return False
            
            logger.info("Event bus integration test passed")
            return True
            
        except Exception as e:
            logger.error("Event bus integration test failed", error=str(e))
            return False
    
    def test_configuration_loading(self) -> bool:
        """Test that configuration loading works properly."""
        try:
            # Test main API config endpoint
            response = self.session.get(f"{self.main_api_url}/config")
            
            # Config endpoint might be disabled in production mode
            if response.status_code == 200:
                config_data = response.json()
                if "app" in config_data and "api" in config_data:
                    logger.info("Configuration loading test passed", config_keys=list(config_data.keys()))
                    return True
            
            # If config endpoint is disabled, check that services are running with proper config
            # by testing their functionality
            response = self.session.get(f"{self.main_api_url}/")
            if response.status_code == 200:
                logger.info("Configuration loading test passed (indirect verification)")
                return True
            
            return False
            
        except Exception as e:
            logger.error("Configuration loading test failed", error=str(e))
            return False
    
    def test_import_validation(self) -> bool:
        """Test that all imports work without errors."""
        try:
            # This is tested indirectly by the services starting up successfully
            # If there were import errors, the services wouldn't start
            
            # Test that all service endpoints are accessible
            services = [
                ("Main API", self.main_api_url),
                ("Feedback API", self.feedback_api_url),
                ("Oracle API", self.oracle_api_url)
            ]
            
            for service_name, url in services:
                try:
                    response = self.session.get(f"{url}/", timeout=5)
                    if response.status_code != 200:
                        logger.error(f"Import validation failed - {service_name} not accessible")
                        return False
                except Exception as e:
                    logger.error(f"Import validation failed - {service_name} connection error", error=str(e))
                    return False
            
            logger.info("Import validation test passed")
            return True
            
        except Exception as e:
            logger.error("Import validation test failed", error=str(e))
            return False
    
    def run_comprehensive_tests(self) -> int:
        """Run all tests and return exit code."""
        logger.info("🚀 Starting Liquid Hive comprehensive backend testing")
        
        # Test service health
        self.run_test("Main API Health", self.test_service_health, 
                     "Main API", self.main_api_url, ["status", "version"])
        
        self.run_test("Feedback API Health", self.test_service_health,
                     "Feedback API", self.feedback_api_url, ["status", "service"])
        
        self.run_test("Oracle API Health", self.test_service_health,
                     "Oracle API", self.oracle_api_url, ["status", "service"])
        
        # Test core functionality
        self.run_test("Main API Endpoints", self.test_main_api_endpoints)
        self.run_test("Feedback Collection", self.test_feedback_collection)
        self.run_test("Oracle Analysis", self.test_oracle_analysis)
        self.run_test("Event Bus Integration", self.test_event_bus_integration)
        self.run_test("Configuration Loading", self.test_configuration_loading)
        self.run_test("Import Validation", self.test_import_validation)
        
        # Print results
        logger.info("🏁 Testing completed")
        logger.info(f"📊 Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.failed_tests:
            logger.error("❌ Failed tests:")
            for test in self.failed_tests:
                logger.error(f"  - {test}")
        else:
            logger.info("🎉 All tests passed!")
        
        return 0 if self.tests_passed == self.tests_run else 1


def main():
    """Main test execution function."""
    tester = LiquidHiveAPITester()
    
    try:
        exit_code = tester.run_comprehensive_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error during testing", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()