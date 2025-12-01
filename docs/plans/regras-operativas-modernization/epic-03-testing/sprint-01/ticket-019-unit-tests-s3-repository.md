# [TICKET-019] Unit tests for S3Repository

> **Epic**: [Epic 03: Testing Infrastructure](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: TICKET-018 (pytest fixtures), TICKET-002 (S3Repository)  
> **Blocks**: None

## Context

### Background

S3Repository is the core adapter for all S3 operations. Comprehensive unit tests ensure the repository handles success cases, error cases, and edge cases correctly.

### Files to Read Before Starting

- `app/adapters/s3_repository.py` - Implementation to test
- `tests/conftest.py` - Available fixtures
- `app/internal/exceptions.py` - Exception classes to verify

## Specification

### File to Create

`tests/unit/test_s3_repository.py`

### Test Cases

```python
"""Unit tests for S3Repository."""

import io
import pytest
from pathlib import Path
from botocore.exceptions import ClientError

from app.adapters.s3_repository import S3Repository, reset_s3_repository
from app.internal.exceptions import (
    ArtifactNotFoundError,
    S3DownloadError,
    S3UploadError,
)


class TestS3RepositorySingleton:
    """Test singleton pattern behavior."""
    
    def test_get_instance_returns_same_instance(self, s3_client, aws_credentials):
        """Verify singleton returns same instance."""
        reset_s3_repository()
        repo1 = S3Repository.get_instance()
        repo2 = S3Repository.get_instance()
        assert repo1 is repo2
        reset_s3_repository()
    
    def test_reset_clears_singleton(self, s3_client, aws_credentials):
        """Verify reset creates new instance."""
        reset_s3_repository()
        repo1 = S3Repository.get_instance()
        reset_s3_repository()
        repo2 = S3Repository.get_instance()
        assert repo1 is not repo2
        reset_s3_repository()


class TestS3RepositoryDownload:
    """Test download operations."""
    
    def test_download_object_success(self, s3_repo, s3_client, temp_directory):
        """Test successful object download."""
        # Arrange
        bucket = "test-decomp-bucket"
        key = "test/file.txt"
        content = b"test content"
        s3_client.put_object(Bucket=bucket, Key=key, Body=content)
        local_path = temp_directory / "downloaded.txt"
        
        # Act
        s3_repo.download_object(bucket, key, local_path)
        
        # Assert
        assert local_path.exists()
        assert local_path.read_bytes() == content
    
    def test_download_object_creates_parent_dirs(self, s3_repo, s3_client, temp_directory):
        """Test download creates parent directories."""
        bucket = "test-decomp-bucket"
        key = "test/file.txt"
        s3_client.put_object(Bucket=bucket, Key=key, Body=b"content")
        local_path = temp_directory / "nested" / "dir" / "file.txt"
        
        s3_repo.download_object(bucket, key, local_path)
        
        assert local_path.exists()
    
    def test_download_object_not_found_raises_error(self, s3_repo, temp_directory):
        """Test download of non-existent object raises error."""
        bucket = "test-decomp-bucket"
        key = "nonexistent/file.txt"
        local_path = temp_directory / "file.txt"
        
        with pytest.raises(ArtifactNotFoundError) as exc_info:
            s3_repo.download_object(bucket, key, local_path)
        
        assert bucket in str(exc_info.value)
        assert key in str(exc_info.value)
    
    def test_download_bytes_success(self, s3_repo, s3_client):
        """Test downloading object as bytes."""
        bucket = "test-decomp-bucket"
        key = "test/data.bin"
        content = b"\x00\x01\x02\x03"
        s3_client.put_object(Bucket=bucket, Key=key, Body=content)
        
        result = s3_repo.download_bytes(bucket, key)
        
        assert result == content
    
    def test_download_bytes_not_found_raises_error(self, s3_repo):
        """Test download bytes of non-existent object."""
        with pytest.raises(ArtifactNotFoundError):
            s3_repo.download_bytes("test-decomp-bucket", "nonexistent.txt")


class TestS3RepositoryUpload:
    """Test upload operations."""
    
    def test_upload_object_from_file(self, s3_repo, s3_client, temp_directory):
        """Test uploading a local file."""
        bucket = "test-decomp-bucket"
        key = "uploaded/file.txt"
        content = b"upload test content"
        local_file = temp_directory / "to_upload.txt"
        local_file.write_bytes(content)
        
        s3_repo.upload_object(bucket, key, local_file)
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        assert response["Body"].read() == content
    
    def test_upload_bytes(self, s3_repo, s3_client):
        """Test uploading bytes directly."""
        bucket = "test-decomp-bucket"
        key = "uploaded/bytes.bin"
        content = b"bytes content"
        
        s3_repo.upload_bytes(bucket, key, content)
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        assert response["Body"].read() == content
    
    def test_upload_fileobj(self, s3_repo, s3_client):
        """Test uploading file-like object."""
        bucket = "test-decomp-bucket"
        key = "uploaded/fileobj.txt"
        content = b"fileobj content"
        fileobj = io.BytesIO(content)
        
        s3_repo.upload_fileobj(bucket, key, fileobj)
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        assert response["Body"].read() == content


class TestS3RepositoryList:
    """Test list operations."""
    
    def test_list_objects_returns_keys(self, s3_repo, s3_client):
        """Test listing objects in a prefix."""
        bucket = "test-decomp-bucket"
        s3_client.put_object(Bucket=bucket, Key="prefix/file1.txt", Body=b"1")
        s3_client.put_object(Bucket=bucket, Key="prefix/file2.txt", Body=b"2")
        s3_client.put_object(Bucket=bucket, Key="other/file3.txt", Body=b"3")
        
        result = s3_repo.list_objects(bucket, "prefix/")
        
        assert len(result) == 2
        assert "prefix/file1.txt" in result
        assert "prefix/file2.txt" in result
        assert "other/file3.txt" not in result
    
    def test_list_objects_empty_prefix(self, s3_repo, s3_client):
        """Test listing with empty prefix returns all."""
        bucket = "test-decomp-bucket"
        s3_client.put_object(Bucket=bucket, Key="file1.txt", Body=b"1")
        s3_client.put_object(Bucket=bucket, Key="dir/file2.txt", Body=b"2")
        
        result = s3_repo.list_objects(bucket, "")
        
        assert len(result) >= 2
    
    def test_list_objects_no_matches(self, s3_repo, s3_client):
        """Test listing returns empty for no matches."""
        bucket = "test-decomp-bucket"
        s3_client.put_object(Bucket=bucket, Key="exists.txt", Body=b"1")
        
        result = s3_repo.list_objects(bucket, "nonexistent/")
        
        assert result == []


class TestS3RepositoryExists:
    """Test existence check operations."""
    
    def test_object_exists_returns_true(self, s3_repo, s3_client):
        """Test exists returns True for existing object."""
        bucket = "test-decomp-bucket"
        key = "existing.txt"
        s3_client.put_object(Bucket=bucket, Key=key, Body=b"content")
        
        assert s3_repo.object_exists(bucket, key) is True
    
    def test_object_exists_returns_false(self, s3_repo):
        """Test exists returns False for non-existing object."""
        assert s3_repo.object_exists("test-decomp-bucket", "nonexistent.txt") is False


class TestS3RepositoryDelete:
    """Test delete operations."""
    
    def test_delete_object_success(self, s3_repo, s3_client):
        """Test deleting existing object."""
        bucket = "test-decomp-bucket"
        key = "to_delete.txt"
        s3_client.put_object(Bucket=bucket, Key=key, Body=b"content")
        
        s3_repo.delete_object(bucket, key)
        
        assert s3_repo.object_exists(bucket, key) is False
    
    def test_delete_nonexistent_does_not_raise(self, s3_repo):
        """Test deleting non-existent object doesn't raise."""
        # S3 delete is idempotent
        s3_repo.delete_object("test-decomp-bucket", "nonexistent.txt")


class TestS3RepositoryArtifactPaths:
    """Test artifact path helper methods."""
    
    def test_get_input_artifact_path(self, s3_repo):
        """Test input artifact path generation."""
        path = s3_repo.get_input_artifact_path("hash123")
        assert path == "artifacts/hash123/entradas/deck_processado.zip"
    
    def test_get_output_artifact_path(self, s3_repo):
        """Test output artifact path generation."""
        path = s3_repo.get_output_artifact_path("hash123", "ingest")
        assert path == "ingest/hash123_regras.zip"
    
    def test_get_relato_path_decomp(self, s3_repo):
        """Test relato path for DECOMP."""
        path = s3_repo.get_relato_path("hash123", "DECOMP", revision=0)
        assert "saidas" in path
        assert "relato" in path.lower()
```

## Acceptance Criteria

- [ ] All test cases pass with `pytest tests/unit/test_s3_repository.py -v`
- [ ] Test coverage for s3_repository.py ≥ 80%
- [ ] Tests use moto fixtures (no real AWS calls)
- [ ] Error cases properly verified with pytest.raises
- [ ] Tests are independent (can run in any order)

## Implementation Guide

### Step 1: Create Test File

```bash
touch tests/unit/test_s3_repository.py
```

### Step 2: Implement Tests by Category

1. Start with singleton tests
2. Add download tests
3. Add upload tests
4. Add list/exists/delete tests
5. Add helper method tests

### Step 3: Run and Verify Coverage

```bash
uv run pytest tests/unit/test_s3_repository.py -v --cov=app/adapters/s3_repository --cov-report=term-missing
```

## Testing Requirements

### Coverage Target

- Minimum 80% line coverage for `app/adapters/s3_repository.py`
- All public methods tested
- Error paths tested

## Definition of Done

- [ ] All test cases implemented
- [ ] All tests pass
- [ ] Coverage ≥ 80%
- [ ] No flaky tests
- [ ] Code reviewed

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Standard moto-based S3 testing, well-documented pattern
