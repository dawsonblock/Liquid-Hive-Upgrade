"""Calculator Tool for LIQUID-HIVE
==============================

A safe mathematical calculation tool with support for basic arithmetic,
trigonometry, and statistical functions.
"""

import ast
import math
import operator
import statistics
from typing import Any

from .base_tool import BaseTool, ToolParameter, ToolParameterType, ToolResult


class CalculatorTool(BaseTool):
    """Safe mathematical calculator tool."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform safe mathematical calculations including arithmetic, trigonometry, and statistics"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type=ToolParameterType.STRING,
                description="Mathematical expression to evaluate (e.g., '2 + 3 * 4', 'sin(pi/4)', 'sqrt(16)')",
                required=True,
            ),
            ToolParameter(
                name="precision",
                type=ToolParameterType.INTEGER,
                description="Number of decimal places for the result",
                required=False,
                default=6,
                min_value=0,
                max_value=15,
            ),
        ]

    @property
    def category(self) -> str:
        return "mathematics"

    def __init__(self):
        # Safe operators and functions
        self.safe_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.FloorDiv: operator.floordiv,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        self.safe_functions = {
            # Basic math
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            # Math module functions
            "sqrt": math.sqrt,
            "pow": math.pow,
            "exp": math.exp,
            "log": math.log,
            "log10": math.log10,
            "log2": math.log2,
            # Trigonometry
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "atan2": math.atan2,
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            # Rounding and conversion
            "ceil": math.ceil,
            "floor": math.floor,
            "trunc": math.trunc,
            "degrees": math.degrees,
            "radians": math.radians,
            # Statistics (for lists)
            "mean": statistics.mean,
            "median": statistics.median,
            "mode": statistics.mode,
            "stdev": statistics.stdev,
            "variance": statistics.variance,
        }

        self.safe_constants = {
            "pi": math.pi,
            "e": math.e,
            "tau": math.tau,
            "inf": math.inf,
        }

    def _safe_eval(self, node, precision: int = 6):
        """Safely evaluate an AST node."""
        if isinstance(node, ast.Constant):  # Numbers and strings
            return node.value
        elif isinstance(node, ast.Name):  # Variable names (constants)
            if node.id in self.safe_constants:
                return self.safe_constants[node.id]
            else:
                raise ValueError(f"Undefined variable: {node.id}")
        elif isinstance(node, ast.BinOp):  # Binary operations
            left = self._safe_eval(node.left, precision)
            right = self._safe_eval(node.right, precision)
            op = self.safe_ops.get(type(node.op))
            if op:
                return op(left, right)
            else:
                raise ValueError(f"Unsupported operation: {type(node.op).__name__}")
        elif isinstance(node, ast.UnaryOp):  # Unary operations
            operand = self._safe_eval(node.operand, precision)
            op = self.safe_ops.get(type(node.op))
            if op:
                return op(operand)
            else:
                raise ValueError(f"Unsupported unary operation: {type(node.op).__name__}")
        elif isinstance(node, ast.Call):  # Function calls
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name and func_name in self.safe_functions:
                args = [self._safe_eval(arg, precision) for arg in node.args]
                return self.safe_functions[func_name](*args)
            else:
                raise ValueError(f"Unsupported function: {func_name}")
        elif isinstance(node, ast.List):  # Lists
            return [self._safe_eval(item, precision) for item in node.elts]
        else:
            raise ValueError(f"Unsupported AST node type: {type(node).__name__}")

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        """Execute the calculator tool."""
        expression = parameters["expression"]
        precision = parameters.get("precision", 6)

        try:
            # Parse the expression into an AST
            tree = ast.parse(expression, mode="eval")

            # Evaluate the AST safely
            result = self._safe_eval(tree.body, precision)

            # Format the result based on precision
            if isinstance(result, float):
                if precision == 0:
                    formatted_result = int(round(result))
                else:
                    formatted_result = round(result, precision)
            else:
                formatted_result = result

            return ToolResult(
                success=True,
                data=formatted_result,
                metadata={
                    "expression": expression,
                    "precision": precision,
                    "type": type(formatted_result).__name__,
                },
            )

        except ZeroDivisionError:
            return ToolResult(success=False, error="Division by zero")
        except ValueError as e:
            return ToolResult(success=False, error=f"Invalid expression: {e!s}")
        except SyntaxError as e:
            return ToolResult(success=False, error=f"Syntax error in expression: {e!s}")
        except Exception as e:
            return ToolResult(success=False, error=f"Calculation error: {e!s}")
