# TICKET-002: Implement S3Repository

> **Epic**: [Epic 01: S3 Integration Layer](../../00-epic-overview.md)  
> **Sprint**: [Sprint 01](./00-sprint-overview.md)  
> **Points**: 3  
> **Dependencies**: [TICKET-001](./ticket-001-create-exception-hierarchy.md)  
> **Blocks**: [TICKET-006](../sprint-02/ticket-006-create-s3-decomp-uow.md), [TICKET-007](../sprint-02/ticket-007-create-s3-newave-uow.md)

## Context

### Background

The service needs to download artifacts from S3 (deck_processado.zip, relato files) and upload processed results. This repository abstracts all S3 operations and provides async-compatible methods using ThreadPoolExecutor.

### Current State

The current codebase reads directly from the filesystem. This ticket creates the S3 abstraction layer.

## Specification

### File Location

- `app/adapters/s3_repository.py` (CREATE)

### Class Interface

```python
class AbstractS3Repository(ABC):
    """Abstract interface for S3 operations."""

    @abstractmethod
    async def download_file(self, bucket: str, key: str, local_path: str) -> None:
        """Download file from S3 to local path."""
        pass

    @abstractmethod
    async def upload_file(self, local_path: str, bucket: str, key: str) -> str:
        """Upload file to S3, return the key."""
        pass

    @abstractmethod
    async def download_bytes(self, bucket: str, key: str) -> bytes:
        """Download object as bytes."""
        pass

    @abstractmethod
    async def object_exists(self, bucket: str, key: str) -> bool:
        """Check if object exists."""
        pass

    @abstractmethod
    async def list_objects(self, bucket: str, prefix: str, max_keys: int = 1000) -> list[str]:
        """List objects with prefix."""
        pass
```

### Implementation Details

```python
class S3Repository(AbstractS3Repository):
    def __init__(
        self,
        region: str,
        endpoint_url: str | None = None,
        max_workers: int = 4,
    ):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
            max_pool_connections=max_workers,
        )
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            config=config,
        )
```

### Error Handling

- `404` / `NoSuchKey` → `ArtifactNotFoundError`
- Other `ClientError` → `S3OperationError`

### Singleton Pattern

```python
_s3_repository: S3Repository | None = None

def get_s3_repository() -> S3Repository:
    """Get or create singleton S3Repository."""
    global _s3_repository
    if _s3_repository is None:
        _s3_repository = S3Repository(
            region=Settings.aws_region,
            endpoint_url=Settings.s3_endpoint_url,
        )
    return _s3_repository

def reset_s3_repository() -> None:
    """Reset singleton (for testing)."""
    global _s3_repository
    if _s3_repository is not None:
        _s3_repository.close()
        _s3_repository = None
```

## Acceptance Criteria

- [ ] Given valid bucket and key, when `download_file()` is called, then file is downloaded to local path
- [ ] Given non-existent key, when `download_file()` is called, then `ArtifactNotFoundError` is raised
- [ ] Given valid local file, when `upload_file()` is called, then file is uploaded and key is returned
- [ ] Given network error, when any S3 operation fails, then `S3OperationError` is raised with details
- [ ] Given custom `endpoint_url`, when repository is created, then it connects to that endpoint (for LocalStack)
- [ ] `get_s3_repository()` returns same instance on repeated calls
- [ ] `reset_s3_repository()` closes executor and resets singleton

## Implementation Guide

### Suggested Approach

1. Create `app/adapters/s3_repository.py`
2. Copy implementation from flexibilizador-service (exact copy works)
3. Update imports to use local `exceptions.py`
4. Write unit tests with moto

### Reference Implementation

Copy from: `/home/rogerio/git/flexibilizador-service/app/adapters/s3_repository.py`

Changes needed:
- Update import: `from app.internal.exceptions import ...`
- No other changes required

### Key Files to Read

- `/home/rogerio/git/flexibilizador-service/app/adapters/s3_repository.py` - Reference implementation
- `app/internal/exceptions.py` - Exception classes (from TICKET-001)

### boto3 Configuration

```python
from botocore.config import Config

config = Config(
    retries={"max_attempts": 3, "mode": "adaptive"},
    connect_timeout=5,
    read_timeout=30,
    max_pool_connections=4,
)
```

### Pitfalls to Avoid

- ⚠️ Don't forget to close ThreadPoolExecutor in `close()` method
- ⚠️ Don't call async methods without `await`
- ⚠️ Remember 404 can be either "404" or "NoSuchKey" error code
- ⚠️ Use `run_in_executor` for all boto3 calls (they are synchronous)

## Testing Requirements

### Unit Tests

Create `tests/unit/test_s3_repository.py`:

```python
import pytest
from moto import mock_aws
import boto3
from app.adapters.s3_repository import S3Repository, reset_s3_repository
from app.internal.exceptions import ArtifactNotFoundError, S3OperationError

@pytest.fixture
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

@pytest.fixture
def s3_client(aws_credentials):
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-bucket")
        yield client

@pytest.fixture
def s3_repo(s3_client):
    repo = S3Repository(region="us-east-1")
    yield repo
    repo.close()

@pytest.mark.asyncio
async def test_download_file_success(s3_repo, s3_client, tmp_path):
    # Upload test file
    s3_client.put_object(Bucket="test-bucket", Key="test.txt", Body=b"content")
    
    # Download
    local_path = tmp_path / "downloaded.txt"
    await s3_repo.download_file("test-bucket", "test.txt", str(local_path))
    
    assert local_path.read_bytes() == b"content"

@pytest.mark.asyncio
async def test_download_file_not_found(s3_repo):
    with pytest.raises(ArtifactNotFoundError):
        await s3_repo.download_file("test-bucket", "nonexistent.txt", "/tmp/out.txt")

@pytest.mark.asyncio
async def test_upload_file_success(s3_repo, s3_client, tmp_path):
    local_file = tmp_path / "upload.txt"
    local_file.write_bytes(b"upload content")
    
    key = await s3_repo.upload_file(str(local_file), "test-bucket", "uploaded.txt")
    
    assert key == "uploaded.txt"
    response = s3_client.get_object(Bucket="test-bucket", Key="uploaded.txt")
    assert response["Body"].read() == b"upload content"
```

## Definition of Done

- [ ] `app/adapters/s3_repository.py` created
- [ ] AbstractS3Repository and S3Repository implemented
- [ ] Singleton pattern with get/reset functions
- [ ] Unit tests with moto passing
- [ ] All methods have docstrings
- [ ] Error handling maps to custom exceptions

## Effort Estimate

**Points**: 3  
**Confidence**: High  
**Rationale**: Direct copy from flexibilizador, well-tested pattern
