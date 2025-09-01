"""
Tool Registry for LIQUID-HIVE Tool Framework
===========================================

Enhanced registry with approval workflows, analytics, and audit capabilities.
"""

import importlib
import inspect
import logging
import pkgutil
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from collections import defaultdict
from datetime import datetime, timedelta

from .base_tool import BaseTool, ToolResult

class ToolRegistry:
    """Enhanced central registry for managing tools in the LIQUID-HIVE system."""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger(__name__)
        
        # Analytics and tracking
        self.execution_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
            "last_executed": None,
            "error_types": defaultdict(int),
            "average_execution_time": 0.0
        })
        
        # Approval system
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        self.approval_history: List[Dict[str, Any]] = []
        
        # Tool usage tracking
        self.tool_usage_log: List[Dict[str, Any]] = []
    
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
    
    def register_tool_class(self, tool_class: Type[BaseTool]) -> bool:
        """Register a tool class (will instantiate it)."""
        try:
            tool_instance = tool_class()
            return self.register_tool(tool_instance)
        except Exception as e:
            self.logger.error(f"Failed to instantiate and register tool class {tool_class.__name__}: {e}")
            return False
    
    def discover_tools(self, search_paths: Optional[List[str]] = None) -> int:
        """
        Automatically discover and register tools from specified paths.
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
                        if (issubclass(obj, BaseTool) and 
                            obj != BaseTool and 
                            not inspect.isabstract(obj)):
                            
                            if self.register_tool_class(obj):
                                discovered_count += 1
                            
            except Exception as e:
                self.logger.error(f"Failed to load tool from {py_file}: {e}")
        
        return discovered_count
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a registered tool by name."""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """List all registered tool names, optionally filtered by category."""
        if category is None:
            return list(self.tools.keys())
        
        return [
            name for name, tool in self.tools.items()
            if tool.category == category
        ]
    
    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the schema for a specific tool."""
        tool = self.get_tool(name)
        if tool:
            return tool.get_schema()
        return None
    
    def get_all_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Get schemas for all registered tools."""
        return {
            name: tool.get_schema()
            for name, tool in self.tools.items()
        }
    
    async def execute_tool(self, name: str, parameters: Dict[str, Any], 
                          operator_id: Optional[str] = None) -> ToolResult:
        """Enhanced tool execution with approval workflow and analytics."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found"
            )
        
        # Check if tool requires approval
        if tool.requires_approval and not self._is_approved(name, parameters, operator_id):
            approval_id = self._create_approval_request(name, parameters, operator_id)
            return ToolResult(
                success=False,
                error=f"Tool '{name}' requires approval. Approval request ID: {approval_id}",
                metadata={
                    "requires_approval": True,
                    "approval_id": approval_id,
                    "risk_level": tool.risk_level
                }
            )
        
        # Record execution start
        start_time = time.time()
        execution_id = f"{name}_{int(start_time * 1000000)}"
        
        self.logger.info(f"Executing tool: {name} (ID: {execution_id}) with parameters: {list(parameters.keys())}")
        
        # Execute with safety wrapper and enhanced tracking
        result = await tool.safe_execute(parameters)
        
        # Record execution metrics
        execution_time = time.time() - start_time
        self._record_execution_metrics(name, result, execution_time, parameters, operator_id)
        
        # Log execution details
        self._log_tool_usage(name, parameters, result, execution_time, operator_id, execution_id)
        
        # Enhanced logging based on result
        if result.success:
            self.logger.info(f"Tool {name} (ID: {execution_id}) executed successfully in {execution_time:.3f}s")
        else:
            self.logger.warning(f"Tool {name} (ID: {execution_id}) execution failed: {result.error}")
        
        # Add execution metadata to result
        result.metadata.update({
            "execution_id": execution_id,
            "execution_time": execution_time,
            "operator_id": operator_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
    
    def get_tools_by_category(self) -> Dict[str, List[str]]:
        """Group tools by category."""
        categories: Dict[str, List[str]] = {}
        
        for name, tool in self.tools.items():
            category = tool.category
            if category not in categories:
                categories[category] = []
            categories[category].append(name)
        
        return categories
    
    def get_high_risk_tools(self) -> List[str]:
        """Get list of tools marked as high risk or critical."""
        return [
            name for name, tool in self.tools.items()
            if tool.risk_level in ['high', 'critical']
        ]
    
    def get_approval_required_tools(self) -> List[str]:
        """Get list of tools that require operator approval."""
        return [
            name for name, tool in self.tools.items()
            if tool.requires_approval
        ]

# Global registry instance
global_registry = ToolRegistry()