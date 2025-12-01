# TICKET-007: Create S3NewaveUnitOfWork

> **Epic**: [Epic 01: S3 Integration Layer](../../00-epic-overview.md)  
> **Sprint**: [Sprint 02](./00-sprint-overview.md)  
> **Points**: 3  
> **Dependencies**: [TICKET-002](../sprint-01/ticket-002-implement-s3-repository.md), [TICKET-003](../sprint-01/ticket-003-implement-zip-utilities.md), [TICKET-004](../sprint-01/ticket-004-implement-temp-manager.md)  
> **Blocks**: [TICKET-015](../../epic-02-api-modernization/sprint-02/ticket-015-update-reservoir-router.md)

## Context

### Background

The service needs to handle NEWAVE cases as destinations for rule application. When rules are applied to NEWAVE, the files modified are `re.dat` and `modif.dat`. The Unit of Work must download, extract, provide repository access, and upload results.

### Current State

The existing `NewaveUnitOfWork` in `app/services/unitofwork.py` uses filesystem paths. We need an S3-based variant.

## Specification

### File Location

- `app/services/unitofwork.py` (MODIFY - add new class)

### Class: S3NewaveUnitOfWork

```python
class S3NewaveUnitOfWork(AbstractUnitOfWork):
    """
    Unit of Work for a NEWAVE case from S3.
    
    Downloads deck_processado.zip, extracts to temp dir, provides file access,
    and supports uploading modified results back to S3.
    
    Modified files for rules:
    - re.dat (reservoir constraints)
    - modif.dat (modifications)
    """
    
    def __init__(
        self,
        s3_repo: S3Repository,
        bucket: str,
        execution_hash: str,
        output_prefix: str = "ingest",
    ):
        self._s3_repo = s3_repo
        self._bucket = bucket
        self._execution_hash = execution_hash
        self._output_prefix = output_prefix
        self._temp_dir: Optional[Path] = None
        self._newave: Optional[RawNewaveRepository] = None
    
    async def __aenter__(self) -> "S3NewaveUnitOfWork":
        # Create temp directory
        self._temp_dir = Path(tempfile.mkdtemp(
            dir=Settings.temp_dir,
            prefix="newave_"
        ))
        
        # Download and extract deck
        zip_key = f"artifacts/{self._execution_hash}/entradas/deck_processado.zip"
        zip_path = self._temp_dir / "deck_processado.zip"
        await self._s3_repo.download_file(self._bucket, zip_key, str(zip_path))
        extract_zip(zip_path, self._temp_dir)
        zip_path.unlink()  # Remove zip after extraction
        
        # Create repository
        self._newave = RawNewaveRepository(str(self._temp_dir))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._temp_dir:
            cleanup_directory(self._temp_dir)
    
    @property
    def program(self) -> Program:
        return Program.NEWAVE
    
    @property
    def files(self) -> AbstractNewaveRepository:
        return self._newave
    
    async def upload_result(self) -> str:
        """
        Zip temp directory and upload to S3.
        
        Returns:
            S3 key of uploaded file
        """
        output_key = f"{self._output_prefix}/{self._execution_hash}_regras.zip"
        zip_path = self._temp_dir.parent / f"{self._execution_hash}_regras.zip"
        
        create_zip(self._temp_dir, zip_path, Settings.zip_compression_level)
        await self._s3_repo.upload_file(str(zip_path), self._bucket, output_key)
        zip_path.unlink()
        
        return output_key
    
    def rollback(self):
        """No-op for S3 - cleanup handled by __aexit__."""
        pass
```

### S3 Key Patterns

```python
# Input
f"artifacts/{execution_hash}/entradas/deck_processado.zip"

# Output
f"ingest/{execution_hash}_regras.zip"
```

### NEWAVE Files Modified by Rules

| File | Purpose | Registry Modified |
|------|---------|-------------------|
| `re.dat` | Reservoir constraints | RE records |
| `modif.dat` | General modifications | Various |

## Acceptance Criteria

- [ ] Given valid S3 bucket and hash, when `S3NewaveUnitOfWork` enters context, then deck_processado.zip is downloaded and extracted
- [ ] Given extracted files, when `files` property accessed, then `RawNewaveRepository` provides file access
- [ ] Given modified files, when `upload_result()` called, then zip uploaded to `ingest/<hash>_regras.zip`
- [ ] Given context exit (normal or exception), when `__aexit__` runs, then temp dir is cleaned up
- [ ] Given missing S3 object, when download attempted, then `ArtifactNotFoundError` raised
- [ ] `program` property returns `Program.NEWAVE`

## Implementation Guide

### Suggested Approach

1. Open `app/services/unitofwork.py`
2. Copy pattern from `S3DecompUnitOfWork`
3. Change repository to `RawNewaveRepository`
4. Change `Program` to `NEWAVE`
5. Adjust temp dir prefix to `newave_`
6. Keep existing `NewaveUnitOfWork` for backward compatibility
7. Write integration tests

### Key Files to Read

- `app/services/unitofwork.py` - Current implementation
- `app/adapters/newaverepository.py` - Repository interface
- [TICKET-006](./ticket-006-create-s3-decomp-uow.md) - Similar DECOMP implementation

### Pitfalls to Avoid

- ⚠️ NEWAVE doesn't need relato download (unlike DECOMP prospection)
- ⚠️ NEWAVE doesn't use caso.dat for extension (uses arquivos.dat)
- ⚠️ Remember to import `RawNewaveRepository`

## Testing Requirements

### Integration Tests

Create `tests/integration/test_s3_newave_uow.py`:

```python
import pytest
from moto import mock_aws
import boto3
from app.services.unitofwork import S3NewaveUnitOfWork
from app.adapters.s3_repository import S3Repository
from app.models.program import Program

@pytest.fixture
def s3_with_newave_case(aws_credentials):
    """S3 bucket with a NEWAVE case uploaded."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="newave-bucket")
        
        # Upload deck_processado.zip with minimal NEWAVE files
        # ... fixture setup ...
        
        yield client

@pytest.mark.asyncio
async def test_s3_newave_uow_download_extract(s3_with_newave_case):
    s3_repo = S3Repository(region="us-east-1")
    
    async with S3NewaveUnitOfWork(
        s3_repo, "newave-bucket", "test456"
    ) as uow:
        assert uow.program == Program.NEWAVE
        assert uow.files is not None

@pytest.mark.asyncio
async def test_s3_newave_uow_upload_result(s3_with_newave_case):
    s3_repo = S3Repository(region="us-east-1")
    
    async with S3NewaveUnitOfWork(
        s3_repo, "newave-bucket", "test456"
    ) as uow:
        output_key = await uow.upload_result()
        assert output_key == "ingest/test456_regras.zip"

@pytest.mark.asyncio
async def test_s3_newave_uow_cleanup_on_exception(s3_with_newave_case, tmp_path):
    s3_repo = S3Repository(region="us-east-1")
    temp_dir = None
    
    with pytest.raises(RuntimeError):
        async with S3NewaveUnitOfWork(
            s3_repo, "newave-bucket", "test456"
        ) as uow:
            temp_dir = uow._temp_dir
            raise RuntimeError("Test error")
    
    assert not temp_dir.exists()  # Cleaned up despite exception
```

## Definition of Done

- [ ] `S3NewaveUnitOfWork` implemented
- [ ] Integration tests with moto passing
- [ ] Temp directory cleaned up on exit
- [ ] Upload creates proper zip and S3 key
- [ ] Docstrings on class and methods

## Effort Estimate

**Points**: 3  
**Confidence**: High  
**Rationale**: Similar pattern to DECOMP but simpler (no prospection)
