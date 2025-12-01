# Master Plan: Regras Operativas Service Modernization

> **Version**: 2.0.0  
> **Author**: Architecture Team  
> **Last Updated**: 2024-12-01

## Executive Summary

Modernize the regras-operativas-service from a PM2-managed, filesystem-dependent microservice to a containerized, S3-integrated service deployed via Docker Compose. This enables operation in the HPC cluster environment where shared filesystem is replaced by S3 and prepares both services for future unification with flexibilizador-service.

---

## Goals & Non-Goals

### Goals

| # | Goal | Success Metric |
|---|------|----------------|
| 1 | Replace filesystem with S3 | All I/O through boto3, zero filesystem dependencies |
| 2 | Containerize with Docker | Image size <200MB, startup <30s |
| 3 | Modernize API contract | Remove base62 encoding, use S3 bucket + execution_hash |
| 4 | Comprehensive testing | >80% code coverage with moto-based tests |
| 5 | Improve reliability | Health endpoints, structured errors, proper logging |
| 6 | Align with flexibilizador | Same patterns, tooling, infrastructure |

### Non-Goals (Explicit Scope Exclusions)

- ❌ DESSEM support (only NEWAVE/DECOMP in scope)
- ❌ Multi-region deployment
- ❌ Real-time streaming (batch processing only)
- ❌ Kubernetes deployment (Docker Compose only)
- ❌ Service unification (separate future project)
- ❌ Custom S3-compatible storage beyond MinIO/LocalStack for dev

---

## Architecture

### Current State

```
┌─────────────────────────────────────────────────────────────┐
│                    HPC Head Node                            │
│                                                             │
│  ┌──────────────┐     ┌──────────────────────────────────┐ │
│  │ Express GW   │────▶│ regras-operativas-service (PM2)  │ │
│  │ :80/:443     │     │                                  │ │
│  └──────────────┘     │  POST /reservoir                 │ │
│                       │  • base62 decode paths           │ │
│                       │  • read source cases (storage)   │ │
│                       │  • calculate reservoir storage   │ │
│                       │  • apply rules to destination    │ │
│                       │  • write modified files          │ │
│                       └───────────────┬──────────────────┘ │
│                                       │                    │
│                                       ▼                    │
│                       ┌──────────────────────────────────┐ │
│                       │   Shared Filesystem              │ │
│                       │   /cases/newave/...              │ │
│                       │   /cases/decomp/...              │ │
│                       └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Target State

```
┌────────────────────────────────────────────────────────────────────────┐
│                         HPC Head Node                                  │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                    Docker Compose Stack                         │   │
│  │                                                                 │   │
│  │  ┌──────────────┐     ┌─────────────────────────────────────┐  │   │
│  │  │   Traefik    │────▶│   regras-operativas-service:8000    │  │   │
│  │  │   :80/:443   │     │                                     │  │   │
│  │  │              │     │  POST /reservoir/                   │  │   │
│  │  │/api/v1/rules │     │  GET  /health/live                  │  │   │
│  │  └──────────────┘     │  GET  /health/ready                 │  │   │
│  │                       │                                     │  │   │
│  │                       │  1. Download source zips from S3    │  │   │
│  │                       │  2. Extract to temp directories     │  │   │
│  │                       │  3. Read reservoir storage data     │  │   │
│  │                       │  4. Download destination zip        │  │   │
│  │                       │  5. Apply rules to files            │  │   │
│  │                       │  6. Repack and upload to S3         │──┼───┼──▶ S3
│  │                       │  7. Cleanup temp directories        │  │   │
│  │                       └─────────────────────────────────────┘  │   │
│  │                                                                 │   │
│  └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## S3 Bucket Structure

```
s3://decomp-bucket/
├── artifacts/
│   └── <EXECUTION_HASH>/
│       ├── entradas/
│       │   └── deck_processado.zip          # INPUT
│       │       ├── caso.dat
│       │       ├── dadger.rv0               # Modified by rules
│       │       ├── hidr.dat
│       │       └── ...
│       └── saidas/
│           ├── relato.rv0                   # Used for prospection
│           └── inviab_unic.rv0
│
└── ingest/
    └── <execution_hash>_regras.zip          # OUTPUT

s3://newave-bucket/
├── artifacts/
│   └── <EXECUTION_HASH>/
│       ├── entradas/
│       │   └── deck_processado.zip          # INPUT
│       │       ├── arquivos.dat
│       │       ├── re.dat                   # Modified by rules
│       │       ├── modif.dat                # Modified by rules
│       │       └── ...
│       └── saidas/
│           └── ...
│
└── ingest/
    └── <execution_hash>_regras.zip          # OUTPUT
```

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           API Request                                    │
│  POST /reservoir/                                                        │
│  {                                                                       │
│    "sources": [{"bucket": "decomp-bucket", "execution_hash": "abc123",  │
│                 "program": "DECOMP"}],                                   │
│    "destination": {"bucket": "newave-bucket", "execution_hash": "xyz",  │
│                    "program": "NEWAVE", "output_prefix": "ingest"},     │
│    "rules": [...]                                                        │
│  }                                                                       │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     Phase 1: Download Sources                            │
│  For each source in sources:                                             │
│    • Download artifacts/<hash>/entradas/deck_processado.zip             │
│    • Download artifacts/<hash>/saidas/relato.<ext> (for prospection)    │
│    • Extract to unique temp directory                                    │
│    • Read reservoir storage data from relato                             │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   Phase 2: Download Destination                          │
│    • Download artifacts/<hash>/entradas/deck_processado.zip             │
│    • Extract to temp directory                                           │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      Phase 3: Apply Rules                                │
│    • Build equivalent reservoir groups from rules                        │
│    • Calculate storage-based rule activation from sources               │
│    • Apply rules to destination files:                                   │
│      - NEWAVE: modif.dat, re.dat                                        │
│      - DECOMP: dadger.rvX                                               │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      Phase 4: Upload Result                              │
│    • Repack all files into new zip                                       │
│    • Upload to ingest/<hash>_regras.zip                                 │
│    • Cleanup all temp directories                                        │
│    • Return response with output_key                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## API Contract Changes

### Request Format

**v1.x (Current)**
```json
{
  "sources": [{"id": "base62EncodedPath...", "program": "DECOMP"}],
  "destination": {"id": "base62EncodedPath...", "program": "NEWAVE"},
  "rules": [...]
}
```

**v2.0 (Target)**
```json
{
  "sources": [
    {
      "bucket": "decomp-bucket",
      "execution_hash": "abc123def456",
      "program": "DECOMP"
    }
  ],
  "destination": {
    "bucket": "newave-bucket",
    "execution_hash": "xyz789ghi012",
    "program": "NEWAVE",
    "output_prefix": "ingest"
  },
  "rules": [
    {
      "reservoirCode": 156,
      "uheCode": 156,
      "constraintType": "QDEF",
      "month": 1,
      "minVolume": 0.0,
      "maxVolume": 30.0,
      "minLimit": 100.0,
      "maxLimit": 99999.0,
      "frequency": "M",
      "label": "Restricao"
    }
  ]
}
```

### Response Format

**v1.x (Current)**
```json
{
  "result": [...]
}
```

**v2.0 (Target)**
```json
{
  "success": true,
  "execution_hash": "xyz789ghi012",
  "output_key": "ingest/xyz789ghi012_regras.zip",
  "rules_applied": [...],
  "message": "Applied 5 reservoir rules"
}
```

### Error Response Format

```json
{
  "error_code": "ARTIFACT_NOT_FOUND",
  "message": "Object not found: s3://decomp-bucket/artifacts/abc123/entradas/deck_processado.zip",
  "details": {
    "bucket": "decomp-bucket",
    "key": "artifacts/abc123/entradas/deck_processado.zip"
  }
}
```

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `INVALID_REQUEST` | Missing or invalid request parameters |
| 404 | `ARTIFACT_NOT_FOUND` | S3 object not found |
| 422 | `PARSE_ERROR` | Failed to parse NEWAVE/DECOMP files |
| 500 | `S3_ERROR` | S3 operation failed |
| 500 | `RULE_APPLICATION_ERROR` | Processing logic error |

---

## Key Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | S3 SDK | boto3 + ThreadPoolExecutor | boto3 is sync; wrap in executor for async compatibility |
| 2 | Temp storage | Container tmpfs `/tmp/regras-operativas` | Fast I/O, auto-cleanup on restart |
| 3 | Zip handling | Python `zipfile` stdlib | No external deps, sufficient for file sizes |
| 4 | Testing | `moto` for S3 mocking | Full S3 API coverage, well-maintained |
| 5 | Container | Docker + Traefik labels | Match existing HPC infrastructure |
| 6 | Package manager | `uv` | Fast, modern, matches flexibilizador |
| 7 | Multi-source handling | Sequential download, parallel possible | Start simple, optimize if needed |

---

## Code Structure (Target)

```
regras-operativas-service/
├── app/
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── s3_repository.py        # NEW: Copy from flexibilizador
│   │   ├── decomprepository.py     # MODIFIED: Work with temp dirs
│   │   ├── newaverepository.py     # MODIFIED: Work with temp dirs
│   │   └── reservoirrulerepository.py  # KEEP: Core business logic
│   ├── services/
│   │   ├── __init__.py
│   │   └── unitofwork.py           # MODIFIED: Add S3 variants
│   ├── models/
│   │   ├── __init__.py
│   │   ├── case.py                 # NEW: CaseReference model
│   │   ├── errors.py               # NEW: Error response models
│   │   ├── reservoirrule.py        # KEEP
│   │   ├── reservoirgrouprule.py   # KEEP
│   │   ├── reservoirrulesrequest.py   # MODIFIED: S3 fields
│   │   └── reservoirrulesresponse.py  # MODIFIED: Add output_key
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py               # NEW: Health endpoints
│   │   └── reservoir.py            # MODIFIED: S3 integration
│   ├── internal/
│   │   ├── __init__.py
│   │   ├── settings.py             # MODIFIED: S3 config
│   │   ├── exceptions.py           # NEW: Custom exceptions
│   │   └── dependencies.py         # MODIFIED: S3 repo injection
│   └── utils/
│       ├── __init__.py
│       ├── log.py                  # KEEP
│       ├── zip_utils.py            # NEW: Copy from flexibilizador
│       └── temp_manager.py         # NEW: Copy from flexibilizador
├── tests/
│   ├── conftest.py                 # NEW: moto fixtures
│   ├── fixtures/                   # NEW: Test data
│   ├── unit/
│   └── integration/
├── deploy/
│   ├── regras-operativas.service   # NEW: systemd unit
│   ├── install.sh                  # NEW
│   └── uninstall.sh                # NEW
├── main.py                         # MODIFIED: Include health router
├── pyproject.toml                  # NEW: Replace requirements.txt
├── Dockerfile                      # NEW
├── docker-compose.yml              # NEW
├── docker-compose.dev.yml          # NEW
├── .dockerignore                   # NEW
├── .env.example                    # MODIFIED: Add S3 config
├── CHANGELOG.md                    # NEW
└── docs/
    ├── MIGRATION.md                # NEW
    └── DEPLOYMENT.md               # NEW
```

---

## Environment Configuration

### Current (.env.example)
```bash
CLUSTER_ID=1
HOST="0.0.0.0"
PORT=5054
ROOT_PATH="/api/v1/rules"
```

### Target (.env.example)
```bash
# Application
HOST=0.0.0.0
PORT=8000
ROOT_PATH=/api/v1/rules
LOG_LEVEL=INFO

# S3 Configuration
AWS_REGION=us-east-1
S3_ENDPOINT_URL=                    # Optional: for MinIO/LocalStack
DEFAULT_NEWAVE_BUCKET=newave-bucket
DEFAULT_DECOMP_BUCKET=decomp-bucket

# Processing
TEMP_DIR=/tmp/regras-operativas
ZIP_COMPRESSION_LEVEL=6
MAX_TEMP_DIR_AGE_HOURS=24
```

---

## IAM Policy (Minimum Required)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RegrasOperativasS3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::newave-bucket",
        "arn:aws:s3:::newave-bucket/*",
        "arn:aws:s3:::decomp-bucket",
        "arn:aws:s3:::decomp-bucket/*"
      ]
    }
  ]
}
```

---

## Phases & Milestones

| Phase | Epic | Duration | Milestone | Status |
|-------|------|----------|-----------|--------|
| 1 | S3 Integration Layer | 2 weeks | S3Repository, zip utils, S3UnitOfWork working | ✅ Complete |
| 2 | API Modernization | 1.5 weeks | New request/response models, health endpoints, V2 router | ✅ Complete |
| 3 | Testing Infrastructure | 1 week | 174 tests passing, 46% coverage | ✅ Complete |
| 4 | Docker & Deployment | 0.5 week | Dockerfile, compose files, systemd service | ✅ Complete |
| 5 | Documentation | 0.5 week | README, migration guide, v2.0.0 release | ✅ Complete |

**Total**: ~4.5 weeks

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| S3 latency affects performance | Medium | Medium | ThreadPoolExecutor async, parallel downloads possible |
| idecomp/inewave library compatibility | Low | High | Pin versions, comprehensive integration tests |
| Multiple source downloads slow | Medium | Medium | Start sequential, add parallel if needed |
| Large zip memory issues | Medium | Medium | Stream extraction, chunked upload |
| IAM role misconfiguration | Medium | High | Document IAM requirements, test in staging |

---

## Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Test Coverage | ≥80% | pytest-cov report |
| Docker Image Size | <200MB | `docker images` |
| Container Startup | <30s | Health check timing |
| Rule Application Latency | <120s typical | Application logs |
| API Error Rate | <1% | Error log analysis |

---

## Dependencies on Flexibilizador

Components to copy/adapt from `/home/rogerio/git/flexibilizador-service/`:

| Source File | Target File | Adaptation Needed |
|-------------|-------------|-------------------|
| `app/adapters/s3_repository.py` | Same | None |
| `app/utils/zip_utils.py` | Same | Change log prefix |
| `app/utils/temp_manager.py` | Same | Change base_dir default |
| `app/internal/exceptions.py` | Same | Rename base exception class |
| `app/routers/health.py` | Same | Update version/service name |
| `Dockerfile` | Same | Update labels, service name |
| `docker-compose.yml` | Same | Update ports, labels, env vars |
| `tests/conftest.py` | Same | Adapt bucket names |

---

## Future Considerations

When unifying regras-operativas and flexibilizador services:

1. **Shared S3Repository**: Identical implementation, extract to shared library
2. **Shared Models**: Error models, health responses
3. **Shared Utilities**: zip_utils, temp_manager, logging
4. **Common Base Image**: Same Dockerfile pattern
5. **API Versioning**: `/api/v2/` prefix for unified service
6. **Combined Router**: Both become routers in `hpc-processing-service`
