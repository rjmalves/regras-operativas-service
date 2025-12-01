"""Unit tests for temp_manager utilities."""

import os
import time
from pathlib import Path

import pytest

from app.utils.temp_manager import (
    async_temp_directory,
    cleanup_directory,
    cleanup_old_temp_dirs,
    temp_directory,
)


class TestTempDirectory:
    """Tests for temp_directory context manager."""

    def test_creates_temp_directory(self, tmp_path):
        """Test that temp directory is created."""
        with temp_directory(base_dir=str(tmp_path)) as temp_dir:
            assert temp_dir.exists()
            assert temp_dir.is_dir()
            assert temp_dir.parent == tmp_path

    def test_cleans_up_on_exit(self, tmp_path):
        """Test that temp directory is cleaned up on exit."""
        with temp_directory(base_dir=str(tmp_path)) as temp_dir:
            temp_path = temp_dir
            assert temp_path.exists()

        assert not temp_path.exists()

    def test_cleans_up_on_exception(self, tmp_path):
        """Test that temp directory is cleaned up on exception."""
        temp_path = None
        try:
            with temp_directory(base_dir=str(tmp_path)) as temp_dir:
                temp_path = temp_dir
                raise ValueError("test error")
        except ValueError:
            pass

        assert not temp_path.exists()

    def test_creates_files_in_temp_dir(self, tmp_path):
        """Test that files can be created in temp directory."""
        with temp_directory(base_dir=str(tmp_path)) as temp_dir:
            test_file = temp_dir / "test.txt"
            test_file.write_text("content")
            assert test_file.exists()

    def test_uses_prefix(self, tmp_path):
        """Test that prefix is used in directory name."""
        with temp_directory(base_dir=str(tmp_path), prefix="custom_") as temp_dir:
            assert temp_dir.name.startswith("custom_")


class TestAsyncTempDirectory:
    """Tests for async_temp_directory context manager."""

    @pytest.mark.asyncio
    async def test_creates_temp_directory(self, tmp_path):
        """Test that temp directory is created."""
        async with async_temp_directory(base_dir=str(tmp_path)) as temp_dir:
            assert temp_dir.exists()
            assert temp_dir.is_dir()

    @pytest.mark.asyncio
    async def test_cleans_up_on_exit(self, tmp_path):
        """Test that temp directory is cleaned up on exit."""
        async with async_temp_directory(base_dir=str(tmp_path)) as temp_dir:
            temp_path = temp_dir
            assert temp_path.exists()

        assert not temp_path.exists()

    @pytest.mark.asyncio
    async def test_cleans_up_on_exception(self, tmp_path):
        """Test that temp directory is cleaned up on exception."""
        temp_path = None
        try:
            async with async_temp_directory(base_dir=str(tmp_path)) as temp_dir:
                temp_path = temp_dir
                raise ValueError("test error")
        except ValueError:
            pass

        assert not temp_path.exists()


class TestCleanupDirectory:
    """Tests for cleanup_directory function."""

    def test_removes_empty_directory(self, tmp_path):
        """Test removing an empty directory."""
        dir_path = tmp_path / "empty"
        dir_path.mkdir()

        result = cleanup_directory(dir_path)

        assert result is True
        assert not dir_path.exists()

    def test_removes_directory_with_files(self, tmp_path):
        """Test removing a directory with files."""
        dir_path = tmp_path / "with_files"
        dir_path.mkdir()
        (dir_path / "file1.txt").write_text("content")
        (dir_path / "subdir").mkdir()
        (dir_path / "subdir" / "file2.txt").write_text("content")

        result = cleanup_directory(dir_path)

        assert result is True
        assert not dir_path.exists()

    def test_nonexistent_directory_returns_true(self, tmp_path):
        """Test that non-existent directory returns True."""
        dir_path = tmp_path / "nonexistent"

        result = cleanup_directory(dir_path)

        assert result is True


class TestCleanupOldTempDirs:
    """Tests for cleanup_old_temp_dirs function."""

    def test_removes_old_directories(self, tmp_path):
        """Test removing old directories."""
        # Create old directory
        old_dir = tmp_path / "regras_old"
        old_dir.mkdir()
        # Set mtime to 2 days ago
        old_time = time.time() - (48 * 3600)
        os.utime(old_dir, (old_time, old_time))

        removed = cleanup_old_temp_dirs(base_dir=str(tmp_path), max_age_hours=24)

        assert removed == 1
        assert not old_dir.exists()

    def test_keeps_recent_directories(self, tmp_path):
        """Test keeping recent directories."""
        # Create recent directory
        recent_dir = tmp_path / "regras_recent"
        recent_dir.mkdir()

        removed = cleanup_old_temp_dirs(base_dir=str(tmp_path), max_age_hours=24)

        assert removed == 0
        assert recent_dir.exists()

    def test_ignores_non_matching_directories(self, tmp_path):
        """Test ignoring directories that don't match prefix."""
        # Create old directory with different prefix
        other_dir = tmp_path / "other_old"
        other_dir.mkdir()
        old_time = time.time() - (48 * 3600)
        os.utime(other_dir, (old_time, old_time))

        removed = cleanup_old_temp_dirs(base_dir=str(tmp_path), max_age_hours=24)

        assert removed == 0
        assert other_dir.exists()

    def test_nonexistent_base_dir(self, tmp_path):
        """Test with non-existent base directory."""
        removed = cleanup_old_temp_dirs(base_dir=str(tmp_path / "nonexistent"))
        assert removed == 0
