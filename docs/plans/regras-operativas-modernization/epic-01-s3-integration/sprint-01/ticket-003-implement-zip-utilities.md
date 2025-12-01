# TICKET-003: Implement Zip Utilities

> **Epic**: [Epic 01: S3 Integration Layer](../../00-epic-overview.md)  
> **Sprint**: [Sprint 01](./00-sprint-overview.md)  
> **Points**: 2  
> **Dependencies**: None  
> **Blocks**: [TICKET-006](../sprint-02/ticket-006-create-s3-decomp-uow.md), [TICKET-007](../sprint-02/ticket-007-create-s3-newave-uow.md)

## Context

### Background

DECOMP and NEWAVE artifacts are stored as zip files in S3 (deck_processado.zip). We need utilities to extract these zips to temporary directories for processing and to create new zips for upload after rule application.

### Current State

No zip handling utilities exist. Files are read directly from the filesystem.

## Specification

### File Location

- `app/utils/zip_utils.py` (CREATE)

### Functions

```python
def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """
    Extract a zip file to a destination directory.
    
    All files extracted to root of dest_dir (no subdirectories preserved).
    Validates zip integrity before extraction.
    
    Args:
        zip_path: Path to the zip file
        dest_dir: Directory to extract files to
        
    Raises:
        zipfile.BadZipFile: If zip file is corrupted
        FileNotFoundError: If zip file doesn't exist
    """

def create_zip(
    source_dir: Path,
    zip_path: Path,
    compression_level: int = 6,
) -> None:
    """
    Create a zip file from all files in a directory.
    
    Files added at root level (no directory structure preserved).
    
    Args:
        source_dir: Directory containing files to zip
        zip_path: Path for the output zip file
        compression_level: Compression level (0-9, default 6)
        
    Raises:
        FileNotFoundError: If source_dir doesn't exist
        ValueError: If source_dir is empty
    """

def get_zip_file_list(zip_path: Path) -> list[str]:
    """
    Get list of files in a zip archive.
    
    Args:
        zip_path: Path to the zip file
        
    Returns:
        List of filenames in the archive
    """
```

### Implementation

```python
import zipfile
from pathlib import Path
from app.utils.log import Log

def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    Log.log().info(f"Extracting {zip_path} to {dest_dir}")
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Validate zip integrity
        bad_file = zf.testzip()
        if bad_file is not None:
            raise zipfile.BadZipFile(f"Corrupted file in archive: {bad_file}")
        
        zf.extractall(dest_dir)
    
    Log.log().info(f"Extracted {len(list(dest_dir.iterdir()))} files")

def create_zip(
    source_dir: Path,
    zip_path: Path,
    compression_level: int = 6,
) -> None:
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")
    
    files = [f for f in source_dir.iterdir() if f.is_file()]
    if not files:
        raise ValueError(f"Source directory is empty: {source_dir}")
    
    Log.log().info(f"Creating zip {zip_path} from {len(files)} files")
    
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=compression_level,
    ) as zf:
        for file_path in files:
            zf.write(file_path, file_path.name)
    
    Log.log().info(f"Created zip: {zip_path} ({zip_path.stat().st_size} bytes)")
```

## Acceptance Criteria

- [ ] Given valid zip file, when `extract_zip()` is called, then all files extracted to dest_dir
- [ ] Given corrupted zip file, when `extract_zip()` is called, then `BadZipFile` is raised
- [ ] Given non-existent zip file, when `extract_zip()` is called, then `FileNotFoundError` is raised
- [ ] Given directory with files, when `create_zip()` is called, then zip created with all files
- [ ] Given empty directory, when `create_zip()` is called, then `ValueError` is raised
- [ ] Given compression_level=0, when `create_zip()` is called, then zip has no compression
- [ ] `get_zip_file_list()` returns list of all filenames in archive

## Implementation Guide

### Suggested Approach

1. Create `app/utils/zip_utils.py`
2. Copy implementation from flexibilizador-service
3. Update log message prefix if desired
4. Write unit tests with real zip files

### Reference Implementation

Copy from: `/home/rogerio/git/flexibilizador-service/app/utils/zip_utils.py`

Changes needed:
- None (exact copy works)

### Key Files to Read

- `/home/rogerio/git/flexibilizador-service/app/utils/zip_utils.py` - Reference implementation
- `app/utils/log.py` - Logging utilities

### Pitfalls to Avoid

- ⚠️ Don't forget to validate zip integrity with `testzip()`
- ⚠️ Extracted files go to root of dest_dir (no nested directories)
- ⚠️ Created zip has files at root level (just filename, no path)

## Testing Requirements

### Unit Tests

Create `tests/unit/test_zip_utils.py`:

```python
import pytest
import zipfile
from pathlib import Path
from app.utils.zip_utils import extract_zip, create_zip, get_zip_file_list

@pytest.fixture
def sample_zip(tmp_path):
    """Create a sample zip file for testing."""
    zip_path = tmp_path / "test.zip"
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "file1.txt").write_text("content1")
    (source_dir / "file2.dat").write_bytes(b"\x00\x01\x02")
    
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(source_dir / "file1.txt", "file1.txt")
        zf.write(source_dir / "file2.dat", "file2.dat")
    
    return zip_path

def test_extract_zip_success(sample_zip, tmp_path):
    dest = tmp_path / "extracted"
    dest.mkdir()
    
    extract_zip(sample_zip, dest)
    
    assert (dest / "file1.txt").read_text() == "content1"
    assert (dest / "file2.dat").read_bytes() == b"\x00\x01\x02"

def test_extract_zip_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_zip(tmp_path / "nonexistent.zip", tmp_path)

def test_create_zip_success(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.txt").write_text("a")
    (source / "b.txt").write_text("b")
    
    zip_path = tmp_path / "output.zip"
    create_zip(source, zip_path)
    
    assert zip_path.exists()
    file_list = get_zip_file_list(zip_path)
    assert set(file_list) == {"a.txt", "b.txt"}

def test_create_zip_empty_dir(tmp_path):
    source = tmp_path / "empty"
    source.mkdir()
    
    with pytest.raises(ValueError, match="empty"):
        create_zip(source, tmp_path / "out.zip")

def test_get_zip_file_list(sample_zip):
    files = get_zip_file_list(sample_zip)
    assert set(files) == {"file1.txt", "file2.dat"}
```

## Definition of Done

- [ ] `app/utils/zip_utils.py` created
- [ ] All 3 functions implemented
- [ ] Unit tests passing
- [ ] Functions have docstrings
- [ ] Logging on extract/create operations

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Direct copy from flexibilizador, straightforward stdlib usage
