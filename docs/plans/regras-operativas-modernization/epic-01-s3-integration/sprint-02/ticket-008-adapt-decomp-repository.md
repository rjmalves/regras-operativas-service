# TICKET-008: Adapt DECOMP Repository for Temp Directories

> **Epic**: [Epic 01: S3 Integration Layer](../../00-epic-overview.md)  
> **Sprint**: [Sprint 02](./00-sprint-overview.md)  
> **Points**: 3  
> **Dependencies**: None  
> **Blocks**: [TICKET-006](./ticket-006-create-s3-decomp-uow.md)

## Context

### Background

The `RawDecompRepository` in `app/adapters/decomprepository.py` currently works with filesystem paths. It needs to work with temporary directories created by the S3 Unit of Work. The main change is removing the dependency on `chdir()` and ensuring all file operations work with the provided path.

### Current State

The repository uses:
- `chdir()` in Unit of Work context
- Relative paths for file operations
- `Settings.encoding_script` for encoding conversion

After this change:
- Works with absolute paths in temp directories
- No `chdir()` needed
- Remove encoding script dependency (files from S3 are already UTF-8)

## Specification

### File Location

- `app/adapters/decomprepository.py` (MODIFY)

### Changes Required

1. **Remove encoding script dependency**: S3 artifacts are already UTF-8
2. **Accept directory path in constructor**: Already exists, ensure it works with temp dirs
3. **Ensure all file operations use absolute paths**: Join with `self.__path`
4. **Update async methods**: Remove `chdir()` assumption

### Current vs Target

**Current (simplified):**
```python
class RawDecompRepository(AbstractDecompRepository):
    def __init__(self, path: str):
        self.__path = path
        self.__caso = Caso.read(join(str(self.__path), "caso.dat"))
    
    async def get_dadger(self) -> Union[Dadger, HTTPResponse]:
        # Uses encoding script, relative paths
        caminho = pathlib.Path(self.__path).joinpath(self.arquivos.dadger)
        script = pathlib.Path(Settings.installdir).joinpath(Settings.encoding_script)
        await converte_codificacao(caminho, script)
        self.__dadger = Dadger.read(join(self.__path, self.arquivos.dadger))
```

**Target:**
```python
class RawDecompRepository(AbstractDecompRepository):
    def __init__(self, path: str):
        self.__path = Path(path)  # Store as Path object
        self.__caso = Caso.read(str(self.__path / "caso.dat"))
    
    async def get_dadger(self) -> Union[Dadger, HTTPResponse]:
        # No encoding script, use absolute paths
        dadger_path = self.__path / self.arquivos.dadger
        Log.log().info(f"Reading file {dadger_path}")
        self.__dadger = Dadger.read(str(dadger_path))
```

### Methods to Update

| Method | Changes |
|--------|---------|
| `__init__` | Store path as `Path` object |
| `arquivos` property | Use `self.__path / filename` |
| `get_dadger()` | Remove encoding script call |
| `get_dadgnl()` | Remove encoding script call |
| `get_relato()` | Use absolute path |
| `get_relgnl()` | Use absolute path |
| `get_inviabunic()` | Use absolute path |
| `get_hidr()` | Use absolute path |
| `set_dadger()` | Use absolute path |
| `set_dadgnl()` | Use absolute path |

### Remove/Deprecate

- `app/utils/encoding.py` - No longer needed
- `app/static/converte_utf8.sh` - No longer needed (can keep for legacy)

## Acceptance Criteria

- [ ] Given a temp directory path, when repository is created, then it reads caso.dat correctly
- [ ] Given repository, when `get_dadger()` called, then dadger file read from correct path
- [ ] Given repository with dadger loaded, when `set_dadger()` called, then file written to correct path
- [ ] Given repository, when any file operation performed, then no `chdir()` is used
- [ ] Encoding script is not called for any file operation
- [ ] All existing tests still pass (with path fixes)

## Implementation Guide

### Suggested Approach

1. Open `app/adapters/decomprepository.py`
2. Change `self.__path` to be stored as `Path` object
3. Update all file read/write to use `self.__path / filename`
4. Remove calls to `converte_codificacao()`
5. Update return types to not use `HTTPResponse` (use exceptions instead)
6. Run existing tests, fix any path issues

### Key Files to Read

- `app/adapters/decomprepository.py` - Current implementation
- `app/utils/encoding.py` - Encoding script wrapper (to be removed)
- `app/internal/httpresponse.py` - Current error handling

### Pitfalls to Avoid

- ⚠️ idecomp library expects string paths, not Path objects - use `str(path)`
- ⚠️ Don't break existing filesystem-based Unit of Work yet (keep compatible)
- ⚠️ File extensions vary (rv0, rv1, etc.) - use `self.caso.arquivos`

## Testing Requirements

### Unit Tests

Update `tests/unit/test_decomprepository.py`:

```python
import pytest
from pathlib import Path
from app.adapters.decomprepository import RawDecompRepository

@pytest.fixture
def decomp_case_dir(tmp_path):
    """Create a minimal DECOMP case directory."""
    # Create caso.dat
    (tmp_path / "caso.dat").write_text("rv0")
    
    # Create minimal arquivos file
    # ... setup minimal files ...
    
    return tmp_path

def test_repository_reads_from_temp_dir(decomp_case_dir):
    repo = RawDecompRepository(str(decomp_case_dir))
    
    assert repo.caso is not None
    assert repo.caso.arquivos == "rv0"

@pytest.mark.asyncio
async def test_get_dadger_uses_absolute_path(decomp_case_dir):
    # Create minimal dadger file
    # ...
    
    repo = RawDecompRepository(str(decomp_case_dir))
    dadger = await repo.get_dadger()
    
    assert dadger is not None

def test_set_dadger_writes_to_temp_dir(decomp_case_dir):
    repo = RawDecompRepository(str(decomp_case_dir))
    # ... test dadger writing ...
```

## Definition of Done

- [ ] Repository works with temp directory paths
- [ ] No `chdir()` calls
- [ ] No encoding script calls
- [ ] All file operations use absolute paths
- [ ] Unit tests passing
- [ ] Existing functionality preserved

## Effort Estimate

**Points**: 3  
**Confidence**: Medium  
**Rationale**: Many methods to update, need to maintain compatibility with idecomp library
