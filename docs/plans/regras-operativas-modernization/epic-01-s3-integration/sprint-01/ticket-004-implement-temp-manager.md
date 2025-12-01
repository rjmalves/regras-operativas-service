# TICKET-004: Implement Temp Directory Manager

> **Epic**: [Epic 01: S3 Integration Layer](../../00-epic-overview.md)  
> **Sprint**: [Sprint 01](./00-sprint-overview.md)  
> **Points**: 2  
> **Dependencies**: None  
> **Blocks**: [TICKET-006](../sprint-02/ticket-006-create-s3-decomp-uow.md), [TICKET-007](../sprint-02/ticket-007-create-s3-newave-uow.md)

## Context

### Background

When processing artifacts from S3, we need temporary directories to extract zip files and work with the contents. These directories must be cleaned up after processing to avoid disk space issues. The manager provides context managers for safe lifecycle management.

### Current State

No temp directory management exists. The codebase uses `chdir()` to navigate to case directories on the filesystem.

## Specification

### File Location

- `app/utils/temp_manager.py` (CREATE)

### Functions and Context Managers

```python
@contextmanager
def temp_directory(
    base_dir: str = "/tmp/regras-operativas",
    prefix: str = "regras_",
) -> Generator[Path, None, None]:
    """
    Sync context manager for temporary directory lifecycle.
    
    Creates unique temp directory, yields it, cleans up on exit.
    """

@asynccontextmanager
async def async_temp_directory(
    base_dir: str = "/tmp/regras-operativas",
    prefix: str = "regras_",
) -> AsyncGenerator[Path, None]:
    """
    Async context manager for temporary directory lifecycle.
    """

def cleanup_directory(dir_path: Path) -> bool:
    """
    Remove a directory and all contents.
    
    Returns True if cleanup succeeded, False otherwise.
    """

def cleanup_old_temp_dirs(
    base_dir: str = "/tmp/regras-operativas",
    max_age_hours: int = 24,
) -> int:
    """
    Remove temp directories older than max_age_hours.
    
    Returns number of directories removed.
    """
```

### Implementation

```python
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
    if not dir_path.exists():
        return True
    
    try:
        shutil.rmtree(dir_path)
        Log.log().info(f"Cleaned up temp directory: {dir_path}")
        return True
    except Exception as e:
        Log.log().warning(f"Failed to cleanup {dir_path}: {e}")
        return False
```

## Acceptance Criteria

- [ ] Given `temp_directory()` context manager, when entered, then unique directory created under base_dir
- [ ] Given `temp_directory()` context manager, when exited normally, then directory is deleted
- [ ] Given `temp_directory()` context manager, when exception raised inside, then directory is still deleted
- [ ] Given `async_temp_directory()`, when used with `async with`, then behaves same as sync version
- [ ] Given `cleanup_directory()` on existing dir, when called, then returns True and dir is gone
- [ ] Given `cleanup_directory()` on non-existent dir, when called, then returns True
- [ ] Given `cleanup_old_temp_dirs()` with old directories, when called, then old dirs removed
- [ ] Temp directories have prefix "regras_" by default

## Implementation Guide

### Suggested Approach

1. Create `app/utils/temp_manager.py`
2. Copy implementation from flexibilizador-service
3. Change default `base_dir` to `/tmp/regras-operativas`
4. Change default `prefix` to `regras_`
5. Write unit tests

### Reference Implementation

Copy from: `/home/rogerio/git/flexibilizador-service/app/utils/temp_manager.py`

Changes needed:
- `base_dir` default: `/tmp/flexibilizador` → `/tmp/regras-operativas`
- `prefix` default: `flex_` → `regras_`

### Key Files to Read

- `/home/rogerio/git/flexibilizador-service/app/utils/temp_manager.py` - Reference
- `app/utils/log.py` - Logging utilities

### Pitfalls to Avoid

- ⚠️ Always use context manager or ensure cleanup is called
- ⚠️ Don't assume base_dir exists - create it with `mkdir(parents=True, exist_ok=True)`
- ⚠️ The `cleanup_old_temp_dirs` looks for prefix "regras_" specifically

## Testing Requirements

### Unit Tests

Create `tests/unit/test_temp_manager.py`:

```python
import pytest
import time
from pathlib import Path
from app.utils.temp_manager import (
    temp_directory,
    async_temp_directory,
    cleanup_directory,
    cleanup_old_temp_dirs,
)

def test_temp_directory_creates_and_cleans(tmp_path):
    base = tmp_path / "base"
    
    with temp_directory(str(base), prefix="test_") as temp_dir:
        assert temp_dir.exists()
        assert temp_dir.name.startswith("test_")
        (temp_dir / "file.txt").write_text("test")
    
    assert not temp_dir.exists()

def test_temp_directory_cleans_on_exception(tmp_path):
    base = tmp_path / "base"
    
    with pytest.raises(ValueError):
        with temp_directory(str(base)) as temp_dir:
            created_dir = temp_dir
            raise ValueError("test error")
    
    assert not created_dir.exists()

@pytest.mark.asyncio
async def test_async_temp_directory(tmp_path):
    base = tmp_path / "base"
    
    async with async_temp_directory(str(base)) as temp_dir:
        assert temp_dir.exists()
    
    assert not temp_dir.exists()

def test_cleanup_directory_success(tmp_path):
    target = tmp_path / "to_delete"
    target.mkdir()
    (target / "file.txt").write_text("content")
    
    result = cleanup_directory(target)
    
    assert result is True
    assert not target.exists()

def test_cleanup_directory_nonexistent(tmp_path):
    result = cleanup_directory(tmp_path / "nonexistent")
    assert result is True

def test_cleanup_old_temp_dirs(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    
    # Create "old" directory (modify mtime)
    old_dir = base / "regras_old"
    old_dir.mkdir()
    import os
    old_time = time.time() - (25 * 3600)  # 25 hours ago
    os.utime(old_dir, (old_time, old_time))
    
    # Create "new" directory
    new_dir = base / "regras_new"
    new_dir.mkdir()
    
    removed = cleanup_old_temp_dirs(str(base), max_age_hours=24)
    
    assert removed == 1
    assert not old_dir.exists()
    assert new_dir.exists()
```

## Definition of Done

- [ ] `app/utils/temp_manager.py` created
- [ ] Context managers work (sync and async)
- [ ] Cleanup functions work
- [ ] Unit tests passing
- [ ] Functions have docstrings
- [ ] Default paths updated for regras-operativas

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Direct copy with minor path changes
