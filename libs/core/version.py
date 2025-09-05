"""Version information for Liquid Hive."""

__version__ = "1.0.0"
__version_info__ = tuple(int(i) for i in __version__.split("."))

# Version metadata
VERSION = __version__
VERSION_INFO = __version_info__

# Build information
BUILD_DATE = "2024-01-01"
BUILD_COMMIT = "unknown"
BUILD_BRANCH = "main"

def get_version() -> str:
    """Get the current version string."""
    return VERSION

def get_version_info() -> tuple[int, ...]:
    """Get the version as a tuple of integers."""
    return VERSION_INFO

def get_build_info() -> dict[str, str]:
    """Get build information."""
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "build_commit": BUILD_COMMIT,
        "build_branch": BUILD_BRANCH,
    }