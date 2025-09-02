"""
Base classes for the LIQUID-HIVE Tool Framework
==============================================
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ToolParameterType(Enum):
    """Supported parameter types for tools."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    type: ToolParameterType
    description: str
    required: bool = True
    default: Any = None
    choices: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None


@dataclass
class ToolResult:
    """Result returned by a tool execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseTool(ABC):
    """Abstract base class for all LIQUID-HIVE tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """List of parameters this tool accepts."""
        pass

    @property
    def category(self) -> str:
        """Category this tool belongs to (for organization)."""
        return "general"

    @property
    def version(self) -> str:
        """Version of this tool."""
        return "1.0.0"

    @property
    def requires_approval(self) -> bool:
        """Whether this tool requires operator approval before execution."""
        return False

    @property
    def risk_level(self) -> str:
        """Risk level: low, medium, high, critical."""
        return "low"

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate parameters against tool specification."""
        errors = []

        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in parameters:
                errors.append(f"Missing required parameter: {param.name}")

            if param.name in parameters:
                value = parameters[param.name]

                # Type validation
                if param.type == ToolParameterType.STRING and not isinstance(
                    value, str
                ):
                    errors.append(f"Parameter {param.name} must be a string")
                elif param.type == ToolParameterType.INTEGER and not isinstance(
                    value, int
                ):
                    errors.append(f"Parameter {param.name} must be an integer")
                elif param.type == ToolParameterType.FLOAT and not isinstance(
                    value, (int, float)
                ):
                    errors.append(f"Parameter {param.name} must be a number")
                elif param.type == ToolParameterType.BOOLEAN and not isinstance(
                    value, bool
                ):
                    errors.append(f"Parameter {param.name} must be a boolean")
                elif param.type == ToolParameterType.LIST and not isinstance(
                    value, list
                ):
                    errors.append(f"Parameter {param.name} must be a list")
                elif param.type == ToolParameterType.DICT and not isinstance(
                    value, dict
                ):
                    errors.append(f"Parameter {param.name} must be a dictionary")

                # Range validation
                if param.min_value is not None and isinstance(value, (int, float)):
                    if value < param.min_value:
                        errors.append(
                            f"Parameter {param.name} must be >= {param.min_value}"
                        )

                if param.max_value is not None and isinstance(value, (int, float)):
                    if value > param.max_value:
                        errors.append(
                            f"Parameter {param.name} must be <= {param.max_value}"
                        )

                # Choice validation
                if param.choices is not None and value not in param.choices:
                    errors.append(
                        f"Parameter {param.name} must be one of: {param.choices}"
                    )

        return errors

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    async def safe_execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute tool with validation and error handling."""
        try:
            # Validate parameters
            validation_errors = self.validate_parameters(parameters)
            if validation_errors:
                return ToolResult(
                    success=False,
                    error=f"Parameter validation failed: {'; '.join(validation_errors)}",
                )

            # Execute the tool
            return await self.execute(parameters)

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                metadata={"exception_type": type(e).__name__},
            )

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for this tool."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "requires_approval": self.requires_approval,
            "risk_level": self.risk_level,
            "parameters": [
                {
                    "name": param.name,
                    "type": param.type.value,
                    "description": param.description,
                    "required": param.required,
                    "default": param.default,
                    "choices": param.choices,
                    "min_value": param.min_value,
                    "max_value": param.max_value,
                }
                for param in self.parameters
            ],
        }
