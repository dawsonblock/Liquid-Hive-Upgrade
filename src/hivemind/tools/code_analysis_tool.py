"""
Code Analysis Tool for LIQUID-HIVE
==================================

A tool for analyzing code, performing static analysis, and providing insights
about code structure, complexity, and quality.
"""

import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .base_tool import BaseTool, ToolParameter, ToolParameterType, ToolResult


class CodeAnalysisTool(BaseTool):
    """Code analysis tool for static analysis and insights."""

    @property
    def name(self) -> str:
        return "code_analysis"

    @property
    def description(self) -> str:
        return (
            "Analyze code for structure, complexity, dependencies, and quality metrics"
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type=ToolParameterType.STRING,
                description="Source code to analyze",
                required=True,
            ),
            ToolParameter(
                name="language",
                type=ToolParameterType.STRING,
                description="Programming language",
                required=True,
                choices=["python", "javascript", "typescript", "generic"],
            ),
            ToolParameter(
                name="analysis_type",
                type=ToolParameterType.STRING,
                description="Type of analysis to perform",
                required=False,
                default="comprehensive",
                choices=[
                    "structure",
                    "complexity",
                    "dependencies",
                    "quality",
                    "comprehensive",
                ],
            ),
            ToolParameter(
                name="include_suggestions",
                type=ToolParameterType.BOOLEAN,
                description="Include improvement suggestions",
                required=False,
                default=True,
            ),
        ]

    @property
    def category(self) -> str:
        return "development"

    @property
    def risk_level(self) -> str:
        return "low"  # Static analysis is safe

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute code analysis."""
        code = parameters["code"]
        language = parameters["language"]
        analysis_type = parameters.get("analysis_type", "comprehensive")
        include_suggestions = parameters.get("include_suggestions", True)

        try:
            if language == "python":
                result = await self._analyze_python_code(
                    code, analysis_type, include_suggestions
                )
            elif language in ["javascript", "typescript"]:
                result = await self._analyze_js_code(
                    code, analysis_type, include_suggestions
                )
            else:
                result = await self._analyze_generic_code(
                    code, analysis_type, include_suggestions
                )

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "language": language,
                    "analysis_type": analysis_type,
                    "code_length": len(code),
                    "lines_of_code": len(code.splitlines()),
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=f"Code analysis failed: {str(e)}")

    async def _analyze_python_code(
        self, code: str, analysis_type: str, include_suggestions: bool
    ) -> Dict[str, Any]:
        """Analyze Python code using AST."""
        try:
            tree = ast.parse(code)

            analysis = {"language": "python", "syntax_valid": True}

            if analysis_type in ["structure", "comprehensive"]:
                analysis["structure"] = self._analyze_python_structure(tree)

            if analysis_type in ["complexity", "comprehensive"]:
                analysis["complexity"] = self._analyze_python_complexity(tree)

            if analysis_type in ["dependencies", "comprehensive"]:
                analysis["dependencies"] = self._analyze_python_dependencies(tree)

            if analysis_type in ["quality", "comprehensive"]:
                analysis["quality"] = self._analyze_python_quality(code, tree)

            if include_suggestions:
                analysis["suggestions"] = self._generate_python_suggestions(
                    code, tree, analysis
                )

            return analysis

        except SyntaxError as e:
            return {
                "language": "python",
                "syntax_valid": False,
                "syntax_error": {
                    "line": e.lineno,
                    "offset": e.offset,
                    "message": str(e),
                },
            }

    def _analyze_python_structure(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze Python code structure."""
        structure = {
            "classes": [],
            "functions": [],
            "imports": [],
            "constants": [],
            "total_lines": 0,
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                structure["classes"].append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "methods": methods,
                        "method_count": len(methods),
                        "bases": [
                            ast.unparse(base) if hasattr(ast, "unparse") else "unknown"
                            for base in node.bases
                        ],
                    }
                )

            elif isinstance(node, ast.FunctionDef):
                # Only top-level functions (not methods)
                if not any(
                    isinstance(parent, ast.ClassDef)
                    for parent in ast.walk(tree)
                    if any(child for child in ast.walk(parent) if child is node)
                ):
                    structure["functions"].append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "args": len(node.args.args),
                            "decorators": len(node.decorator_list),
                            "is_async": isinstance(node, ast.AsyncFunctionDef),
                        }
                    )

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        structure["imports"].append(
                            {
                                "module": alias.name,
                                "alias": alias.asname,
                                "type": "import",
                            }
                        )
                else:
                    for alias in node.names:
                        structure["imports"].append(
                            {
                                "module": node.module,
                                "name": alias.name,
                                "alias": alias.asname,
                                "type": "from_import",
                            }
                        )

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        structure["constants"].append(
                            {"name": target.id, "line": node.lineno}
                        )

        return structure

    def _analyze_python_complexity(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze Python code complexity."""
        complexity = {
            "cyclomatic_complexity": 1,  # Base complexity
            "nesting_depth": 0,
            "function_complexities": [],
        }

        for node in ast.walk(tree):
            # Cyclomatic complexity
            if isinstance(
                node,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.ExceptHandler,
                    ast.With,
                    ast.Assert,
                    ast.ListComp,
                    ast.DictComp,
                    ast.SetComp,
                    ast.GeneratorExp,
                ),
            ):
                complexity["cyclomatic_complexity"] += 1
            elif isinstance(node, ast.BoolOp):
                complexity["cyclomatic_complexity"] += len(node.values) - 1

        # Calculate nesting depth
        complexity["nesting_depth"] = self._calculate_nesting_depth(tree)

        # Function-level complexity
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_complexity = self._calculate_function_complexity(node)
                complexity["function_complexities"].append(
                    {
                        "name": node.name,
                        "complexity": func_complexity,
                        "line": node.lineno,
                    }
                )

        return complexity

    def _calculate_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth."""
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a specific function."""
        complexity = 1

        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _analyze_python_dependencies(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze Python code dependencies."""
        deps = {
            "stdlib_imports": [],
            "third_party_imports": [],
            "local_imports": [],
            "unused_imports": [],
        }

        # Common stdlib modules
        stdlib_modules = {
            "os",
            "sys",
            "json",
            "time",
            "datetime",
            "collections",
            "itertools",
            "functools",
            "pathlib",
            "typing",
            "re",
            "math",
            "random",
            "hashlib",
            "urllib",
            "http",
            "asyncio",
            "logging",
            "unittest",
            "sqlite3",
        }

        imports = []
        used_names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
                    if alias.name.split(".")[0] in stdlib_modules:
                        deps["stdlib_imports"].append(alias.name)
                    else:
                        deps["third_party_imports"].append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    if node.module.split(".")[0] in stdlib_modules:
                        deps["stdlib_imports"].append(node.module)
                    elif node.level > 0:
                        deps["local_imports"].append(node.module or ".")
                    else:
                        deps["third_party_imports"].append(node.module)

            elif isinstance(node, ast.Name):
                used_names.add(node.id)

        return deps

    def _analyze_python_quality(self, code: str, tree: ast.AST) -> Dict[str, Any]:
        """Analyze Python code quality."""
        lines = code.splitlines()
        quality = {
            "total_lines": len(lines),
            "blank_lines": sum(1 for line in lines if not line.strip()),
            "comment_lines": sum(1 for line in lines if line.strip().startswith("#")),
            "docstring_functions": 0,
            "total_functions": 0,
            "long_functions": [],
            "code_issues": [],
        }

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                quality["total_functions"] += 1

                # Check for docstring
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    quality["docstring_functions"] += 1

                # Check function length
                func_lines = getattr(node, "end_lineno", node.lineno) - node.lineno + 1
                if func_lines > 50:
                    quality["long_functions"].append(
                        {
                            "name": node.name,
                            "lines": func_lines,
                            "start_line": node.lineno,
                        }
                    )

        # Calculate documentation ratio
        if quality["total_functions"] > 0:
            quality["documentation_ratio"] = (
                quality["docstring_functions"] / quality["total_functions"]
            )
        else:
            quality["documentation_ratio"] = 0

        return quality

    def _generate_python_suggestions(
        self, code: str, tree: ast.AST, analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement suggestions for Python code."""
        suggestions = []

        # Complexity suggestions
        if "complexity" in analysis:
            if analysis["complexity"]["cyclomatic_complexity"] > 10:
                suggestions.append(
                    "Consider breaking down complex logic to reduce cyclomatic complexity"
                )

            if analysis["complexity"]["nesting_depth"] > 4:
                suggestions.append(
                    "Consider reducing nesting depth by using early returns or extracting functions"
                )

        # Quality suggestions
        if "quality" in analysis:
            if analysis["quality"]["documentation_ratio"] < 0.5:
                suggestions.append(
                    "Add docstrings to functions to improve code documentation"
                )

            if analysis["quality"]["long_functions"]:
                suggestions.append(
                    "Consider breaking down long functions into smaller, more focused functions"
                )

        # Structure suggestions
        if "structure" in analysis:
            if (
                len(analysis["structure"]["classes"]) == 0
                and len(analysis["structure"]["functions"]) > 5
            ):
                suggestions.append(
                    "Consider organizing functions into classes for better code structure"
                )

        return suggestions

    async def _analyze_js_code(
        self, code: str, analysis_type: str, include_suggestions: bool
    ) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript code (basic analysis)."""
        analysis = {
            "language": "javascript",
            "syntax_valid": True,  # We can't easily parse JS without a proper parser
        }

        lines = code.splitlines()
        analysis["lines_of_code"] = len(lines)
        analysis["blank_lines"] = sum(1 for line in lines if not line.strip())
        analysis["comment_lines"] = sum(
            1 for line in lines if line.strip().startswith("//")
        )

        # Basic pattern matching for structure
        functions = re.findall(
            r"(?:function\s+(\w+)|(\w+)\s*[:=]\s*(?:function|\(.*?\)\s*=>))", code
        )
        classes = re.findall(r"class\s+(\w+)", code)
        imports = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', code)

        analysis["structure"] = {
            "functions": [f[0] or f[1] for f in functions],
            "classes": classes,
            "imports": imports,
        }

        if include_suggestions:
            analysis["suggestions"] = self._generate_js_suggestions(code, analysis)

        return analysis

    def _generate_js_suggestions(
        self, code: str, analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement suggestions for JavaScript code."""
        suggestions = []

        if "var " in code:
            suggestions.append(
                "Consider using 'let' or 'const' instead of 'var' for better scoping"
            )

        if "==" in code and "===" not in code:
            suggestions.append(
                "Consider using strict equality (===) instead of loose equality (==)"
            )

        if analysis.get("lines_of_code", 0) > 200:
            suggestions.append("Consider breaking large files into smaller modules")

        return suggestions

    async def _analyze_generic_code(
        self, code: str, analysis_type: str, include_suggestions: bool
    ) -> Dict[str, Any]:
        """Analyze code in generic way (language-agnostic)."""
        lines = code.splitlines()

        analysis = {
            "language": "generic",
            "lines_of_code": len(lines),
            "blank_lines": sum(1 for line in lines if not line.strip()),
            "avg_line_length": (
                sum(len(line) for line in lines) / len(lines) if lines else 0
            ),
            "max_line_length": max(len(line) for line in lines) if lines else 0,
            "character_count": len(code),
        }

        # Simple pattern detection
        patterns = {
            "brackets": code.count("{") + code.count("[") + code.count("("),
            "loops": len(re.findall(r"\b(for|while|do)\b", code, re.IGNORECASE)),
            "conditionals": len(
                re.findall(r"\b(if|else|switch|case)\b", code, re.IGNORECASE)
            ),
            "functions": len(
                re.findall(r"\b(function|def|fn|func)\b", code, re.IGNORECASE)
            ),
        }

        analysis["patterns"] = patterns

        if include_suggestions:
            suggestions = []
            if analysis["max_line_length"] > 100:
                suggestions.append(
                    "Consider breaking long lines for better readability"
                )
            if analysis["avg_line_length"] > 50:
                suggestions.append("Consider using more concise expressions")
            analysis["suggestions"] = suggestions

        return analysis
