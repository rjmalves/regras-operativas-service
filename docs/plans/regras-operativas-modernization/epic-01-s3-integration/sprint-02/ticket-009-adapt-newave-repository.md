# TICKET-009: Adapt NEWAVE Repository for Temp Directories

> **Epic**: [Epic 01: S3 Integration Layer](../../00-epic-overview.md)  
> **Sprint**: [Sprint 02](./00-sprint-overview.md)  
> **Points**: 2  
> **Dependencies**: None  
> **Blocks**: [TICKET-007](./ticket-007-create-s3-newave-uow.md)

## Context

### Background

The `RawNewaveRepository` in `app/adapters/newaverepository.py` needs to work with temporary directories. Similar changes to DECOMP repository are needed.

### Current State

The repository likely uses filesystem paths and may have encoding conversion. Needs to work with absolute paths in temp directories.

## Specification

### File Location

- `app/adapters/newaverepository.py` (MODIFY)

### Changes Required

1. Store path as `Path` object
2. Use absolute paths for all file operations
3. Remove encoding script dependency if present
4. Ensure compatibility with inewave library

### Methods to Update (Common Pattern)

```python
class RawNewaveRepository(AbstractNewaveRepository):
    def __init__(self, path: str):
        self.__path = Path(path)  # Store as Path
        # Read arquivos.dat or similar config
    
    def get_re(self) -> RE:
        """Read re.dat file."""
        re_path = self.__path / "re.dat"
        return RE.read(str(re_path))
    
    def set_re(self, re: RE) -> None:
        """Write re.dat file."""
        re_path = self.__path / "re.dat"
        re.write(str(re_path))
    
    def get_modif(self) -> Modif:
        """Read modif.dat file."""
        modif_path = self.__path / "modif.dat"
        return Modif.read(str(modif_path))
    
    def set_modif(self, modif: Modif) -> None:
        """Write modif.dat file."""
        modif_path = self.__path / "modif.dat"
        modif.write(str(modif_path))
```

### NEWAVE Files for Rules

| File | Purpose | inewave Class |
|------|---------|---------------|
| `re.dat` | Reservoir restrictions | `RE` |
| `modif.dat` | Modifications | `Modif` |
| `arquivos.dat` | File configuration | `Arquivos` |

## Acceptance Criteria

- [ ] Given a temp directory path, when repository is created, then it initializes correctly
- [ ] Given repository, when `get_re()` called, then re.dat read from correct path
- [ ] Given repository, when `set_re()` called, then re.dat written to correct path
- [ ] Given repository, when `get_modif()` called, then modif.dat read correctly
- [ ] All file operations use absolute paths (no `chdir()`)
- [ ] Existing tests pass

## Implementation Guide

### Suggested Approach

1. Open `app/adapters/newaverepository.py`
2. Review current implementation
3. Apply same pattern as DECOMP repository (TICKET-008)
4. Update all file operations to use `self.__path / filename`
5. Run existing tests

### Key Files to Read

- `app/adapters/newaverepository.py` - Current implementation
- [TICKET-008](./ticket-008-adapt-decomp-repository.md) - Similar DECOMP changes

### Pitfalls to Avoid

- ⚠️ inewave library expects string paths - use `str(path)`
- ⚠️ NEWAVE file structure differs from DECOMP

## Testing Requirements

### Unit Tests

```python
import pytest
from pathlib import Path
from app.adapters.newaverepository import RawNewaveRepository

@pytest.fixture
def newave_case_dir(tmp_path):
    """Create minimal NEWAVE case directory."""
    # Create arquivos.dat
    (tmp_path / "arquivos.dat").write_text("...")
    # Create minimal required files
    return tmp_path

def test_repository_with_temp_dir(newave_case_dir):
    repo = RawNewaveRepository(str(newave_case_dir))
    assert repo is not None

def test_get_set_re(newave_case_dir):
    # Create minimal re.dat
    (newave_case_dir / "re.dat").write_text("...")
    
    repo = RawNewaveRepository(str(newave_case_dir))
    re_data = repo.get_re()
    # Modify and write back
    repo.set_re(re_data)
```

## Definition of Done

- [ ] Repository works with temp directory paths
- [ ] No `chdir()` calls
- [ ] All file operations use absolute paths
- [ ] Unit tests passing
- [ ] Existing functionality preserved

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Same pattern as DECOMP, simpler interface
