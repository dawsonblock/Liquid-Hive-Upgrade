"""
LIQUID-HIVE Tool & Plugin Ecosystem
==================================

A formal framework for adding extensible tools and capabilities to the AI system.
Tools can be anything from calculators to web search to database queries.
"""

from .base_tool import BaseTool, ToolResult, ToolParameter
from .tool_registry import ToolRegistry
from .calculator_tool import CalculatorTool
from .web_search_tool import WebSearchTool

__all__ = [
    'BaseTool',
    'ToolResult', 
    'ToolParameter',
    'ToolRegistry',
    'CalculatorTool',
    'WebSearchTool'
]