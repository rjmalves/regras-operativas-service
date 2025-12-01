"""Unit tests for zip utilities."""

import zipfile
from pathlib import Path

import pytest

from app.internal.exceptions import ZipExtractionError
from app.utils.zip_utils import create_zip, extract_zip, get_zip_file_list


class TestExtractZip:
    """Tests for extract_zip function."""

    def test_extract_valid_zip(self, tmp_path):
        """Test extracting a valid zip file."""
        # Create test zip
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("file2.txt", "content2")

        # Extract
        dest_dir = tmp_path / "extracted"
        dest_dir.mkdir()
        extract_zip(zip_path, dest_dir)

        # Verify
        assert (dest_dir / "file1.txt").read_text() == "content1"
        assert (dest_dir / "file2.txt").read_text() == "content2"

    def test_extract_nonexistent_zip(self, tmp_path):
        """Test extracting a non-existent zip file."""
        zip_path = tmp_path / "nonexistent.zip"
        dest_dir = tmp_path / "extracted"
        dest_dir.mkdir()

        with pytest.raises(ZipExtractionError) as exc_info:
            extract_zip(zip_path, dest_dir)

        assert "not found" in exc_info.value.message.lower()

    def test_extract_invalid_zip(self, tmp_path):
        """Test extracting an invalid zip file."""
        # Create invalid "zip" file
        zip_path = tmp_path / "invalid.zip"
        zip_path.write_bytes(b"not a zip file")

        dest_dir = tmp_path / "extracted"
        dest_dir.mkdir()

        with pytest.raises(ZipExtractionError) as exc_info:
            extract_zip(zip_path, dest_dir)

        assert "invalid" in exc_info.value.message.lower()


class TestCreateZip:
    """Tests for create_zip function."""

    def test_create_zip_success(self, tmp_path):
        """Test creating a zip file."""
        # Create source files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")

        # Create zip
        zip_path = tmp_path / "output.zip"
        create_zip(source_dir, zip_path)

        # Verify
        assert zip_path.exists()
        with zipfile.ZipFile(zip_path, "r") as zf:
            assert set(zf.namelist()) == {"file1.txt", "file2.txt"}
            assert zf.read("file1.txt") == b"content1"

    def test_create_zip_with_compression(self, tmp_path):
        """Test creating a zip with specified compression."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        # Write larger file to see compression effect
        (source_dir / "large.txt").write_text("A" * 10000)

        zip_path = tmp_path / "output.zip"
        create_zip(source_dir, zip_path, compression_level=9)

        assert zip_path.exists()
        # Compressed file should be smaller than original
        assert zip_path.stat().st_size < 10000

    def test_create_zip_nonexistent_source(self, tmp_path):
        """Test creating zip from non-existent source."""
        source_dir = tmp_path / "nonexistent"
        zip_path = tmp_path / "output.zip"

        with pytest.raises(ZipExtractionError) as exc_info:
            create_zip(source_dir, zip_path)

        assert "not found" in exc_info.value.message.lower()

    def test_create_zip_empty_source(self, tmp_path):
        """Test creating zip from empty source directory."""
        source_dir = tmp_path / "empty"
        source_dir.mkdir()
        zip_path = tmp_path / "output.zip"

        with pytest.raises(ZipExtractionError) as exc_info:
            create_zip(source_dir, zip_path)

        assert "empty" in exc_info.value.message.lower()


class TestGetZipFileList:
    """Tests for get_zip_file_list function."""

    def test_get_file_list(self, tmp_path):
        """Test getting file list from zip."""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("dir/file2.txt", "content2")
            zf.writestr("file3.dat", "content3")

        files = get_zip_file_list(zip_path)

        assert set(files) == {"file1.txt", "dir/file2.txt", "file3.dat"}

    def test_get_file_list_nonexistent(self, tmp_path):
        """Test getting file list from non-existent zip."""
        zip_path = tmp_path / "nonexistent.zip"

        with pytest.raises(ZipExtractionError):
            get_zip_file_list(zip_path)

    def test_get_file_list_invalid_zip(self, tmp_path):
        """Test getting file list from invalid zip."""
        zip_path = tmp_path / "invalid.zip"
        zip_path.write_bytes(b"not a zip")

        with pytest.raises(ZipExtractionError):
            get_zip_file_list(zip_path)
