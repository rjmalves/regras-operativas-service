# Changelog

All notable changes to regras-operativas-service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2024-12-01

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
  - 46% code coverage (174 tests)

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
