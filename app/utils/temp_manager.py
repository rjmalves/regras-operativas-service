"""
Temporary directory lifecycle management.

This module provides context managers and utilities for creating and
cleaning up temporary directories used during rules processing.
"""

import shutil
import tempfile
import time
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

from app.utils.log import Log


@contextmanager
def temp_directory(
    base_dir: str = "/tmp/regras-operativas",
    prefix: str = "regras_",
) -> Generator[Path, None, None]:
    """
    Context manager for temporary directory lifecycle.

    Creates a unique temporary directory that is automatically cleaned up
    when the context exits, even if an exception occurs.

    Args:
        base_dir: Parent directory for temp directories
        prefix: Prefix for temp directory name

    Yields:
        Path to the temporary directory

    Example:
        with temp_directory() as temp_dir:
            # Use temp_dir for file operations
            (temp_dir / "file.txt").write_text("content")
        # Directory is automatically cleaned up
    """
    # Ensure base directory exists
    Path(base_dir).mkdir(parents=True, exist_ok=True)

    # Create unique temp directory
    temp_dir = Path(tempfile.mkdtemp(dir=base_dir, prefix=prefix))
    Log.log().info(f"Created temp directory: {temp_dir}")

    try:
        yield temp_dir
    finally:
        cleanup_directory(temp_dir)


@asynccontextmanager
async def async_temp_directory(
    base_dir: str = "/tmp/regras-operativas",
    prefix: str = "regras_",
) -> AsyncGenerator[Path, None]:
    """
    Async context manager for temporary directory lifecycle.

    Same as temp_directory but for use in async code.

    Args:
        base_dir: Parent directory for temp directories
        prefix: Prefix for temp directory name

    Yields:
        Path to the temporary directory
    """
    # Ensure base directory exists
    Path(base_dir).mkdir(parents=True, exist_ok=True)

    # Create unique temp directory
    temp_dir = Path(tempfile.mkdtemp(dir=base_dir, prefix=prefix))
    Log.log().info(f"Created temp directory: {temp_dir}")

    try:
        yield temp_dir
    finally:
        cleanup_directory(temp_dir)


def cleanup_directory(dir_path: Path) -> bool:
    """
    Remove a directory and all its contents.

    Args:
        dir_path: Directory to remove

    Returns:
        True if cleanup succeeded, False if it failed
    """
    if not dir_path.exists():
        Log.log().debug(f"Directory already removed: {dir_path}")
        return True

    try:
        shutil.rmtree(dir_path)
        Log.log().info(f"Cleaned up temp directory: {dir_path}")
        return True
    except Exception as e:
        Log.log().warning(f"Failed to cleanup {dir_path}: {e}")
        return False


def cleanup_old_temp_dirs(
    base_dir: str = "/tmp/regras-operativas",
    max_age_hours: int = 24,
) -> int:
    """
    Remove temp directories older than max_age_hours.

    Useful for cleaning up orphaned directories from crashed processes.

    Args:
        base_dir: Directory containing temp directories
        max_age_hours: Maximum age in hours before cleanup

    Returns:
        Number of directories removed
    """
    base_path = Path(base_dir)
    if not base_path.exists():
        return 0

    removed = 0
    max_age_seconds = max_age_hours * 3600
    now = time.time()

    for item in base_path.iterdir():
        if item.is_dir() and item.name.startswith("regras_"):
            age = now - item.stat().st_mtime
            if age > max_age_seconds and cleanup_directory(item):
                removed += 1

    if removed > 0:
        Log.log().info(f"Cleaned up {removed} old temp directories")

    return removed
