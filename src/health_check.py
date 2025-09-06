"""
Comprehensive health check system for Liquid Hive.
Provides system health monitoring and status reporting.
"""

import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from .logging_config import get_logger
from .error_handling import ErrorSeverity, LiquidHiveError


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: float
    duration: float = 0.0


class HealthChecker:
    """Centralized health checking system."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.checks: Dict[str, Callable] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.last_check: Optional[float] = None
        self.check_interval: float = 30.0  # seconds

    def register_check(self, name: str, check_func: Callable):
        """Register a health check function."""
        self.checks[name] = check_func
        self.logger.info(f"Registered health check: {name}")

    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found",
                details={},
                timestamp=time.time()
            )

        start_time = time.time()

        try:
            check_func = self.checks[name]
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()

            duration = time.time() - start_time

            # Ensure result is a HealthCheckResult
            if not isinstance(result, HealthCheckResult):
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message="Check completed successfully",
                    details=result if isinstance(result, dict) else {"result": str(result)},
                    timestamp=time.time(),
                    duration=duration
                )
            else:
                result.duration = duration

            self.results[name] = result
            return result

        except Exception as e:
            duration = time.time() - start_time
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                timestamp=time.time(),
                duration=duration
            )
            self.results[name] = result
            self.logger.error(f"Health check '{name}' failed: {e}")
            return result

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        self.logger.info("Running all health checks...")

        tasks = []
        for name in self.checks:
            tasks.append(self.run_check(name))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                name = list(self.checks.keys())[i]
                self.results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check exception: {str(result)}",
                    details={"error": str(result)},
                    timestamp=time.time()
                )

        self.last_check = time.time()
        return self.results.copy()

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        if not self.results:
            return HealthStatus.UNKNOWN

        statuses = [result.status for result in self.results.values()]

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary."""
        overall_status = self.get_overall_status()

        summary = {
            "overall_status": overall_status.value,
            "last_check": self.last_check,
            "check_count": len(self.results),
            "healthy_checks": len([r for r in self.results.values() if r.status == HealthStatus.HEALTHY]),
            "warning_checks": len([r for r in self.results.values() if r.status == HealthStatus.WARNING]),
            "critical_checks": len([r for r in self.results.values() if r.status == HealthStatus.CRITICAL]),
            "unknown_checks": len([r for r in self.results.values() if r.status == HealthStatus.UNKNOWN]),
            "checks": {name: {
                "status": result.status.value,
                "message": result.message,
                "duration": result.duration,
                "timestamp": result.timestamp
            } for name, result in self.results.items()}
        }

        return summary


# Global health checker instance
health_checker = HealthChecker()


# Built-in health checks
async def check_system_resources() -> HealthCheckResult:
    """Check system resource usage."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Determine status based on thresholds
        status = HealthStatus.HEALTHY
        issues = []

        if cpu_percent > 90:
            status = HealthStatus.CRITICAL
            issues.append(f"CPU usage critical: {cpu_percent:.1f}%")
        elif cpu_percent > 80:
            status = HealthStatus.WARNING
            issues.append(f"CPU usage high: {cpu_percent:.1f}%")

        if memory.percent > 95:
            status = HealthStatus.CRITICAL
            issues.append(f"Memory usage critical: {memory.percent:.1f}%")
        elif memory.percent > 85:
            status = HealthStatus.WARNING
            issues.append(f"Memory usage high: {memory.percent:.1f}%")

        if disk.percent > 95:
            status = HealthStatus.CRITICAL
            issues.append(f"Disk usage critical: {disk.percent:.1f}%")
        elif disk.percent > 85:
            status = HealthStatus.WARNING
            issues.append(f"Disk usage high: {disk.percent:.1f}%")

        message = "System resources healthy"
        if issues:
            message = "; ".join(issues)

        return HealthCheckResult(
            name="system_resources",
            status=status,
            message=message,
            details={
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3)
            },
            timestamp=time.time()
        )

    except Exception as e:
        return HealthCheckResult(
            name="system_resources",
            status=HealthStatus.CRITICAL,
            message=f"Failed to check system resources: {str(e)}",
            details={"error": str(e)},
            timestamp=time.time()
        )


async def check_python_environment() -> HealthCheckResult:
    """Check Python environment health."""
    try:
        import sys
        import importlib

        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 11):
            return HealthCheckResult(
                name="python_environment",
                status=HealthStatus.WARNING,
                message=f"Python version {python_version.major}.{python_version.minor} is below recommended 3.11+",
                details={"python_version": f"{python_version.major}.{python_version.minor}.{python_version.micro}"},
                timestamp=time.time()
            )

        # Check critical imports
        critical_modules = [
            'fastapi',
            'uvicorn',
            'pydantic',
            'redis',
            'sqlalchemy'
        ]

        missing_modules = []
        for module in critical_modules:
            try:
                importlib.import_module(module)
            except ImportError:
                missing_modules.append(module)

        if missing_modules:
            return HealthCheckResult(
                name="python_environment",
                status=HealthStatus.CRITICAL,
                message=f"Missing critical modules: {', '.join(missing_modules)}",
                details={"missing_modules": missing_modules},
                timestamp=time.time()
            )

        return HealthCheckResult(
            name="python_environment",
            status=HealthStatus.HEALTHY,
            message="Python environment is healthy",
            details={
                "python_version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
                "critical_modules": critical_modules
            },
            timestamp=time.time()
        )

    except Exception as e:
        return HealthCheckResult(
            name="python_environment",
            status=HealthStatus.CRITICAL,
            message=f"Failed to check Python environment: {str(e)}",
            details={"error": str(e)},
            timestamp=time.time()
        )


async def check_database_connectivity() -> HealthCheckResult:
    """Check database connectivity."""
    try:
        # This would be implemented based on your actual database setup
        # For now, return a placeholder
        return HealthCheckResult(
            name="database_connectivity",
            status=HealthStatus.HEALTHY,
            message="Database connectivity check not implemented",
            details={"note": "Implement based on your database setup"},
            timestamp=time.time()
        )

    except Exception as e:
        return HealthCheckResult(
            name="database_connectivity",
            status=HealthStatus.CRITICAL,
            message=f"Database connectivity check failed: {str(e)}",
            details={"error": str(e)},
            timestamp=time.time()
        )


async def check_api_endpoints() -> HealthCheckResult:
    """Check API endpoint availability."""
    try:
        # This would check your actual API endpoints
        # For now, return a placeholder
        return HealthCheckResult(
            name="api_endpoints",
            status=HealthStatus.HEALTHY,
            message="API endpoints check not implemented",
            details={"note": "Implement based on your API setup"},
            timestamp=time.time()
        )

    except Exception as e:
        return HealthCheckResult(
            name="api_endpoints",
            status=HealthStatus.CRITICAL,
            message=f"API endpoints check failed: {str(e)}",
            details={"error": str(e)},
            timestamp=time.time()
        )


# Register built-in health checks
health_checker.register_check("system_resources", check_system_resources)
health_checker.register_check("python_environment", check_python_environment)
health_checker.register_check("database_connectivity", check_database_connectivity)
health_checker.register_check("api_endpoints", check_api_endpoints)


# Convenience functions
async def run_health_checks() -> Dict[str, HealthCheckResult]:
    """Run all health checks."""
    return await health_checker.run_all_checks()


def get_health_summary() -> Dict[str, Any]:
    """Get health summary."""
    return health_checker.get_health_summary()


def get_overall_status() -> HealthStatus:
    """Get overall health status."""
    return health_checker.get_overall_status()


def register_health_check(name: str, check_func: Callable):
    """Register a custom health check."""
    health_checker.register_check(name, check_func)
