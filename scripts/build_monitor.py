#!/usr/bin/env python3
"""
Build monitoring and metrics collection script for Liquid Hive.
Provides comprehensive build health monitoring, performance metrics, and alerts.
"""

import os
import sys
import json
import time
import logging
import psutil
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse

# Set up logging
logger = logging.getLogger(__name__)


class BuildMonitor:
    """Comprehensive build monitoring system."""

    def __init__(self, config_file: Optional[str] = None):
        self.config = self.load_config(config_file)
        self.metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "build_id": os.environ.get("BUILD_ID", "local"),
            "git_commit": self.get_git_commit(),
            "git_branch": self.get_git_branch(),
            "system": {},
            "build": {},
            "services": {},
            "performance": {},
            "alerts": []
        }

    def load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load monitoring configuration."""
        default_config = {
            "services": {
                "api": {"port": 8001, "health_endpoint": "/health"},
                "frontend": {"port": 3000, "health_endpoint": "/health"},
                "feedback": {"port": 8091, "health_endpoint": "/health"},
                "oracle": {"port": 8092, "health_endpoint": "/health"}
            },
            "thresholds": {
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "disk_usage": 90.0,
                "response_time": 5.0,
                "build_time": 300.0
            },
            "alerts": {
                "enabled": True,
                "webhook_url": os.environ.get("ALERT_WEBHOOK_URL"),
                "email": os.environ.get("ALERT_EMAIL")
            }
        }

        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()[:8]
        except subprocess.CalledProcessError:
            return "unknown"

    def get_git_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available": memory.available,
                "disk_usage": disk.percent,
                "disk_free": disk.free,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
                "process_count": len(psutil.pids()),
                "uptime": time.time() - psutil.boot_time()
            }
        except Exception as e:
            self.add_alert("error", f"Failed to collect system metrics: {e}")
            return {}

    def collect_build_metrics(self) -> Dict[str, Any]:
        """Collect build-specific metrics."""
        try:
            # Check build artifacts
            frontend_dist = Path("frontend/dist")
            docker_images = self.get_docker_images()

            return {
                "frontend_build_exists": frontend_dist.exists(),
                "frontend_build_size": self.get_directory_size(frontend_dist) if frontend_dist.exists() else 0,
                "docker_images": docker_images,
                "build_artifacts": self.get_build_artifacts(),
                "dependencies": self.check_dependencies()
            }
        except Exception as e:
            self.add_alert("error", f"Failed to collect build metrics: {e}")
            return {}

    def get_docker_images(self) -> List[Dict[str, str]]:
        """Get list of Docker images."""
        try:
            result = subprocess.run(['docker', 'images', '--format', 'json'],
                                  capture_output=True, text=True, check=True)
            images = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    img_data = json.loads(line)
                    if 'liquid-hive' in img_data.get('Repository', ''):
                        images.append({
                            "repository": img_data.get('Repository', ''),
                            "tag": img_data.get('Tag', ''),
                            "size": img_data.get('Size', ''),
                            "created": img_data.get('CreatedAt', '')
                        })
            return images
        except subprocess.CalledProcessError:
            return []

    def get_directory_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        if not path.exists():
            return 0

        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def get_build_artifacts(self) -> Dict[str, Any]:
        """Get information about build artifacts."""
        artifacts = {
            "python_cache": len(list(Path(".").rglob("__pycache__"))),
            "node_modules": Path("frontend/node_modules").exists(),
            "coverage_reports": len(list(Path(".").rglob("coverage.xml"))),
            "test_reports": len(list(Path(".").rglob("pytest-report.xml"))),
            "security_reports": len(list(Path(".").rglob("*security*.json")))
        }
        return artifacts

    def check_dependencies(self) -> Dict[str, Any]:
        """Check dependency status."""
        deps = {
            "python": self.check_command("python3", "--version"),
            "node": self.check_command("node", "--version"),
            "yarn": self.check_command("yarn", "--version"),
            "docker": self.check_command("docker", "--version"),
            "docker_compose": self.check_command("docker", "compose", "version")
        }
        return deps

    def check_command(self, *args) -> Dict[str, Any]:
        """Check if a command is available and get its version."""
        try:
            result = subprocess.run(args, capture_output=True, text=True, check=True)
            return {
                "available": True,
                "version": result.stdout.strip(),
                "error": None
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return {
                "available": False,
                "version": None,
                "error": str(e)
            }

    def check_service_health(self, service_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check health of a specific service with retry logic."""
        url = f"http://localhost:{config['port']}{config['health_endpoint']}"
        max_attempts = config.get('max_attempts', 3)
        base_delay = config.get('base_delay', 1.0)

        for attempt in range(max_attempts):
            try:
                start_time = time.time()
                response = requests.get(url, timeout=5)
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return {
                        "healthy": True,
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "url": url,
                        "error": None
                    }
                else:
                    logger.warning(f"Service {service_name} returned status {response.status_code} on attempt {attempt + 1}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Service {service_name} health check failed on attempt {attempt + 1}: {e}")

                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(delay)
                else:
                    return {
                        "healthy": False,
                        "status_code": None,
                        "response_time": None,
                        "url": url,
                        "error": str(e)
                    }

        # If we get here, all attempts failed
        return {
            "healthy": False,
            "status_code": None,
            "response_time": None,
            "url": url,
            "error": f"All {max_attempts} attempts failed"
        }

    def collect_service_metrics(self) -> Dict[str, Any]:
        """Collect metrics for all services."""
        services = {}
        for service_name, config in self.config["services"].items():
            services[service_name] = self.check_service_health(service_name, config)
        return services

    def collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance-related metrics."""
        try:
            # Get build times from recent builds
            build_times = self.get_recent_build_times()

            # Get test coverage if available
            coverage = self.get_test_coverage()

            return {
                "recent_build_times": build_times,
                "test_coverage": coverage,
                "bundle_size": self.get_bundle_size(),
                "performance_score": self.calculate_performance_score()
            }
        except Exception as e:
            self.add_alert("error", f"Failed to collect performance metrics: {e}")
            return {}

    def get_recent_build_times(self) -> List[float]:
        """Get build times from recent builds."""
        # This would typically read from a build log or database
        # For now, return empty list
        return []

    def get_test_coverage(self) -> Optional[float]:
        """Get test coverage percentage."""
        try:
            coverage_file = Path("coverage.xml")
            if coverage_file.exists():
                import xml.etree.ElementTree as ET
                tree = ET.parse(coverage_file)
                root = tree.getroot()

                # Try different coverage report formats
                # Format 1: coverage element with line-rate attribute
                if root.tag == "coverage" and "line-rate" in root.attrib:
                    return float(root.attrib["line-rate"]) * 100

                # Format 2: coverage element with lines-covered and lines-valid
                if root.tag == "coverage":
                    lines_covered = root.attrib.get("lines-covered", "0")
                    lines_valid = root.attrib.get("lines-valid", "1")
                    if lines_valid != "0":
                        return (float(lines_covered) / float(lines_valid)) * 100

                # Format 3: look for coverage child elements
                for coverage_elem in root.findall(".//coverage"):
                    if "percent" in coverage_elem.attrib:
                        return float(coverage_elem.attrib["percent"])
                    if "line-rate" in coverage_elem.attrib:
                        return float(coverage_elem.attrib["line-rate"]) * 100

                logger.warning("Could not parse coverage percentage from coverage.xml")
                return None
        except Exception as e:
            logger.exception(f"Failed to parse coverage.xml: {e}")
        return None

    def get_bundle_size(self) -> Dict[str, int]:
        """Get frontend bundle size information."""
        try:
            dist_path = Path("frontend/dist")
            if dist_path.exists():
                js_files = list(dist_path.rglob("*.js"))
                css_files = list(dist_path.rglob("*.css"))

                js_size = sum(f.stat().st_size for f in js_files)
                css_size = sum(f.stat().st_size for f in css_files)

                return {
                    "total_js_size": js_size,
                    "total_css_size": css_size,
                    "js_files": len(js_files),
                    "css_files": len(css_files)
                }
        except Exception:
            pass
        return {}

    def calculate_performance_score(self) -> float:
        """Calculate overall performance score."""
        # This is a simplified scoring algorithm
        score = 100.0

        # Deduct points for high resource usage
        if self.metrics["system"].get("cpu_usage", 0) > 80:
            score -= 20
        if self.metrics["system"].get("memory_usage", 0) > 85:
            score -= 20
        if self.metrics["system"].get("disk_usage", 0) > 90:
            score -= 30

        # Deduct points for unhealthy services
        unhealthy_services = sum(1 for s in self.metrics["services"].values()
                               if not s.get("healthy", False))
        score -= unhealthy_services * 10

        return max(0, score)

    def add_alert(self, level: str, message: str):
        """Add an alert to the metrics."""
        self.metrics["alerts"].append({
            "level": level,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })

    def check_thresholds(self):
        """Check if any metrics exceed configured thresholds."""
        thresholds = self.config["thresholds"]

        # Check system thresholds
        if self.metrics["system"].get("cpu_usage", 0) > thresholds["cpu_usage"]:
            self.add_alert("warning", f"High CPU usage: {self.metrics['system']['cpu_usage']:.1f}%")

        if self.metrics["system"].get("memory_usage", 0) > thresholds["memory_usage"]:
            self.add_alert("warning", f"High memory usage: {self.metrics['system']['memory_usage']:.1f}%")

        if self.metrics["system"].get("disk_usage", 0) > thresholds["disk_usage"]:
            self.add_alert("critical", f"High disk usage: {self.metrics['system']['disk_usage']:.1f}%")

        # Check service health
        for service_name, service_data in self.metrics["services"].items():
            if not service_data.get("healthy", False):
                self.add_alert("critical", f"Service {service_name} is unhealthy")
            elif service_data.get("response_time", 0) > thresholds["response_time"]:
                self.add_alert("warning", f"Service {service_name} slow response: {service_data['response_time']:.2f}s")

    def send_alerts(self):
        """Send alerts if configured."""
        if not self.config["alerts"]["enabled"]:
            return

        critical_alerts = [a for a in self.metrics["alerts"] if a["level"] == "critical"]
        if not critical_alerts:
            return

        # Send webhook alert
        if self.config["alerts"]["webhook_url"]:
            self.send_webhook_alert(critical_alerts)

        # Send email alert
        if self.config["alerts"]["email"]:
            self.send_email_alert(critical_alerts)

    def send_webhook_alert(self, alerts: List[Dict[str, str]]):
        """Send webhook alert."""
        try:
            payload = {
                "text": f"🚨 Liquid Hive Build Alert - {len(alerts)} critical issues",
                "attachments": [
                    {
                        "color": "danger",
                        "fields": [
                            {"title": "Alert", "value": alert["message"], "short": False}
                            for alert in alerts
                        ]
                    }
                ]
            }

            response = requests.post(self.config["alerts"]["webhook_url"],
                                   json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.exception(f"Failed to send webhook alert: {e}")
            # Record the failure in metrics
            self.metrics["webhook_failures"] = self.metrics.get("webhook_failures", 0) + 1
            self.metrics["last_webhook_error"] = str(e)

    def send_email_alert(self, alerts: List[Dict[str, str]]):
        """Send email alert."""
        # This would typically use an email service like SendGrid, SES, etc.
        print(f"Email alert would be sent to {self.config['alerts']['email']}")
        for alert in alerts:
            print(f"  - {alert['message']}")

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report."""
        self.metrics["system"] = self.collect_system_metrics()
        self.metrics["build"] = self.collect_build_metrics()
        self.metrics["services"] = self.collect_service_metrics()
        self.metrics["performance"] = self.collect_performance_metrics()

        self.check_thresholds()
        self.send_alerts()

        return self.metrics

    def save_report(self, filename: str = None):
        """Save monitoring report to file."""
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"build_monitor_report_{timestamp}.json"

        report_path = Path("reports") / filename
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)

        print(f"📊 Monitoring report saved to {report_path}")
        return report_path

    def print_summary(self):
        """Print a summary of the monitoring results."""
        print("\n" + "="*60)
        print("🔍 LIQUID HIVE BUILD MONITORING REPORT")
        print("="*60)

        # System status
        print(f"\n💻 System Status:")
        print(f"  CPU Usage: {self.metrics['system'].get('cpu_usage', 0):.1f}%")
        print(f"  Memory Usage: {self.metrics['system'].get('memory_usage', 0):.1f}%")
        print(f"  Disk Usage: {self.metrics['system'].get('disk_usage', 0):.1f}%")

        # Service status
        print(f"\n🌐 Service Status:")
        for service_name, service_data in self.metrics["services"].items():
            status = "✅ Healthy" if service_data.get("healthy", False) else "❌ Unhealthy"
            response_time = service_data.get("response_time", 0)
            print(f"  {service_name}: {status} ({response_time:.2f}s)")

        # Build status
        print(f"\n🏗️  Build Status:")
        print(f"  Frontend Build: {'✅' if self.metrics['build'].get('frontend_build_exists', False) else '❌'}")
        print(f"  Docker Images: {len(self.metrics['build'].get('docker_images', []))}")

        # Performance
        print(f"\n⚡ Performance:")
        print(f"  Performance Score: {self.metrics['performance'].get('performance_score', 0):.1f}/100")
        coverage = self.metrics['performance'].get('test_coverage')
        if coverage:
            print(f"  Test Coverage: {coverage:.1f}%")

        # Alerts
        alerts = self.metrics.get("alerts", [])
        if alerts:
            print(f"\n🚨 Alerts ({len(alerts)}):")
            for alert in alerts:
                level_icon = "🔴" if alert["level"] == "critical" else "🟡"
                print(f"  {level_icon} {alert['message']}")
        else:
            print(f"\n✅ No alerts")

        print("\n" + "="*60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Liquid Hive Build Monitor")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--watch", action="store_true", help="Watch mode (continuous monitoring)")
    parser.add_argument("--interval", type=int, default=60, help="Watch interval in seconds")

    args = parser.parse_args()

    monitor = BuildMonitor(args.config)

    if args.watch:
        print(f"🔄 Starting continuous monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop")

        try:
            while True:
                monitor.generate_report()
                monitor.print_summary()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")
    else:
        monitor.generate_report()
        monitor.print_summary()

        if args.output:
            monitor.save_report(args.output)
        else:
            monitor.save_report()


if __name__ == "__main__":
    main()
