# Sprint 02: Unit of Work Adaptation

> **Epic**: [Epic 01: S3 Integration Layer](../00-epic-overview.md)  
> **Duration**: 1 week  
> **Status**: ✅ Complete

## Goals

1. ✅ Create S3-based Unit of Work for DECOMP (with prospection support)
2. ✅ Create S3-based Unit of Work for NEWAVE
3. ✅ Adapt existing repositories to work with temp directories
4. ✅ Enable multi-source downloads for reservoir storage prospection

## Tickets

| ID | Title | Points | Dependencies | Status |
|----|-------|--------|--------------|--------|
| [TICKET-006](./ticket-006-create-s3-decomp-uow.md) | Create S3DecompUnitOfWork | 5 | TICKET-002, TICKET-003, TICKET-004 | ✅ Done |
| [TICKET-007](./ticket-007-create-s3-newave-uow.md) | Create S3NewaveUnitOfWork | 3 | TICKET-002, TICKET-003, TICKET-004 | ✅ Done |
| [TICKET-008](./ticket-008-adapt-decomp-repository.md) | Adapt DECOMP repository for temp dirs | 3 | None | ✅ Done (no changes needed) |
| [TICKET-009](./ticket-009-adapt-newave-repository.md) | Adapt NEWAVE repository for temp dirs | 2 | None | ✅ Done (no changes needed) |

**Total Points**: 13

## Dependencies

- **From Sprint 01**: TICKET-002 (S3Repository), TICKET-003 (zip_utils), TICKET-004 (temp_manager)
- **To Epic 02**: Enables router to use S3-based workflow

## Key Design Decision: Multi-Source Handling

Unlike flexibilizador (single source), regras-operativas needs to download multiple DECOMP cases for prospection (reading reservoir storage from previous executions):

```python
class S3DecompProspectionUnitOfWork:
    """Downloads multiple DECOMP cases for prospection."""
    
    def __init__(self, s3_repo: S3Repository, sources: List[CaseReference]):
        self.sources = sources
        self.temp_dirs: List[Path] = []
        self._repositories: List[RawDecompRepository] = []
    
    @property
    def repositories(self) -> List[RawDecompRepository]:
        """Access to all source repositories for prospection."""
        return self._repositories
```

## Files Delivered

| File | Description | Status |
|------|-------------|--------|
| `app/services/unitofwork.py` | S3-based Unit of Work classes | ✅ Updated |
| `app/adapters/decomprepository.py` | Already accepts directory path | ✅ No changes needed |
| `app/adapters/newaverepository.py` | Already accepts directory path | ✅ No changes needed |
| `tests/integration/test_s3_unitofwork.py` | Integration tests | ✅ Created |

## Definition of Done

- [x] All 4 tickets complete
- [x] S3 download → extract → process → upload flow works
- [x] Multi-source prospection supported
- [x] Integration tests with moto passing (9 tests)
- [x] Cleanup on normal exit and exceptions
