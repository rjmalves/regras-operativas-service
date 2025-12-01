# [TICKET-030] Create CHANGELOG.md and release

> **Epic**: [Epic 05: Documentation & Release](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: All other tickets complete  
> **Blocks**: None

## Context

### Background

Create CHANGELOG.md documenting all changes in v2.0.0 and prepare the release (git tag, release notes).

### Current State

No changelog exists.

## Specification

### Files to Create/Update

1. `CHANGELOG.md` - Version history
2. Git tag `v2.0.0`
3. GitHub release (if applicable)

### CHANGELOG.md Content

```markdown
# Changelog

All notable changes to regras-operativas-service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2024-XX-XX

### Added

- **S3 Integration**: Read/write artifacts from S3 buckets instead of filesystem
  - New `S3Repository` adapter for all S3 operations
  - Support for MinIO and LocalStack for development
  - Configurable bucket names via environment variables

- **Health Endpoints**: Kubernetes-ready probes
  - `GET /health/live` - Liveness probe
  - `GET /health/ready` - Readiness probe with S3 connectivity check
  - `GET /health/version` - Service version information

- **Docker Support**: Full containerization
  - Multi-stage Dockerfile with uv for fast builds
  - Docker Compose for production deployment
  - Docker Compose development setup with LocalStack
  - Image size < 200MB

- **systemd Integration**: Production service management
  - systemd service unit file
  - Install/uninstall/upgrade scripts
  - Automatic restart on failure

- **Testing Infrastructure**: Comprehensive test suite
  - pytest with moto for S3 mocking
  - Unit tests for all components
  - Integration tests for API endpoints
  - >80% code coverage target

- **Modern Python Tooling**:
  - `pyproject.toml` for dependency management
  - `uv` for fast package installation
  - `ruff` for linting and formatting
  - `mypy` for type checking

- **Structured Error Handling**:
  - Custom exception hierarchy
  - Standardized error response format with error codes
  - Detailed error messages with context

- **Documentation**:
  - Updated README.md with v2.0 API
  - MIGRATION.md for v1.x to v2.0 migration
  - DEPLOYMENT.md for production deployment

### Changed

- **BREAKING**: Request format changed from base62-encoded paths to S3 bucket + execution_hash
  ```json
  // Old
  {"sources": [{"id": "base62EncodedPath...", "program": "DECOMP"}]}
  
  // New
  {"sources": [{"bucket": "decomp-bucket", "execution_hash": "abc123", "program": "DECOMP"}]}
  ```

- **BREAKING**: Response format changed to include more metadata
  ```json
  // Old
  {"result": [...]}
  
  // New
  {"success": true, "execution_hash": "...", "output_key": "...", "rules_applied": [...]}
  ```

- **BREAKING**: Default port changed from 5054 to 8000

- **BREAKING**: Deployment method changed from PM2 to Docker Compose

- Refactored Unit of Work pattern to support S3-based workflows
- Updated DECOMP and NEWAVE repositories to work with temporary directories
- Modernized settings management using pydantic-settings

### Removed

- Filesystem-based artifact storage
- base62 path encoding/decoding
- PM2 process management
- `ecosystem.config.js` configuration
- `requirements.txt` (replaced by pyproject.toml)
- `CLUSTER_ID` configuration (no longer needed)

### Security

- Container runs as non-root user (uid 1000)
- No hardcoded credentials
- Least-privilege IAM policy documented

### Fixed

- Improved error handling for missing artifacts
- Better cleanup of temporary directories
- More robust zip file handling

## [1.x.x] - Previous Versions

Legacy versions using PM2 and filesystem storage. See git history for details.

---

[Unreleased]: https://github.com/your-org/regras-operativas-service/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/your-org/regras-operativas-service/releases/tag/v2.0.0
```

### Release Checklist

Before creating the release:

- [ ] All tickets in this plan are complete
- [ ] All tests pass: `uv run pytest`
- [ ] Coverage ≥ 80%: `uv run pytest --cov=app`
- [ ] Linting passes: `uv run ruff check app/`
- [ ] Type checking passes: `uv run mypy app/`
- [ ] Docker build succeeds: `docker compose build`
- [ ] Container starts and health checks pass
- [ ] Documentation reviewed and accurate
- [ ] CHANGELOG.md has correct date

### Git Tag Commands

```bash
# Ensure you're on main branch with all changes
git checkout main
git pull origin main

# Verify everything is committed
git status

# Create annotated tag
git tag -a v2.0.0 -m "Release v2.0.0: S3 integration, Docker deployment"

# Push tag
git push origin v2.0.0
```

### GitHub Release (if applicable)

1. Go to repository releases page
2. Click "Create a new release"
3. Select tag `v2.0.0`
4. Title: `v2.0.0 - S3 Integration & Docker Deployment`
5. Description: Copy relevant sections from CHANGELOG.md
6. Attach artifacts if needed (none for this service)
7. Publish release

## Acceptance Criteria

- [ ] CHANGELOG.md created with v2.0.0 changes
- [ ] All breaking changes clearly marked
- [ ] Changelog follows Keep a Changelog format
- [ ] Git tag v2.0.0 created
- [ ] Release notes complete
- [ ] Date updated in CHANGELOG.md

## Implementation Guide

### Step 1: Verify All Work Complete

Run through the release checklist above.

### Step 2: Create CHANGELOG.md

Create the file with content above, updating the date.

### Step 3: Final Review

```bash
# Run all checks
uv run pytest --cov=app
uv run ruff check app/
uv run mypy app/
docker compose build
docker compose up -d
curl http://localhost:8000/health/live
docker compose down
```

### Step 4: Commit CHANGELOG

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG.md for v2.0.0 release"
git push origin main
```

### Step 5: Create Tag

```bash
git tag -a v2.0.0 -m "Release v2.0.0: S3 integration, Docker deployment"
git push origin v2.0.0
```

### Step 6: Create GitHub Release (optional)

Follow the GitHub release instructions above.

## Definition of Done

- [ ] CHANGELOG.md created
- [ ] All checks pass
- [ ] Git tag created
- [ ] Tag pushed to remote
- [ ] Release created (if applicable)

## Effort Estimate

**Points**: 1  
**Confidence**: High  
**Rationale**: Documentation and git operations, straightforward
