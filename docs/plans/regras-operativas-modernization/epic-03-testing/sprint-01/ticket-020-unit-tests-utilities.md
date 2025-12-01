# [TICKET-020] Unit tests for utilities

> **Epic**: [Epic 03: Testing Infrastructure](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: TICKET-018 (pytest fixtures), TICKET-001 (exceptions), TICKET-003 (zip_utils), TICKET-004 (temp_manager)  
> **Blocks**: None

## Context

### Background

Utility modules (exceptions, zip_utils, temp_manager, settings) need comprehensive unit tests to ensure reliability. These are foundational components used throughout the application.

### Files to Read Before Starting

- `app/internal/exceptions.py` - Custom exceptions
- `app/utils/zip_utils.py` - Zip file operations
- `app/utils/temp_manager.py` - Temporary directory management
- `app/internal/settings.py` - Configuration settings
- `tests/conftest.py` - Available fixtures

## Specification

### Files to Create

```
tests/unit/
├── test_exceptions.py
├── test_zip_utils.py
├── test_temp_manager.py
└── test_settings.py
```

### test_exceptions.py

```python
"""Unit tests for custom exceptions."""

import pytest
from app.internal.exceptions import (
    RegrasOperativasError,
    ArtifactNotFoundError,
    S3DownloadError,
    S3UploadError,
    ZipExtractionError,
    ZipCreationError,
    ParseError,
    RuleApplicationError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test exception inheritance."""
    
    def test_all_exceptions_inherit_from_base(self):
        """All custom exceptions should inherit from RegrasOperativasError."""
        exceptions = [
            ArtifactNotFoundError,
            S3DownloadError,
            S3UploadError,
            ZipExtractionError,
            ZipCreationError,
            ParseError,
            RuleApplicationError,
            ValidationError,
        ]
        for exc_class in exceptions:
            assert issubclass(exc_class, RegrasOperativasError)
    
    def test_base_exception_is_exception(self):
        """Base exception should inherit from Exception."""
        assert issubclass(RegrasOperativasError, Exception)


class TestArtifactNotFoundError:
    """Test ArtifactNotFoundError."""
    
    def test_create_with_bucket_and_key(self):
        """Test exception creation with bucket and key."""
        exc = ArtifactNotFoundError(bucket="my-bucket", key="path/to/file.zip")
        assert "my-bucket" in str(exc)
        assert "path/to/file.zip" in str(exc)
        assert exc.bucket == "my-bucket"
        assert exc.key == "path/to/file.zip"
    
    def test_can_be_raised_and_caught(self):
        """Test exception can be raised and caught."""
        with pytest.raises(ArtifactNotFoundError) as exc_info:
            raise ArtifactNotFoundError(bucket="bucket", key="key")
        assert exc_info.value.bucket == "bucket"


class TestS3Errors:
    """Test S3 error exceptions."""
    
    def test_s3_download_error_with_message(self):
        """Test S3DownloadError captures message and details."""
        exc = S3DownloadError(
            message="Download failed",
            bucket="bucket",
            key="key",
            original_error=ValueError("original")
        )
        assert "Download failed" in str(exc)
        assert exc.bucket == "bucket"
    
    def test_s3_upload_error_with_message(self):
        """Test S3UploadError captures message and details."""
        exc = S3UploadError(
            message="Upload failed",
            bucket="bucket",
            key="key"
        )
        assert "Upload failed" in str(exc)


class TestZipErrors:
    """Test zip operation errors."""
    
    def test_zip_extraction_error(self):
        """Test ZipExtractionError."""
        exc = ZipExtractionError(
            message="Failed to extract",
            zip_path="/path/to/file.zip"
        )
        assert "Failed to extract" in str(exc)
        assert exc.zip_path == "/path/to/file.zip"
    
    def test_zip_creation_error(self):
        """Test ZipCreationError."""
        exc = ZipCreationError(
            message="Failed to create zip",
            output_path="/path/to/output.zip"
        )
        assert "Failed to create zip" in str(exc)


class TestParseError:
    """Test ParseError for file parsing failures."""
    
    def test_parse_error_with_file_info(self):
        """Test ParseError captures file information."""
        exc = ParseError(
            message="Invalid format",
            file_path="/path/to/file.dat",
            program="NEWAVE"
        )
        assert "Invalid format" in str(exc)
        assert exc.file_path == "/path/to/file.dat"
        assert exc.program == "NEWAVE"


class TestRuleApplicationError:
    """Test RuleApplicationError."""
    
    def test_rule_application_error(self):
        """Test RuleApplicationError captures rule info."""
        exc = RuleApplicationError(
            message="Failed to apply rule",
            rule_id="rule_123",
            reservoir_code=156
        )
        assert "Failed to apply rule" in str(exc)
        assert exc.rule_id == "rule_123"
        assert exc.reservoir_code == 156
```

### test_zip_utils.py

```python
"""Unit tests for zip utilities."""

import pytest
import zipfile
from pathlib import Path

from app.utils.zip_utils import extract_zip, create_zip, validate_zip


class TestExtractZip:
    """Test zip extraction functionality."""
    
    def test_extract_zip_success(self, temp_directory):
        """Test successful zip extraction."""
        # Create a test zip
        zip_path = temp_directory / "test.zip"
        extract_to = temp_directory / "extracted"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("subdir/file2.txt", "content2")
        
        extract_zip(zip_path, extract_to)
        
        assert (extract_to / "file1.txt").exists()
        assert (extract_to / "file1.txt").read_text() == "content1"
        assert (extract_to / "subdir" / "file2.txt").exists()
    
    def test_extract_zip_creates_output_dir(self, temp_directory):
        """Test extraction creates output directory if not exists."""
        zip_path = temp_directory / "test.zip"
        extract_to = temp_directory / "new" / "nested" / "dir"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("file.txt", "content")
        
        extract_zip(zip_path, extract_to)
        
        assert extract_to.exists()
        assert (extract_to / "file.txt").exists()
    
    def test_extract_zip_invalid_file_raises_error(self, temp_directory):
        """Test extraction of invalid zip raises ZipExtractionError."""
        from app.internal.exceptions import ZipExtractionError
        
        invalid_zip = temp_directory / "invalid.zip"
        invalid_zip.write_text("not a zip file")
        
        with pytest.raises(ZipExtractionError):
            extract_zip(invalid_zip, temp_directory / "output")
    
    def test_extract_zip_nonexistent_file_raises_error(self, temp_directory):
        """Test extraction of non-existent file raises error."""
        from app.internal.exceptions import ZipExtractionError
        
        with pytest.raises((ZipExtractionError, FileNotFoundError)):
            extract_zip(
                temp_directory / "nonexistent.zip",
                temp_directory / "output"
            )


class TestCreateZip:
    """Test zip creation functionality."""
    
    def test_create_zip_from_directory(self, temp_directory):
        """Test creating zip from directory."""
        # Setup source directory
        source_dir = temp_directory / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "subdir").mkdir()
        (source_dir / "subdir" / "file2.txt").write_text("content2")
        
        output_zip = temp_directory / "output.zip"
        
        create_zip(source_dir, output_zip)
        
        assert output_zip.exists()
        
        # Verify contents
        with zipfile.ZipFile(output_zip, 'r') as zf:
            names = zf.namelist()
            assert "file1.txt" in names
            assert "subdir/file2.txt" in names
    
    def test_create_zip_with_compression(self, temp_directory):
        """Test zip is compressed."""
        source_dir = temp_directory / "source"
        source_dir.mkdir()
        # Create a compressible file
        (source_dir / "large.txt").write_text("A" * 10000)
        
        output_zip = temp_directory / "output.zip"
        create_zip(source_dir, output_zip, compression_level=9)
        
        assert output_zip.exists()
        # Compressed size should be smaller than uncompressed
        assert output_zip.stat().st_size < 10000
    
    def test_create_zip_empty_directory(self, temp_directory):
        """Test creating zip from empty directory."""
        source_dir = temp_directory / "empty"
        source_dir.mkdir()
        output_zip = temp_directory / "empty.zip"
        
        create_zip(source_dir, output_zip)
        
        assert output_zip.exists()


class TestValidateZip:
    """Test zip validation functionality."""
    
    def test_validate_valid_zip(self, temp_directory):
        """Test validation of valid zip returns True."""
        zip_path = temp_directory / "valid.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("file.txt", "content")
        
        assert validate_zip(zip_path) is True
    
    def test_validate_invalid_zip(self, temp_directory):
        """Test validation of invalid zip returns False."""
        invalid_path = temp_directory / "invalid.zip"
        invalid_path.write_text("not a zip")
        
        assert validate_zip(invalid_path) is False
    
    def test_validate_nonexistent_zip(self, temp_directory):
        """Test validation of non-existent file returns False."""
        assert validate_zip(temp_directory / "nonexistent.zip") is False
```

### test_temp_manager.py

```python
"""Unit tests for temporary directory manager."""

import pytest
import time
from pathlib import Path

from app.utils.temp_manager import TempDirectoryManager


class TestTempDirectoryManager:
    """Test TempDirectoryManager functionality."""
    
    def test_create_temp_directory(self, temp_directory):
        """Test creating a temporary directory."""
        manager = TempDirectoryManager(base_dir=temp_directory)
        
        temp_dir = manager.create("test_operation")
        
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        assert "test_operation" in str(temp_dir)
    
    def test_create_multiple_directories(self, temp_directory):
        """Test creating multiple unique directories."""
        manager = TempDirectoryManager(base_dir=temp_directory)
        
        dir1 = manager.create("operation")
        dir2 = manager.create("operation")
        
        assert dir1 != dir2
        assert dir1.exists()
        assert dir2.exists()
    
    def test_cleanup_specific_directory(self, temp_directory):
        """Test cleaning up a specific directory."""
        manager = TempDirectoryManager(base_dir=temp_directory)
        temp_dir = manager.create("to_cleanup")
        
        # Create some files
        (temp_dir / "file.txt").write_text("content")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "nested.txt").write_text("nested")
        
        manager.cleanup(temp_dir)
        
        assert not temp_dir.exists()
    
    def test_cleanup_nonexistent_does_not_raise(self, temp_directory):
        """Test cleanup of non-existent directory doesn't raise."""
        manager = TempDirectoryManager(base_dir=temp_directory)
        
        # Should not raise
        manager.cleanup(temp_directory / "nonexistent")
    
    def test_cleanup_all(self, temp_directory):
        """Test cleaning up all managed directories."""
        manager = TempDirectoryManager(base_dir=temp_directory)
        
        dir1 = manager.create("op1")
        dir2 = manager.create("op2")
        (dir1 / "file.txt").write_text("content")
        
        manager.cleanup_all()
        
        assert not dir1.exists()
        assert not dir2.exists()
    
    def test_context_manager_cleanup(self, temp_directory):
        """Test context manager auto-cleanup."""
        manager = TempDirectoryManager(base_dir=temp_directory)
        
        with manager.temp_directory("context_test") as temp_dir:
            assert temp_dir.exists()
            (temp_dir / "file.txt").write_text("content")
            saved_path = temp_dir
        
        assert not saved_path.exists()
    
    def test_cleanup_old_directories(self, temp_directory):
        """Test cleanup of old directories by age."""
        manager = TempDirectoryManager(base_dir=temp_directory)
        
        # Create an "old" directory
        old_dir = manager.create("old_operation")
        (old_dir / "marker.txt").write_text("old")
        
        # Cleanup with 0 max age (everything is "old")
        manager.cleanup_old(max_age_seconds=0)
        
        assert not old_dir.exists()
    
    def test_list_managed_directories(self, temp_directory):
        """Test listing managed directories."""
        manager = TempDirectoryManager(base_dir=temp_directory)
        
        dir1 = manager.create("op1")
        dir2 = manager.create("op2")
        
        managed = manager.list_managed()
        
        assert dir1 in managed
        assert dir2 in managed


class TestTempDirectoryManagerEdgeCases:
    """Test edge cases for TempDirectoryManager."""
    
    def test_base_dir_created_if_not_exists(self, temp_directory):
        """Test base directory is created if it doesn't exist."""
        base = temp_directory / "new" / "base" / "dir"
        manager = TempDirectoryManager(base_dir=base)
        
        temp_dir = manager.create("test")
        
        assert base.exists()
        assert temp_dir.exists()
    
    def test_unique_names_with_timestamp(self, temp_directory):
        """Test directory names include timestamp for uniqueness."""
        manager = TempDirectoryManager(base_dir=temp_directory)
        
        dir1 = manager.create("same_prefix")
        dir2 = manager.create("same_prefix")
        
        # Names should be different due to timestamp/uuid
        assert dir1.name != dir2.name
```

### test_settings.py

```python
"""Unit tests for settings module."""

import pytest
import os


class TestSettings:
    """Test Settings configuration."""
    
    def test_default_values(self, monkeypatch):
        """Test default setting values."""
        # Clear environment
        for key in ["AWS_REGION", "S3_ENDPOINT_URL", "LOG_LEVEL"]:
            monkeypatch.delenv(key, raising=False)
        
        # Force reimport to get fresh settings
        from importlib import reload
        from app.internal import settings
        reload(settings)
        
        assert settings.settings.aws_region in ["us-east-1", None, ""]
        assert settings.settings.log_level in ["INFO", "DEBUG", "WARNING"]
    
    def test_environment_override(self, monkeypatch):
        """Test environment variables override defaults."""
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("PORT", "9000")
        
        from importlib import reload
        from app.internal import settings
        reload(settings)
        
        assert settings.settings.aws_region == "eu-west-1"
        assert settings.settings.log_level == "DEBUG"
        assert settings.settings.port == 9000
    
    def test_s3_bucket_defaults(self, monkeypatch):
        """Test S3 bucket configuration."""
        monkeypatch.setenv("DEFAULT_DECOMP_BUCKET", "custom-decomp")
        monkeypatch.setenv("DEFAULT_NEWAVE_BUCKET", "custom-newave")
        
        from importlib import reload
        from app.internal import settings
        reload(settings)
        
        assert settings.settings.default_decomp_bucket == "custom-decomp"
        assert settings.settings.default_newave_bucket == "custom-newave"
    
    def test_temp_dir_configuration(self, monkeypatch):
        """Test temporary directory configuration."""
        monkeypatch.setenv("TEMP_DIR", "/custom/temp")
        
        from importlib import reload
        from app.internal import settings
        reload(settings)
        
        assert settings.settings.temp_dir == "/custom/temp"


class TestSettingsValidation:
    """Test settings validation."""
    
    def test_port_must_be_integer(self, monkeypatch):
        """Test port validation."""
        monkeypatch.setenv("PORT", "8000")
        
        from importlib import reload
        from app.internal import settings
        reload(settings)
        
        assert isinstance(settings.settings.port, int)
```

## Acceptance Criteria

- [ ] All test files created
- [ ] All tests pass with `pytest tests/unit/test_*.py -v`
- [ ] Coverage for utilities ≥ 80%
- [ ] Tests are independent
- [ ] Edge cases covered

## Implementation Guide

### Step 1: Create Test Files

```bash
touch tests/unit/test_exceptions.py
touch tests/unit/test_zip_utils.py
touch tests/unit/test_temp_manager.py
touch tests/unit/test_settings.py
```

### Step 2: Implement Tests

Follow the test implementations above, adapting to actual module interfaces.

### Step 3: Verify Coverage

```bash
uv run pytest tests/unit/ -v --cov=app/internal --cov=app/utils --cov-report=term-missing
```

## Definition of Done

- [ ] All 4 test files created
- [ ] All tests pass
- [ ] Coverage ≥ 80% for tested modules
- [ ] No flaky tests
- [ ] Code reviewed

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Standard utility testing, clear interfaces
