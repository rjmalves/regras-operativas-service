# [TICKET-022] Integration tests for Unit of Work

> **Epic**: [Epic 03: Testing Infrastructure](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: TICKET-018 (pytest fixtures), TICKET-006 (S3DecompUoW), TICKET-007 (S3NewaveUoW)  
> **Blocks**: None

## Context

### Background

The Unit of Work classes orchestrate S3 downloads, file extraction, processing, and uploads. Integration tests verify these workflows work correctly end-to-end with mocked S3.

### Files to Read Before Starting

- `app/services/unitofwork.py` - UoW implementations
- `app/adapters/s3_repository.py` - S3 operations
- `app/utils/temp_manager.py` - Temp directory management
- `tests/conftest.py` - Available fixtures

## Specification

### File to Create

`tests/integration/test_unitofwork.py`

### Test Implementation

```python
"""Integration tests for Unit of Work classes."""

import pytest
import zipfile
from pathlib import Path

from app.services.unitofwork import S3DecompUnitOfWork, S3NewaveUnitOfWork
from app.utils.temp_manager import TempDirectoryManager


@pytest.fixture
def temp_manager(temp_directory):
    """Create temp directory manager for tests."""
    manager = TempDirectoryManager(base_dir=temp_directory)
    yield manager
    manager.cleanup_all()


@pytest.fixture
def decomp_artifact_with_files(s3_client, temp_directory):
    """Create DECOMP artifact with realistic files."""
    bucket = "test-decomp-bucket"
    execution_hash = "decomp_test_hash"
    
    # Create zip with DECOMP-like files
    source_dir = temp_directory / "decomp_source"
    source_dir.mkdir()
    
    # Create minimal DECOMP files
    (source_dir / "caso.dat").write_text("CASO DE TESTE DECOMP\n")
    (source_dir / "dadger.rv0").write_text(
        " TITULO\n"
        " &\n"
        " CASO DE TESTE\n"
        " &\n"
        " FIM\n"
    )
    (source_dir / "hidr.dat").write_text("DADOS HIDRAULICOS\n")
    
    # Create zip
    zip_path = temp_directory / "deck_processado.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in source_dir.iterdir():
            zf.write(file, file.name)
    
    # Upload to S3
    key = f"artifacts/{execution_hash}/entradas/deck_processado.zip"
    with open(zip_path, 'rb') as f:
        s3_client.put_object(Bucket=bucket, Key=key, Body=f.read())
    
    # Also create a mock relato file
    relato_content = b"RELATO DE SAIDA DECOMP\n"
    relato_key = f"artifacts/{execution_hash}/saidas/relato.rv0"
    s3_client.put_object(Bucket=bucket, Key=relato_key, Body=relato_content)
    
    return {
        "bucket": bucket,
        "execution_hash": execution_hash,
        "input_key": key,
        "relato_key": relato_key
    }


@pytest.fixture
def newave_artifact_with_files(s3_client, temp_directory):
    """Create NEWAVE artifact with realistic files."""
    bucket = "test-newave-bucket"
    execution_hash = "newave_test_hash"
    
    # Create zip with NEWAVE-like files
    source_dir = temp_directory / "newave_source"
    source_dir.mkdir()
    
    # Create minimal NEWAVE files
    (source_dir / "arquivos.dat").write_text("ARQUIVOS DE DADOS DO NEWAVE\n")
    (source_dir / "re.dat").write_text(
        " RESTRICOES ELETRICAS\n"
        " &\n"
    )
    (source_dir / "modif.dat").write_text(
        " MODIFICACOES\n"
        " &\n"
    )
    (source_dir / "sistema.dat").write_text("DADOS DO SISTEMA\n")
    
    # Create zip
    zip_path = temp_directory / "deck_processado.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in source_dir.iterdir():
            zf.write(file, file.name)
    
    # Upload to S3
    key = f"artifacts/{execution_hash}/entradas/deck_processado.zip"
    with open(zip_path, 'rb') as f:
        s3_client.put_object(Bucket=bucket, Key=key, Body=f.read())
    
    return {
        "bucket": bucket,
        "execution_hash": execution_hash,
        "input_key": key
    }


class TestS3DecompUnitOfWork:
    """Test S3DecompUnitOfWork integration."""
    
    def test_download_and_extract(
        self, s3_repo, decomp_artifact_with_files, temp_manager
    ):
        """Test downloading and extracting DECOMP artifact."""
        uow = S3DecompUnitOfWork(
            s3_repo=s3_repo,
            temp_manager=temp_manager,
            bucket=decomp_artifact_with_files["bucket"],
            execution_hash=decomp_artifact_with_files["execution_hash"]
        )
        
        # Execute download/extract
        work_dir = uow.setup()
        
        assert work_dir.exists()
        assert (work_dir / "caso.dat").exists()
        assert (work_dir / "dadger.rv0").exists()
        
        # Cleanup
        uow.cleanup()
    
    def test_context_manager_cleanup(
        self, s3_repo, decomp_artifact_with_files, temp_manager
    ):
        """Test context manager auto-cleanup."""
        with S3DecompUnitOfWork(
            s3_repo=s3_repo,
            temp_manager=temp_manager,
            bucket=decomp_artifact_with_files["bucket"],
            execution_hash=decomp_artifact_with_files["execution_hash"]
        ) as uow:
            work_dir = uow.work_dir
            assert work_dir.exists()
        
        # After context, should be cleaned up
        assert not work_dir.exists()
    
    def test_upload_result(
        self, s3_repo, s3_client, decomp_artifact_with_files, temp_manager
    ):
        """Test uploading result back to S3."""
        bucket = decomp_artifact_with_files["bucket"]
        execution_hash = decomp_artifact_with_files["execution_hash"]
        
        uow = S3DecompUnitOfWork(
            s3_repo=s3_repo,
            temp_manager=temp_manager,
            bucket=bucket,
            execution_hash=execution_hash
        )
        
        work_dir = uow.setup()
        
        # Modify a file
        (work_dir / "modified.txt").write_text("Modified content")
        
        # Upload result
        output_key = uow.upload_result(output_prefix="ingest")
        
        # Verify upload
        assert output_key is not None
        assert s3_repo.object_exists(bucket, output_key)
        
        uow.cleanup()
    
    def test_missing_artifact_raises_error(
        self, s3_repo, temp_manager
    ):
        """Test missing artifact raises ArtifactNotFoundError."""
        from app.internal.exceptions import ArtifactNotFoundError
        
        uow = S3DecompUnitOfWork(
            s3_repo=s3_repo,
            temp_manager=temp_manager,
            bucket="test-decomp-bucket",
            execution_hash="nonexistent_hash"
        )
        
        with pytest.raises(ArtifactNotFoundError):
            uow.setup()


class TestS3NewaveUnitOfWork:
    """Test S3NewaveUnitOfWork integration."""
    
    def test_download_and_extract(
        self, s3_repo, newave_artifact_with_files, temp_manager
    ):
        """Test downloading and extracting NEWAVE artifact."""
        uow = S3NewaveUnitOfWork(
            s3_repo=s3_repo,
            temp_manager=temp_manager,
            bucket=newave_artifact_with_files["bucket"],
            execution_hash=newave_artifact_with_files["execution_hash"]
        )
        
        work_dir = uow.setup()
        
        assert work_dir.exists()
        assert (work_dir / "arquivos.dat").exists()
        assert (work_dir / "re.dat").exists()
        assert (work_dir / "modif.dat").exists()
        
        uow.cleanup()
    
    def test_context_manager_cleanup(
        self, s3_repo, newave_artifact_with_files, temp_manager
    ):
        """Test context manager auto-cleanup."""
        with S3NewaveUnitOfWork(
            s3_repo=s3_repo,
            temp_manager=temp_manager,
            bucket=newave_artifact_with_files["bucket"],
            execution_hash=newave_artifact_with_files["execution_hash"]
        ) as uow:
            work_dir = uow.work_dir
            assert work_dir.exists()
            assert (work_dir / "re.dat").exists()
        
        assert not work_dir.exists()
    
    def test_upload_result(
        self, s3_repo, s3_client, newave_artifact_with_files, temp_manager
    ):
        """Test uploading modified NEWAVE result."""
        bucket = newave_artifact_with_files["bucket"]
        execution_hash = newave_artifact_with_files["execution_hash"]
        
        uow = S3NewaveUnitOfWork(
            s3_repo=s3_repo,
            temp_manager=temp_manager,
            bucket=bucket,
            execution_hash=execution_hash
        )
        
        work_dir = uow.setup()
        
        # Modify re.dat
        re_dat = work_dir / "re.dat"
        re_dat.write_text(re_dat.read_text() + " MODIFICADO\n")
        
        # Upload
        output_key = uow.upload_result(output_prefix="ingest")
        
        # Verify
        assert output_key is not None
        assert s3_repo.object_exists(bucket, output_key)
        
        uow.cleanup()


class TestMultiSourceWorkflow:
    """Test multi-source workflow (DECOMP → NEWAVE)."""
    
    def test_read_source_write_destination(
        self, s3_repo, decomp_artifact_with_files, newave_artifact_with_files, temp_manager
    ):
        """Test reading from source and writing to destination."""
        # Setup source (DECOMP)
        source_uow = S3DecompUnitOfWork(
            s3_repo=s3_repo,
            temp_manager=temp_manager,
            bucket=decomp_artifact_with_files["bucket"],
            execution_hash=decomp_artifact_with_files["execution_hash"]
        )
        source_dir = source_uow.setup()
        
        # Read data from source
        source_caso = (source_dir / "caso.dat").read_text()
        
        # Setup destination (NEWAVE)
        dest_uow = S3NewaveUnitOfWork(
            s3_repo=s3_repo,
            temp_manager=temp_manager,
            bucket=newave_artifact_with_files["bucket"],
            execution_hash=newave_artifact_with_files["execution_hash"]
        )
        dest_dir = dest_uow.setup()
        
        # Modify destination based on source
        modif_dat = dest_dir / "modif.dat"
        original_content = modif_dat.read_text()
        modif_dat.write_text(
            original_content + f" &\n BASEADO EM: {source_caso.strip()}\n"
        )
        
        # Upload destination result
        output_key = dest_uow.upload_result(output_prefix="ingest")
        
        # Verify
        assert output_key is not None
        assert s3_repo.object_exists(
            newave_artifact_with_files["bucket"],
            output_key
        )
        
        # Cleanup
        source_uow.cleanup()
        dest_uow.cleanup()


class TestUnitOfWorkErrorHandling:
    """Test error handling in Unit of Work."""
    
    def test_cleanup_on_setup_failure(self, s3_repo, temp_manager):
        """Test cleanup happens even if setup fails."""
        from app.internal.exceptions import ArtifactNotFoundError
        
        uow = S3DecompUnitOfWork(
            s3_repo=s3_repo,
            temp_manager=temp_manager,
            bucket="test-decomp-bucket",
            execution_hash="nonexistent"
        )
        
        try:
            uow.setup()
        except ArtifactNotFoundError:
            pass
        
        # Verify no lingering temp directories
        managed_dirs = temp_manager.list_managed()
        # Should either be empty or the failed dir should be cleaned
        for d in managed_dirs:
            assert not d.exists() or len(list(d.iterdir())) == 0
    
    def test_context_manager_cleanup_on_exception(
        self, s3_repo, decomp_artifact_with_files, temp_manager
    ):
        """Test context manager cleans up on exception."""
        work_dir_path = None
        
        try:
            with S3DecompUnitOfWork(
                s3_repo=s3_repo,
                temp_manager=temp_manager,
                bucket=decomp_artifact_with_files["bucket"],
                execution_hash=decomp_artifact_with_files["execution_hash"]
            ) as uow:
                work_dir_path = uow.work_dir
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        # Should still be cleaned up
        assert work_dir_path is None or not work_dir_path.exists()
```

## Acceptance Criteria

- [ ] All Unit of Work tests pass
- [ ] Download/extract workflow tested
- [ ] Upload workflow tested
- [ ] Context manager cleanup verified
- [ ] Multi-source workflow tested
- [ ] Error handling tested
- [ ] No lingering temp directories after tests

## Implementation Guide

### Step 1: Create Test File

```bash
touch tests/integration/test_unitofwork.py
```

### Step 2: Create Fixtures

Create fixtures that generate realistic DECOMP/NEWAVE file structures.

### Step 3: Implement Tests

Implement tests following the structure above, adapting to actual UoW interface.

### Step 4: Run Tests

```bash
uv run pytest tests/integration/test_unitofwork.py -v
```

## Testing Requirements

### Prerequisites

- S3DecompUnitOfWork implemented
- S3NewaveUnitOfWork implemented
- TempDirectoryManager working
- S3Repository working

### Test Data

Create minimal but valid DECOMP/NEWAVE file structures that the parsing libraries can handle.

## Definition of Done

- [ ] Test file created
- [ ] All tests pass
- [ ] Download/extract verified
- [ ] Upload verified
- [ ] Multi-source workflow tested
- [ ] Error handling verified
- [ ] Code reviewed

## Effort Estimate

**Points**: 3  
**Confidence**: Medium  
**Rationale**: Depends on UoW implementation details; may need fixture adjustments for real parsing
