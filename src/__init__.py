"""Liquid Hive Core Library.

This package contains the core functionality for the Liquid Hive platform.
"""

from .version import VERSION, get_version, get_version_info, get_build_info

__version__ = VERSION
__all__ = ["VERSION", "get_version", "get_version_info", "get_build_info"]