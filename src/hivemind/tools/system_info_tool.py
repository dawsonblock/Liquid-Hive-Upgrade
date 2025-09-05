"""System Information Tool for LIQUID-HIVE
=======================================

A tool to gather system information, monitor resources, and check system health.
"""

import logging
import os
import platform
import time
from datetime import datetime
from typing import Any

import psutil

from .base_tool import BaseTool, ToolParameter, ToolParameterType, ToolResult


class SystemInfoTool(BaseTool):
    """System information and monitoring tool."""

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return "Get system information, resource usage, and health metrics"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="info_type",
                type=ToolParameterType.STRING,
                description="Type of system information to retrieve",
                required=True,
                choices=[
                    "basic",
                    "cpu",
                    "memory",
                    "disk",
                    "network",
                    "processes",
                    "environment",
                    "health",
                    "comprehensive",
                ],
            ),
            ToolParameter(
                name="include_sensitive",
                type=ToolParameterType.BOOLEAN,
                description="Include potentially sensitive information",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="process_count",
                type=ToolParameterType.INTEGER,
                description="Number of top processes to include",
                required=False,
                default=10,
                min_value=1,
                max_value=50,
            ),
        ]

    @property
    def category(self) -> str:
        return "system"

    @property
    def requires_approval(self) -> bool:
        return True  # System information access requires approval

    @property
    def risk_level(self) -> str:
        return "medium"  # System info can be sensitive

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        """Execute system information gathering."""
        info_type = parameters["info_type"]
        include_sensitive = parameters.get("include_sensitive", False)
        process_count = parameters.get("process_count", 10)

        try:
            if info_type == "basic":
                result = self._get_basic_info()
            elif info_type == "cpu":
                result = self._get_cpu_info()
            elif info_type == "memory":
                result = self._get_memory_info()
            elif info_type == "disk":
                result = self._get_disk_info()
            elif info_type == "network":
                result = self._get_network_info()
            elif info_type == "processes":
                result = self._get_process_info(process_count)
            elif info_type == "environment":
                result = self._get_environment_info(include_sensitive)
            elif info_type == "health":
                result = self._get_health_info()
            elif info_type == "comprehensive":
                result = self._get_comprehensive_info(include_sensitive, process_count)
            else:
                return ToolResult(success=False, error=f"Unknown info type: {info_type}")

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "info_type": info_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "include_sensitive": include_sensitive,
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=f"System information gathering failed: {e!s}")

    def _get_basic_info(self) -> dict[str, Any]:
        """Get basic system information."""
        return {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "uptime_seconds": time.time() - psutil.boot_time(),
        }

    def _get_cpu_info(self) -> dict[str, Any]:
        """Get CPU information and usage."""
        cpu_freq = psutil.cpu_freq()

        return {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "max_frequency": cpu_freq.max if cpu_freq else None,
            "min_frequency": cpu_freq.min if cpu_freq else None,
            "current_frequency": cpu_freq.current if cpu_freq else None,
            "cpu_usage_percent": psutil.cpu_percent(interval=1),
            "cpu_usage_per_core": psutil.cpu_percent(interval=1, percpu=True),
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
            "cpu_stats": psutil.cpu_stats()._asdict(),
            "cpu_times": psutil.cpu_times()._asdict(),
        }

    def _get_memory_info(self) -> dict[str, Any]:
        """Get memory information and usage."""
        virtual_mem = psutil.virtual_memory()
        swap_mem = psutil.swap_memory()

        return {
            "virtual_memory": {
                "total": virtual_mem.total,
                "available": virtual_mem.available,
                "used": virtual_mem.used,
                "free": virtual_mem.free,
                "percent": virtual_mem.percent,
                "active": getattr(virtual_mem, "active", None),
                "inactive": getattr(virtual_mem, "inactive", None),
                "buffers": getattr(virtual_mem, "buffers", None),
                "cached": getattr(virtual_mem, "cached", None),
            },
            "swap_memory": {
                "total": swap_mem.total,
                "used": swap_mem.used,
                "free": swap_mem.free,
                "percent": swap_mem.percent,
                "sin": swap_mem.sin,
                "sout": swap_mem.sout,
            },
        }

    def _get_disk_info(self) -> dict[str, Any]:
        """Get disk information and usage."""
        disk_partitions = []

        for partition in psutil.disk_partitions():
            try:
                disk_usage = psutil.disk_usage(partition.mountpoint)
                disk_partitions.append(
                    {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "opts": partition.opts,
                        "total": disk_usage.total,
                        "used": disk_usage.used,
                        "free": disk_usage.free,
                        "percent": (
                            (disk_usage.used / disk_usage.total) * 100
                            if disk_usage.total > 0
                            else 0
                        ),
                    }
                )
            except PermissionError:
                # Skip partitions we can't access
                disk_partitions.append(
                    {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "opts": partition.opts,
                        "error": "Permission denied",
                    }
                )

        disk_io = psutil.disk_io_counters()

        return {
            "partitions": disk_partitions,
            "io_counters": disk_io._asdict() if disk_io else None,
        }

    def _get_network_info(self) -> dict[str, Any]:
        """Get network information."""
        network_io = psutil.net_io_counters()
        network_interfaces = {}

        for interface, stats in psutil.net_io_counters(pernic=True).items():
            network_interfaces[interface] = stats._asdict()

        connections = []
        try:
            for conn in psutil.net_connections():
                connections.append(
                    {
                        "fd": conn.fd,
                        "family": conn.family,
                        "type": conn.type,
                        "laddr": conn.laddr,
                        "raddr": conn.raddr,
                        "status": conn.status,
                        "pid": conn.pid,
                    }
                )
        except (PermissionError, psutil.AccessDenied):
            connections = ["Permission denied - run with appropriate privileges"]

        return {
            "io_counters": network_io._asdict() if network_io else None,
            "interfaces": network_interfaces,
            "connections": connections[:20],  # Limit to first 20 connections
            "connection_count": len(connections) if isinstance(connections, list) else 0,
        }

    def _get_process_info(self, count: int) -> dict[str, Any]:
        """Get process information."""
        processes = []

        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent", "memory_info", "create_time", "status"]
        ):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort by CPU usage
        processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)

        return {
            "total_processes": len(processes),
            "top_processes": processes[:count],
            "process_count_by_status": self._count_processes_by_status(),
        }

    def _count_processes_by_status(self) -> dict[str, int]:
        """Count processes by status."""
        status_counts = {}

        for proc in psutil.process_iter(["status"]):
            try:
                status = proc.info["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return status_counts

    def _get_environment_info(self, include_sensitive: bool) -> dict[str, Any]:
        """Get environment information."""
        env_vars = dict(os.environ)

        if not include_sensitive:
            # Filter out potentially sensitive environment variables
            sensitive_patterns = ["password", "secret", "key", "token", "auth", "credential"]
            filtered_env = {}

            for key, value in env_vars.items():
                key_lower = key.lower()
                if any(pattern in key_lower for pattern in sensitive_patterns):
                    filtered_env[key] = "[FILTERED]"
                else:
                    filtered_env[key] = value

            env_vars = filtered_env

        return {
            "environment_variables": env_vars,
            "path": os.environ.get("PATH", "").split(os.pathsep),
            "home_directory": os.path.expanduser("~"),
            "current_directory": os.getcwd(),
            "user": os.environ.get("USER") or os.environ.get("USERNAME"),
            "shell": os.environ.get("SHELL"),
            "lang": os.environ.get("LANG"),
            "timezone": os.environ.get("TZ"),
        }

    def _get_health_info(self) -> dict[str, Any]:
        """Get system health information."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        # Health scoring
        health_score = 100
        issues = []

        if cpu_percent > 90:
            health_score -= 30
            issues.append(f"High CPU usage: {cpu_percent}%")
        elif cpu_percent > 70:
            health_score -= 15
            issues.append(f"Moderate CPU usage: {cpu_percent}%")

        if memory.percent > 90:
            health_score -= 30
            issues.append(f"High memory usage: {memory.percent}%")
        elif memory.percent > 70:
            health_score -= 15
            issues.append(f"Moderate memory usage: {memory.percent}%")

        # Check disk usage for root partition
        try:
            disk_usage = psutil.disk_usage("/")
            disk_percent = (disk_usage.used / disk_usage.total) * 100

            if disk_percent > 90:
                health_score -= 25
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            elif disk_percent > 80:
                health_score -= 10
                issues.append(f"Moderate disk usage: {disk_percent:.1f}%")
        except Exception as e:
            # Disk usage info unavailable; log and continue with best-effort health scoring
            logging.warning(f"Health scoring: unable to retrieve disk usage: {e!s}")

        # Check load average (on Unix-like systems)
        try:
            load_avg = os.getloadavg()
            cpu_cores = psutil.cpu_count()
            load_ratio = load_avg[0] / cpu_cores if cpu_cores else 0

            if load_ratio > 2.0:
                health_score -= 20
                issues.append(f"High system load: {load_avg[0]:.2f}")
            elif load_ratio > 1.0:
                health_score -= 10
                issues.append(f"Moderate system load: {load_avg[0]:.2f}")
        except Exception as e:
            logging.warning(f"Health scoring: unable to retrieve system load average: {e!s}")

        health_score = max(0, health_score)

        if health_score >= 90:
            status = "excellent"
        elif health_score >= 70:
            status = "good"
        elif health_score >= 50:
            status = "fair"
        else:
            status = "poor"

        return {
            "health_score": health_score,
            "status": status,
            "issues": issues,
            "recommendations": self._generate_health_recommendations(issues),
            "current_metrics": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "uptime_hours": (time.time() - psutil.boot_time()) / 3600,
            },
        }

    def _generate_health_recommendations(self, issues: list[str]) -> list[str]:
        """Generate health recommendations based on issues."""
        recommendations = []

        for issue in issues:
            if "CPU usage" in issue:
                recommendations.append("Consider closing unnecessary applications or processes")
                recommendations.append("Check for processes consuming high CPU resources")
            elif "memory usage" in issue:
                recommendations.append("Close unused applications to free memory")
                recommendations.append("Consider restarting services with memory leaks")
            elif "disk usage" in issue:
                recommendations.append("Clean up temporary files and logs")
                recommendations.append("Consider archiving or deleting old files")
            elif "system load" in issue:
                recommendations.append("Reduce concurrent processes or tasks")
                recommendations.append("Consider upgrading hardware if load is consistently high")

        return list(set(recommendations))  # Remove duplicates

    def _get_comprehensive_info(
        self, include_sensitive: bool, process_count: int
    ) -> dict[str, Any]:
        """Get comprehensive system information."""
        return {
            "basic": self._get_basic_info(),
            "cpu": self._get_cpu_info(),
            "memory": self._get_memory_info(),
            "disk": self._get_disk_info(),
            "network": self._get_network_info(),
            "processes": self._get_process_info(process_count),
            "environment": self._get_environment_info(include_sensitive),
            "health": self._get_health_info(),
        }
