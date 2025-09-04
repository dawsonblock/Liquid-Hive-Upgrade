"""Tool Registry for LIQUID-HIVE Tool Framework
===========================================

Enhanced registry with approval workflows, analytics, and audit capabilities.
"""

import importlib
import inspect
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .base_tool import BaseTool, ToolResult


class ToolRegistry:
    """Enhanced central registry for managing tools in the LIQUID-HIVE system."""

    def __init__(self):
        self.tools: dict[str, BaseTool] = {}
        self.logger = logging.getLogger(__name__)

        # Analytics and tracking
        self.execution_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_execution_time": 0.0,
                "last_executed": None,
                "error_types": defaultdict(int),
                "average_execution_time": 0.0,
            }
        )

        # Approval system
        self.pending_approvals: dict[str, dict[str, Any]] = {}
        self.approval_history: list[dict[str, Any]] = []

        # Tool usage tracking
        self.tool_usage_log: list[dict[str, Any]] = []

    def register_tool(self, tool: BaseTool) -> bool:
        """Register a tool instance."""
        try:
            if tool.name in self.tools:
                self.logger.warning(f"Tool {tool.name} already registered, overwriting")

            self.tools[tool.name] = tool
            self.logger.info(f"Registered tool: {tool.name} v{tool.version}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register tool {getattr(tool, 'name', 'unknown')}: {e}")
            return False

    def register_tool_class(self, tool_class: type[BaseTool]) -> bool:
        """Register a tool class (will instantiate it)."""
        try:
            tool_instance = tool_class()
            return self.register_tool(tool_instance)
        except Exception as e:
            self.logger.error(
                f"Failed to instantiate and register tool class {tool_class.__name__}: {e}"
            )
            return False

    def discover_tools(self, search_paths: Optional[list[str]] = None) -> int:
        """Automatically discover and register tools from specified paths.
        Returns number of tools discovered.
        """
        if search_paths is None:
            # Default search in the tools directory
            tools_dir = Path(__file__).parent
            search_paths = [str(tools_dir)]

        discovered_count = 0

        for search_path in search_paths:
            try:
                discovered_count += self._discover_tools_in_path(search_path)
            except Exception as e:
                self.logger.error(f"Failed to discover tools in {search_path}: {e}")

        return discovered_count

    def _discover_tools_in_path(self, search_path: str) -> int:
        """Discover tools in a specific path."""
        path = Path(search_path)
        if not path.exists():
            self.logger.warning(f"Tool search path does not exist: {search_path}")
            return 0

        discovered_count = 0

        # Look for Python files that might contain tools
        for py_file in path.glob("*_tool.py"):
            if py_file.name.startswith("base_"):
                continue  # Skip base classes

            try:
                # Import the module
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Look for BaseTool subclasses
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, BaseTool)
                            and obj != BaseTool
                            and not inspect.isabstract(obj)
                        ):
                            if self.register_tool_class(obj):
                                discovered_count += 1

            except Exception as e:
                self.logger.error(f"Failed to load tool from {py_file}: {e}")

        return discovered_count

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a registered tool by name."""
        return self.tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> list[str]:
        """List all registered tool names, optionally filtered by category."""
        if category is None:
            return list(self.tools.keys())

        return [name for name, tool in self.tools.items() if tool.category == category]

    def get_tool_schema(self, name: str) -> Optional[dict[str, Any]]:
        """Get the schema for a specific tool."""
        tool = self.get_tool(name)
        if tool:
            return tool.get_schema()
        return None

    def get_all_schemas(self) -> dict[str, dict[str, Any]]:
        """Get schemas for all registered tools."""
        return {name: tool.get_schema() for name, tool in self.tools.items()}

    async def execute_tool(
        self, name: str, parameters: dict[str, Any], operator_id: Optional[str] = None
    ) -> ToolResult:
        """Enhanced tool execution with approval workflow and analytics."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found")

        # Check if tool requires approval
        if tool.requires_approval and not self._is_approved(name, parameters, operator_id):
            approval_id = self._create_approval_request(name, parameters, operator_id)
            return ToolResult(
                success=False,
                error=f"Tool '{name}' requires approval. Approval request ID: {approval_id}",
                metadata={
                    "requires_approval": True,
                    "approval_id": approval_id,
                    "risk_level": tool.risk_level,
                },
            )

        # Record execution start
        start_time = time.time()
        execution_id = f"{name}_{int(start_time * 1000000)}"

        self.logger.info(
            f"Executing tool: {name} (ID: {execution_id}) with parameters: {list(parameters.keys())}"
        )

        # Execute with safety wrapper and enhanced tracking
        result = await tool.safe_execute(parameters)

        # Record execution metrics
        execution_time = time.time() - start_time
        self._record_execution_metrics(name, result, execution_time, parameters, operator_id)

        # Log execution details
        self._log_tool_usage(name, parameters, result, execution_time, operator_id, execution_id)

        # Enhanced logging based on result
        if result.success:
            self.logger.info(
                f"Tool {name} (ID: {execution_id}) executed successfully in {execution_time:.3f}s"
            )
        else:
            self.logger.warning(
                f"Tool {name} (ID: {execution_id}) execution failed: {result.error}"
            )

        # Add execution metadata to result
        result.metadata.update(
            {
                "execution_id": execution_id,
                "execution_time": execution_time,
                "operator_id": operator_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return result

    def get_tools_by_category(self) -> dict[str, list[str]]:
        """Group tools by category."""
        categories: dict[str, list[str]] = {}

        for name, tool in self.tools.items():
            category = tool.category
            if category not in categories:
                categories[category] = []
            categories[category].append(name)

        return categories

    def get_high_risk_tools(self) -> list[str]:
        """Get list of tools marked as high risk or critical."""
        return [
            name for name, tool in self.tools.items() if tool.risk_level in ["high", "critical"]
        ]

    def get_approval_required_tools(self) -> list[str]:
        """Get list of tools that require operator approval."""
        return [name for name, tool in self.tools.items() if tool.requires_approval]

    def _is_approved(
        self, tool_name: str, parameters: dict[str, Any], operator_id: Optional[str]
    ) -> bool:
        """Check if tool execution is approved."""
        # For now, implement simple approval logic
        # In production, this would check against a database or approval service
        approval_key = f"{tool_name}_{hash(str(sorted(parameters.items())))}"

        # Check if there's a pending approval that's been granted
        if approval_key in self.pending_approvals:
            approval = self.pending_approvals[approval_key]
            return approval.get("status") == "approved"

        return False

    def _create_approval_request(
        self, tool_name: str, parameters: dict[str, Any], operator_id: Optional[str]
    ) -> str:
        """Create an approval request for tool execution."""
        approval_id = f"approval_{tool_name}_{int(time.time())}"
        tool = self.get_tool(tool_name)

        approval_request = {
            "approval_id": approval_id,
            "tool_name": tool_name,
            "parameters": parameters,
            "operator_id": operator_id,
            "risk_level": tool.risk_level if tool else "unknown",
            "requested_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "reason": f"Tool '{tool_name}' requires approval due to {tool.risk_level} risk level",
        }

        approval_key = f"{tool_name}_{hash(str(sorted(parameters.items())))}"
        self.pending_approvals[approval_key] = approval_request

        self.logger.info(f"Created approval request {approval_id} for tool {tool_name}")

        return approval_id

    def approve_tool_execution(self, approval_id: str, approver_id: str) -> bool:
        """Approve a pending tool execution request."""
        for approval_key, approval in self.pending_approvals.items():
            if approval["approval_id"] == approval_id:
                approval["status"] = "approved"
                approval["approved_by"] = approver_id
                approval["approved_at"] = datetime.utcnow().isoformat()

                # Add to approval history
                self.approval_history.append(approval.copy())

                self.logger.info(f"Approved tool execution: {approval_id} by {approver_id}")
                return True

        return False

    def deny_tool_execution(self, approval_id: str, approver_id: str, reason: str = "") -> bool:
        """Deny a pending tool execution request."""
        for approval_key, approval in self.pending_approvals.items():
            if approval["approval_id"] == approval_id:
                approval["status"] = "denied"
                approval["denied_by"] = approver_id
                approval["denied_at"] = datetime.utcnow().isoformat()
                approval["denial_reason"] = reason

                # Add to approval history
                self.approval_history.append(approval.copy())

                # Remove from pending
                del self.pending_approvals[approval_key]

                self.logger.info(f"Denied tool execution: {approval_id} by {approver_id}")
                return True

        return False

    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Get list of pending approval requests."""
        return [
            approval
            for approval in self.pending_approvals.values()
            if approval["status"] == "pending"
        ]

    def _record_execution_metrics(
        self,
        tool_name: str,
        result: ToolResult,
        execution_time: float,
        parameters: dict[str, Any],
        operator_id: Optional[str],
    ):
        """Record detailed execution metrics."""
        stats = self.execution_stats[tool_name]

        stats["total_executions"] += 1
        stats["total_execution_time"] += execution_time
        stats["last_executed"] = datetime.utcnow().isoformat()

        if result.success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
            # Track error types
            if result.error:
                error_type = result.error.split(":")[0] if ":" in result.error else "unknown"
                stats["error_types"][error_type] += 1

        # Update average execution time
        stats["average_execution_time"] = stats["total_execution_time"] / stats["total_executions"]

    def _log_tool_usage(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        result: ToolResult,
        execution_time: float,
        operator_id: Optional[str],
        execution_id: str,
    ):
        """Log detailed tool usage for audit and analysis."""
        log_entry = {
            "execution_id": execution_id,
            "tool_name": tool_name,
            "operator_id": operator_id,
            "timestamp": datetime.utcnow().isoformat(),
            "parameters": parameters,
            "success": result.success,
            "error": result.error if not result.success else None,
            "execution_time": execution_time,
            "data_size": len(str(result.data)) if result.data else 0,
            "metadata": result.metadata,
        }

        self.tool_usage_log.append(log_entry)

        # Keep only last 1000 entries to prevent memory issues
        if len(self.tool_usage_log) > 1000:
            self.tool_usage_log = self.tool_usage_log[-1000:]

    def get_tool_analytics(self, tool_name: Optional[str] = None, days: int = 7) -> dict[str, Any]:
        """Get analytics for tools."""
        if tool_name:
            if tool_name not in self.execution_stats:
                return {"error": f"No execution data for tool: {tool_name}"}

            stats = self.execution_stats[tool_name].copy()

            # Convert defaultdict to regular dict for JSON serialization
            if "error_types" in stats:
                stats["error_types"] = dict(stats["error_types"])

            return {
                "tool_name": tool_name,
                "stats": stats,
                "recent_usage": self._get_recent_usage(tool_name, days),
            }
        else:
            # Return analytics for all tools
            all_stats = {}
            for name, stats in self.execution_stats.items():
                stats_copy = stats.copy()
                if "error_types" in stats_copy:
                    stats_copy["error_types"] = dict(stats_copy["error_types"])
                all_stats[name] = stats_copy

            return {
                "overall_stats": all_stats,
                "most_used_tools": self._get_most_used_tools(),
                "error_summary": self._get_error_summary(),
                "performance_summary": self._get_performance_summary(),
            }

    def _get_recent_usage(self, tool_name: str, days: int) -> list[dict[str, Any]]:
        """Get recent usage for a specific tool."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        recent_usage = [
            entry
            for entry in self.tool_usage_log
            if (
                entry["tool_name"] == tool_name
                and datetime.fromisoformat(entry["timestamp"]) > cutoff_date
            )
        ]

        return sorted(recent_usage, key=lambda x: x["timestamp"], reverse=True)[:50]

    def _get_most_used_tools(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most frequently used tools."""
        tool_usage = [
            {
                "tool_name": name,
                "total_executions": stats["total_executions"],
                "success_rate": (stats["successful_executions"] / stats["total_executions"]) * 100
                if stats["total_executions"] > 0
                else 0,
                "average_execution_time": stats["average_execution_time"],
            }
            for name, stats in self.execution_stats.items()
        ]

        return sorted(tool_usage, key=lambda x: x["total_executions"], reverse=True)[:limit]

    def _get_error_summary(self) -> dict[str, Any]:
        """Get summary of errors across all tools."""
        total_errors = 0
        error_types = defaultdict(int)

        for stats in self.execution_stats.values():
            total_errors += stats["failed_executions"]
            for error_type, count in stats["error_types"].items():
                error_types[error_type] += count

        return {
            "total_errors": total_errors,
            "error_types": dict(error_types),
            "tools_with_errors": len(
                [
                    name
                    for name, stats in self.execution_stats.items()
                    if stats["failed_executions"] > 0
                ]
            ),
        }

    def _get_performance_summary(self) -> dict[str, Any]:
        """Get performance summary across all tools."""
        execution_times = []
        total_executions = 0

        for stats in self.execution_stats.values():
            if stats["total_executions"] > 0:
                execution_times.append(stats["average_execution_time"])
                total_executions += stats["total_executions"]

        return {
            "total_executions": total_executions,
            "average_execution_time": sum(execution_times) / len(execution_times)
            if execution_times
            else 0,
            "fastest_tool": min(execution_times) if execution_times else 0,
            "slowest_tool": max(execution_times) if execution_times else 0,
        }


# Global registry instance
global_registry = ToolRegistry()
