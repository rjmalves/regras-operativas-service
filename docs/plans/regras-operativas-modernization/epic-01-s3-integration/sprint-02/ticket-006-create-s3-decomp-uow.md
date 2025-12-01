# TICKET-006: Create S3DecompUnitOfWork

> **Epic**: [Epic 01: S3 Integration Layer](../../00-epic-overview.md)  
> **Sprint**: [Sprint 02](./00-sprint-overview.md)  
> **Points**: 5  
> **Dependencies**: [TICKET-002](../sprint-01/ticket-002-implement-s3-repository.md), [TICKET-003](../sprint-01/ticket-003-implement-zip-utilities.md), [TICKET-004](../sprint-01/ticket-004-implement-temp-manager.md)  
> **Blocks**: [TICKET-015](../../epic-02-api-modernization/sprint-02/ticket-015-update-reservoir-router.md)

## Context

### Background

The service needs to download DECOMP artifacts from S3, extract them to temporary directories, process the files, and upload results. Unlike flexibilizador (single case), regras-operativas needs to support **multiple source cases** for prospection - reading reservoir storage data from previous executions.

### Current State

The existing `DecompUnitOfWork` in `app/services/unitofwork.py` uses `chdir()` to navigate to filesystem paths. We need S3-based variants that:
1. Download from S3
2. Extract to temp dir
3. Provide repository access
4. Upload results
5. Clean up temp dirs

## Specification

### File Location

- `app/services/unitofwork.py` (MODIFY - add new classes)

### Class: S3DecompUnitOfWork (Single Case)

For destination case that will be modified:

```python
class S3DecompUnitOfWork(AbstractUnitOfWork):
    """
    Unit of Work for a single DECOMP case from S3.
    
    Downloads deck_processado.zip, extracts to temp dir, provides file access,
    and supports uploading modified results back to S3.
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
        self._decomp: Optional[RawDecompRepository] = None
    
    async def __aenter__(self) -> "S3DecompUnitOfWork":
        # Create temp directory
        self._temp_dir = Path(tempfile.mkdtemp(
            dir=Settings.temp_dir,
            prefix="decomp_"
        ))
        
        # Download and extract deck
        zip_key = f"artifacts/{self._execution_hash}/entradas/deck_processado.zip"
        zip_path = self._temp_dir / "deck_processado.zip"
        await self._s3_repo.download_file(self._bucket, zip_key, str(zip_path))
        extract_zip(zip_path, self._temp_dir)
        zip_path.unlink()  # Remove zip after extraction
        
        # Create repository
        self._decomp = RawDecompRepository(str(self._temp_dir))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._temp_dir:
            cleanup_directory(self._temp_dir)
    
    @property
    def program(self) -> Program:
        return Program.DECOMP
    
    @property
    def files(self) -> AbstractDecompRepository:
        return self._decomp
    
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
```

### Class: S3DecompProspectionUnitOfWork (Multiple Sources)

For source cases used for reservoir storage prospection:

```python
class S3DecompProspectionUnitOfWork:
    """
    Unit of Work for multiple DECOMP source cases (prospection).
    
    Downloads multiple cases for reading reservoir storage data.
    Does NOT upload - read only.
    """
    
    def __init__(
        self,
        s3_repo: S3Repository,
        sources: List[Tuple[str, str]],  # List of (bucket, execution_hash)
    ):
        self._s3_repo = s3_repo
        self._sources = sources
        self._temp_dirs: List[Path] = []
        self._repositories: List[RawDecompRepository] = []
    
    async def __aenter__(self) -> "S3DecompProspectionUnitOfWork":
        for bucket, execution_hash in self._sources:
            temp_dir = Path(tempfile.mkdtemp(
                dir=Settings.temp_dir,
                prefix=f"decomp_src_{execution_hash[:8]}_"
            ))
            self._temp_dirs.append(temp_dir)
            
            # Download deck and relato
            await self._download_source_files(bucket, execution_hash, temp_dir)
            
            # Create repository
            repo = RawDecompRepository(str(temp_dir))
            self._repositories.append(repo)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for temp_dir in self._temp_dirs:
            cleanup_directory(temp_dir)
    
    async def _download_source_files(
        self, bucket: str, execution_hash: str, temp_dir: Path
    ) -> None:
        """Download deck zip and relato file for a source case."""
        # Download and extract deck
        zip_key = f"artifacts/{execution_hash}/entradas/deck_processado.zip"
        zip_path = temp_dir / "deck_processado.zip"
        await self._s3_repo.download_file(bucket, zip_key, str(zip_path))
        extract_zip(zip_path, temp_dir)
        zip_path.unlink()
        
        # Download relato (need to find extension from caso.dat)
        caso = Caso.read(str(temp_dir / "caso.dat"))
        relato_key = f"artifacts/{execution_hash}/saidas/relato.{caso.arquivos}"
        relato_path = temp_dir / f"relato.{caso.arquivos}"
        await self._s3_repo.download_file(bucket, relato_key, str(relato_path))
    
    @property
    def repositories(self) -> List[RawDecompRepository]:
        """Access to all source repositories for prospection."""
        return self._repositories
```

## Acceptance Criteria

- [ ] Given valid S3 bucket and hash, when `S3DecompUnitOfWork` enters context, then deck_processado.zip is downloaded and extracted
- [ ] Given extracted files, when `files` property accessed, then `RawDecompRepository` provides file access
- [ ] Given modified files, when `upload_result()` called, then zip uploaded to `ingest/<hash>_regras.zip`
- [ ] Given context exit (normal or exception), when `__aexit__` runs, then temp dir is cleaned up
- [ ] Given multiple sources, when `S3DecompProspectionUnitOfWork` enters, then all sources downloaded
- [ ] Given prospection UoW, when `repositories` accessed, then list of repositories returned
- [ ] Given missing S3 object, when download attempted, then `ArtifactNotFoundError` raised

## Implementation Guide

### Suggested Approach

1. Open `app/services/unitofwork.py`
2. Add imports for S3Repository, zip_utils, temp_manager
3. Implement `S3DecompUnitOfWork` class
4. Implement `S3DecompProspectionUnitOfWork` class
5. Keep existing `DecompUnitOfWork` (for backward compatibility during transition)
6. Write integration tests with moto

### S3 Key Patterns

```python
# Input artifacts
f"artifacts/{execution_hash}/entradas/deck_processado.zip"
f"artifacts/{execution_hash}/saidas/relato.{ext}"
f"artifacts/{execution_hash}/saidas/inviab_unic.{ext}"

# Output
f"ingest/{execution_hash}_regras.zip"
```

### Key Files to Read

- `app/services/unitofwork.py` - Current implementation
- `/home/rogerio/git/flexibilizador-service/app/services/unitofwork.py` - Reference (simpler, single case)
- `app/adapters/decomprepository.py` - Repository interface

### Pitfalls to Avoid

- ⚠️ Must use async context manager (`async with`) not sync
- ⚠️ Don't forget to cleanup ALL temp dirs in prospection (loop)
- ⚠️ relato file extension varies - read from caso.dat
- ⚠️ Remove zip file after extraction to save space

## Testing Requirements

### Integration Tests

Create `tests/integration/test_s3_decomp_uow.py`:

```python
import pytest
from moto import mock_aws
import boto3
from pathlib import Path
from app.services.unitofwork import S3DecompUnitOfWork, S3DecompProspectionUnitOfWork
from app.adapters.s3_repository import S3Repository

@pytest.fixture
def s3_with_decomp_case(aws_credentials):
    """S3 bucket with a DECOMP case uploaded."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="decomp-bucket")
        
        # Upload deck_processado.zip (create minimal valid one)
        # ... fixture setup ...
        
        yield client

@pytest.mark.asyncio
async def test_s3_decomp_uow_download_extract(s3_with_decomp_case):
    s3_repo = S3Repository(region="us-east-1")
    
    async with S3DecompUnitOfWork(
        s3_repo, "decomp-bucket", "test123"
    ) as uow:
        # Verify files extracted
        assert uow.files is not None
        # Test file access...
    
    # Verify cleanup
    # ...

@pytest.mark.asyncio
async def test_s3_decomp_uow_upload_result(s3_with_decomp_case):
    s3_repo = S3Repository(region="us-east-1")
    
    async with S3DecompUnitOfWork(
        s3_repo, "decomp-bucket", "test123"
    ) as uow:
        output_key = await uow.upload_result()
        
        assert output_key == "ingest/test123_regras.zip"
        # Verify S3 object exists...
```

## Definition of Done

- [ ] `S3DecompUnitOfWork` implemented
- [ ] `S3DecompProspectionUnitOfWork` implemented
- [ ] Integration tests with moto passing
- [ ] Temp directories cleaned up on exit
- [ ] Upload creates proper zip and S3 key
- [ ] Docstrings on all classes and methods

## Effort Estimate

**Points**: 5  
**Confidence**: Medium  
**Rationale**: Complex due to multi-source handling, async context managers, and S3 interaction
