"""
Performance monitoring and profiling utilities for Liquid Hive.
Provides comprehensive performance tracking and optimization insights.
"""

import time
import psutil
import threading
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import contextmanager

from .logging_config import get_logger


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: float
    unit: str
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionProfile:
    """Function profiling data."""
    name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    last_call: float = 0.0
    errors: int = 0


class PerformanceMonitor:
    """Centralized performance monitoring."""

    def __init__(self, max_history: int = 1000):
        self.logger = get_logger(__name__)
        self.max_history = max_history
        self.metrics: deque = deque(maxlen=max_history)
        self.function_profiles: Dict[str, FunctionProfile] = {}
        self.system_metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

    def start_monitoring(self, interval: float = 5.0):
        """Start system monitoring in background thread."""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_system,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        self.logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop system monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        self.logger.info("Performance monitoring stopped")

    def _monitor_system(self, interval: float):
        """Monitor system metrics in background."""
        while self._monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Error in system monitoring: {e}")
                time.sleep(interval)

    def _collect_system_metrics(self):
        """Collect current system metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            with self._lock:
                self.system_metrics = {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_percent': disk.percent,
                    'disk_used_gb': disk.used / (1024**3),
                    'disk_free_gb': disk.free / (1024**3),
                    'timestamp': time.time()
                }

                # Add to metrics history
                self.metrics.append(PerformanceMetric(
                    name='system_cpu',
                    value=cpu_percent,
                    unit='percent',
                    timestamp=time.time()
                ))

                self.metrics.append(PerformanceMetric(
                    name='system_memory',
                    value=memory.percent,
                    unit='percent',
                    timestamp=time.time()
                ))

        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = 'count',
        context: Optional[Dict[str, Any]] = None
    ):
        """Record a custom performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            context=context or {}
        )

        with self._lock:
            self.metrics.append(metric)

    def profile_function(self, func_name: str, execution_time: float, error: bool = False):
        """Record function execution data."""
        with self._lock:
            if func_name not in self.function_profiles:
                self.function_profiles[func_name] = FunctionProfile(name=func_name)

            profile = self.function_profiles[func_name]
            profile.call_count += 1
            profile.total_time += execution_time
            profile.min_time = min(profile.min_time, execution_time)
            profile.max_time = max(profile.max_time, execution_time)
            profile.avg_time = profile.total_time / profile.call_count
            profile.last_call = time.time()

            if error:
                profile.errors += 1

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        with self._lock:
            return self.system_metrics.copy()

    def get_function_profiles(self) -> Dict[str, FunctionProfile]:
        """Get function profiling data."""
        with self._lock:
            return self.function_profiles.copy()

    def get_metrics_history(
        self,
        name: Optional[str] = None,
        limit: int = 100
    ) -> List[PerformanceMetric]:
        """Get metrics history."""
        with self._lock:
            if name:
                return [m for m in self.metrics if m.name == name][-limit:]
            return list(self.metrics)[-limit:]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        with self._lock:
            summary = {
                'system_metrics': self.system_metrics,
                'total_metrics': len(self.metrics),
                'function_count': len(self.function_profiles),
                'top_functions': self._get_top_functions(),
                'recent_metrics': list(self.metrics)[-10:]
            }
            return summary

    def _get_top_functions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top functions by execution time."""
        functions = list(self.function_profiles.values())
        functions.sort(key=lambda x: x.total_time, reverse=True)

        return [
            {
                'name': f.name,
                'call_count': f.call_count,
                'total_time': f.total_time,
                'avg_time': f.avg_time,
                'errors': f.errors
            }
            for f in functions[:limit]
        ]


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def monitor_performance(
    name: Optional[str] = None,
    record_metric: bool = True,
    profile_function: bool = True
):
    """
    Decorator to monitor function performance.

    Args:
        name: Custom name for the function (defaults to function name)
        record_metric: Whether to record as a metric
        profile_function: Whether to profile the function
    """
    def decorator(func):
        func_name = name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            error = False

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = True
                raise
            finally:
                execution_time = time.time() - start_time

                if record_metric:
                    performance_monitor.record_metric(
                        name=f"function_{func_name}",
                        value=execution_time,
                        unit='seconds',
                        context={'function': func_name, 'error': error}
                    )

                if profile_function:
                    performance_monitor.profile_function(func_name, execution_time, error)

        return wrapper
    return decorator


@contextmanager
def measure_time(name: str, unit: str = 'seconds'):
    """Context manager to measure execution time."""
    start_time = time.time()
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        performance_monitor.record_metric(
            name=name,
            value=execution_time,
            unit=unit
        )


def record_metric(
    name: str,
    value: float,
    unit: str = 'count',
    context: Optional[Dict[str, Any]] = None
):
    """Record a custom performance metric."""
    performance_monitor.record_metric(name, value, unit, context)


def get_performance_summary() -> Dict[str, Any]:
    """Get current performance summary."""
    return performance_monitor.get_performance_summary()


def start_performance_monitoring(interval: float = 5.0):
    """Start performance monitoring."""
    performance_monitor.start_monitoring(interval)


def stop_performance_monitoring():
    """Stop performance monitoring."""
    performance_monitor.stop_monitoring()


# Convenience functions for common metrics
def record_memory_usage(context: Optional[Dict[str, Any]] = None):
    """Record current memory usage."""
    memory = psutil.virtual_memory()
    record_metric(
        name='memory_usage',
        value=memory.percent,
        unit='percent',
        context=context
    )


def record_cpu_usage(context: Optional[Dict[str, Any]] = None):
    """Record current CPU usage."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    record_metric(
        name='cpu_usage',
        value=cpu_percent,
        unit='percent',
        context=context
    )


def record_disk_usage(context: Optional[Dict[str, Any]] = None):
    """Record current disk usage."""
    disk = psutil.disk_usage('/')
    record_metric(
        name='disk_usage',
        value=disk.percent,
        unit='percent',
        context=context
    )


# Auto-start monitoring
start_performance_monitoring()
