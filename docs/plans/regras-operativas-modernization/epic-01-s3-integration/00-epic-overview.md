# Epic 01: S3 Integration Layer

> **Duration**: 2 weeks (2 sprints)  
> **Status**: ✅ Complete  
> **Dependencies**: None (foundational epic)

## Summary

Replace filesystem-based storage with AWS S3 for all input/output operations. This is the foundational epic that enables containerization and aligns with the flexibilizador-service architecture.

## Scope

### Included

- ✅ S3Repository implementation for download/upload operations
- ✅ Zip utilities for artifact extraction and creation
- ✅ Temporary directory lifecycle management
- ✅ S3-based Unit of Work for DECOMP and NEWAVE
- ✅ Exception hierarchy for S3 and processing errors
- ✅ Settings module with S3 configuration

### Excluded

- API changes (Epic 02)
- Health endpoints (Epic 02)
- Testing infrastructure (Epic 03)
- Docker containerization (Epic 04)

## AWS Resources

| Resource | Purpose | Configuration |
|----------|---------|---------------|
| S3 Client | Artifact I/O | boto3 with ThreadPoolExecutor |
| IAM Permissions | S3 access | GetObject, PutObject, ListBucket |

## Acceptance Criteria

- [x] S3Repository can download files from both newave-bucket and decomp-bucket
- [x] S3Repository can upload modified artifacts to S3
- [x] Zip files extracted correctly to temp directories
- [x] Zip files created with configurable compression
- [x] Temp directories cleaned up automatically on context exit
- [x] S3DecompUnitOfWork downloads deck_processado.zip and relato files
- [x] S3NewaveUnitOfWork downloads deck_processado.zip
- [x] Existing repositories work with temp directories instead of filesystem paths
- [x] All S3 errors mapped to custom exceptions
- [x] Unit tests with moto achieve >80% coverage for new code

## Technical Approach

### S3 Operations

Use boto3 synchronous client wrapped in ThreadPoolExecutor for async compatibility:

```python
class S3Repository:
    def __init__(self, region: str, endpoint_url: str | None = None):
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._client = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)
    
    async def download_file(self, bucket: str, key: str, local_path: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self._client.download_file, bucket, key, local_path)
```

### Multiple Sources Handling

Regras-operativas requires downloading multiple source cases for storage prospection:

```python
class S3DecompProspectionUnitOfWork:
    """Downloads multiple DECOMP cases for reservoir storage prospection."""
    
    def __init__(self, s3_repo: S3Repository, sources: List[CaseReference]):
        self.sources = sources
        self.temp_dirs: List[Path] = []
        self._repositories: List[RawDecompRepository] = []
    
    async def __aenter__(self):
        for source in self.sources:
            temp_dir = await self._download_and_extract(source)
            self.temp_dirs.append(temp_dir)
            self._repositories.append(RawDecompRepository(str(temp_dir)))
        return self
    
    async def __aexit__(self, *args):
        for temp_dir in self.temp_dirs:
            cleanup_directory(temp_dir)
```

## Sprints

| Sprint | Focus | Duration |
|--------|-------|----------|
| [Sprint 1](./sprint-01/) | Core S3 infrastructure (exceptions, repository, utils, settings) | 1 week |
| [Sprint 2](./sprint-02/) | Unit of Work adaptation (S3 UoW, repository modifications) | 1 week |

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `app/internal/exceptions.py` | CREATE | Custom exception hierarchy |
| `app/adapters/s3_repository.py` | CREATE | S3 operations |
| `app/utils/zip_utils.py` | CREATE | Zip extraction/creation |
| `app/utils/temp_manager.py` | CREATE | Temp directory lifecycle |
| `app/internal/settings.py` | MODIFY | Add S3 configuration |
| `app/services/unitofwork.py` | MODIFY | Add S3 variants |
| `app/adapters/decomprepository.py` | MODIFY | Work with temp dirs |
| `app/adapters/newaverepository.py` | MODIFY | Work with temp dirs |

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests passing with >80% coverage for new code
- [ ] Integration tests with moto passing
- [ ] Code follows existing project patterns
- [ ] No hardcoded credentials or paths
- [ ] All new code has docstrings
