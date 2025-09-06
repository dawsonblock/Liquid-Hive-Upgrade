from src.logging_config import get_logger
"""File Operations Tool for LIQUID-HIVE
===================================

A secure file operations tool that can read, write, and manage files
with proper security restrictions and approval requirements.
"""

import hashlib
import os
import pathlib
from typing import Any

import aiofiles

from .base_tool import BaseTool, ToolParameter, ToolParameterType, ToolResult


class FileOperationsTool(BaseTool):
    """Secure file operations tool with restricted access."""

    def __init__(self):
        # Define allowed directories for security
        # Use secure temporary directory instead of hardcoded /tmp
        import tempfile

        secure_temp_dir = tempfile.mkdtemp(prefix="liquid_hive_")

        self.allowed_directories = {
            "/app/data/ingest",
            "/app/data/output",
            "/app/data/temp",
            secure_temp_dir,
        }

        # Ensure allowed directories exist
        for directory in self.allowed_directories:
            pathlib.Path(directory).mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "file_operations"

    @property
    def description(self) -> str:
        return "Perform secure file operations including read, write, list, and info operations within allowed directories"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="operation",
                type=ToolParameterType.STRING,
                description="File operation to perform",
                required=True,
                choices=["read", "write", "list", "info", "exists", "delete"],
            ),
            ToolParameter(
                name="path",
                type=ToolParameterType.STRING,
                description="File or directory path (must be within allowed directories)",
                required=True,
            ),
            ToolParameter(
                name="content",
                type=ToolParameterType.STRING,
                description="Content to write (required for 'write' operation)",
                required=False,
            ),
            ToolParameter(
                name="encoding",
                type=ToolParameterType.STRING,
                description="File encoding",
                required=False,
                default="utf-8",
                choices=["utf-8", "ascii", "latin1"],
            ),
            ToolParameter(
                name="max_size_mb",
                type=ToolParameterType.INTEGER,
                description="Maximum file size in MB for read operations",
                required=False,
                default=10,
                min_value=1,
                max_value=100,
            ),
        ]

    @property
    def category(self) -> str:
        return "system"

    @property
    def requires_approval(self) -> bool:
        return True  # File system access requires approval

    @property
    def risk_level(self) -> str:
        return "medium"

    def _is_path_allowed(self, path: str) -> bool:
        """Check if the path is within allowed directories."""
        try:
            resolved_path = pathlib.Path(path).resolve()
            for allowed_dir in self.allowed_directories:
                allowed_path = pathlib.Path(allowed_dir).resolve()
                try:
                    resolved_path.relative_to(allowed_path)
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        """Execute file operation."""
        operation = parameters["operation"]
        path = parameters["path"]
        content = parameters.get("content")
        encoding = parameters.get("encoding", "utf-8")
        max_size_mb = parameters.get("max_size_mb", 10)

        # Security check
        if not self._is_path_allowed(path):
            return ToolResult(
                success=False,
                error=f"Path '{path}' is not within allowed directories: {list(self.allowed_directories)}",
            )

        try:
            if operation == "read":
                return await self._read_file(path, encoding, max_size_mb)
            elif operation == "write":
                if content is None:
                    return ToolResult(
                        success=False, error="Content is required for write operation"
                    )
                return await self._write_file(path, content, encoding)
            elif operation == "list":
                return await self._list_directory(path)
            elif operation == "info":
                return await self._file_info(path)
            elif operation == "exists":
                return await self._file_exists(path)
            elif operation == "delete":
                return await self._delete_file(path)
            else:
                return ToolResult(success=False, error=f"Unknown operation: {operation}")

        except PermissionError as e:
            return ToolResult(success=False, error=f"Permission denied: {e!s}")
        except FileNotFoundError as e:
            return ToolResult(success=False, error=f"File not found: {e!s}")
        except Exception as e:
            return ToolResult(success=False, error=f"File operation failed: {e!s}")

    async def _read_file(self, path: str, encoding: str, max_size_mb: int) -> ToolResult:
        """Read file content."""
        file_path = pathlib.Path(path)

        # Check file size
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > max_size_mb:
                return ToolResult(
                    success=False,
                    error=f"File size ({size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)",
                )

        async with aiofiles.open(path, encoding=encoding) as f:
            content = await f.read()

        # Calculate file hash for integrity
        file_hash = hashlib.sha256(content.encode()).hexdigest()

        return ToolResult(
            success=True,
            data=content,
            metadata={
                "path": path,
                "size_bytes": len(content.encode()),
                "encoding": encoding,
                "md5_hash": file_hash,
                "operation": "read",
            },
        )

    async def _write_file(self, path: str, content: str, encoding: str) -> ToolResult:
        """Write content to file."""
        async with aiofiles.open(path, mode="w", encoding=encoding) as f:
            await f.write(content)

        file_path = pathlib.Path(path)
        size_bytes = file_path.stat().st_size

        return ToolResult(
            success=True,
            data=f"File written successfully to {path}",
            metadata={
                "path": path,
                "size_bytes": size_bytes,
                "encoding": encoding,
                "operation": "write",
            },
        )

    async def _list_directory(self, path: str) -> ToolResult:
        """List directory contents."""
        dir_path = pathlib.Path(path)

        if not dir_path.exists():
            return ToolResult(success=False, error=f"Directory does not exist: {path}")

        if not dir_path.is_dir():
            return ToolResult(success=False, error=f"Path is not a directory: {path}")

        items = []
        for item in dir_path.iterdir():
            stat_info = item.stat()
            items.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size_bytes": stat_info.st_size if item.is_file() else None,
                    "modified": stat_info.st_mtime,
                    "permissions": oct(stat_info.st_mode)[-3:],
                }
            )

        # Sort by name
        items.sort(key=lambda x: x["name"])

        return ToolResult(
            success=True,
            data=items,
            metadata={"path": path, "count": len(items), "operation": "list"},
        )

    async def _file_info(self, path: str) -> ToolResult:
        """Get file information."""
        file_path = pathlib.Path(path)

        if not file_path.exists():
            return ToolResult(success=False, error=f"Path does not exist: {path}")

        stat_info = file_path.stat()
        info = {
            "path": str(file_path.resolve()),
            "name": file_path.name,
            "type": "directory" if file_path.is_dir() else "file",
            "size_bytes": stat_info.st_size,
            "created": stat_info.st_ctime,
            "modified": stat_info.st_mtime,
            "accessed": stat_info.st_atime,
            "permissions": oct(stat_info.st_mode)[-3:],
            "is_readable": os.access(path, os.R_OK),
            "is_writable": os.access(path, os.W_OK),
            "is_executable": os.access(path, os.X_OK),
        }

        # Add file hash if it's a file and small enough
        if file_path.is_file() and stat_info.st_size < 10 * 1024 * 1024:  # 10MB limit
            with open(path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                info["sha256_hash"] = file_hash

        return ToolResult(success=True, data=info, metadata={"operation": "info"})

    async def _file_exists(self, path: str) -> ToolResult:
        """Check if file exists."""
        exists = pathlib.Path(path).exists()

        return ToolResult(success=True, data=exists, metadata={"path": path, "operation": "exists"})

    async def _delete_file(self, path: str) -> ToolResult:
        """Delete file (with extra safety checks)."""
        file_path = pathlib.Path(path)

        if not file_path.exists():
            return ToolResult(success=False, error=f"Path does not exist: {path}")

        if file_path.is_dir():
            return ToolResult(success=False, error="Cannot delete directories with this tool")

        # Additional safety: don't delete system files
        if file_path.name.startswith("."):
            return ToolResult(success=False, error="Cannot delete hidden/system files")

        file_path.unlink()

        return ToolResult(
            success=True,
            data=f"File deleted: {path}",
            metadata={"path": path, "operation": "delete"},
        )
