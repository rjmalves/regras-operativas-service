# TICKET-005: Update Settings with S3 Configuration

> **Epic**: [Epic 01: S3 Integration Layer](../../00-epic-overview.md)  
> **Sprint**: [Sprint 01](./00-sprint-overview.md)  
> **Points**: 2  
> **Dependencies**: None  
> **Blocks**: [TICKET-002](./ticket-002-implement-s3-repository.md)

## Context

### Background

The settings module needs to be updated to include S3 configuration (region, endpoint URL, bucket names) and other new settings (temp directory, log level). This enables configuration via environment variables for different environments (dev with LocalStack, prod with real S3).

### Current State

Current `app/internal/settings.py` has basic settings:
- `clusterId`, `basedir`, `installdir`
- `host`, `port`, `root_path`
- `encoding_script`, `uri_pattern`

## Specification

### File Location

- `app/internal/settings.py` (MODIFY)

### New Settings Structure

```python
import os
from typing import Optional

class Settings:
    """Application settings loaded from environment variables."""
    
    # Application
    host: str = "0.0.0.0"
    port: int = 8000
    root_path: str = "/api/v1/rules"
    log_level: str = "INFO"
    
    # Paths
    basedir: Optional[str] = None
    installdir: Optional[str] = None
    
    # S3 Configuration
    aws_region: str = "us-east-1"
    s3_endpoint_url: Optional[str] = None  # None for real AWS, URL for LocalStack
    default_newave_bucket: str = "newave-bucket"
    default_decomp_bucket: str = "decomp-bucket"
    
    # Processing
    temp_dir: str = "/tmp/regras-operativas"
    zip_compression_level: int = 6
    max_temp_dir_age_hours: int = 24

    @classmethod
    def read_environments(cls) -> None:
        """Load settings from environment variables."""
        # Application
        cls.host = os.getenv("HOST", "0.0.0.0")
        cls.port = int(os.getenv("PORT", "8000"))
        cls.root_path = os.getenv("ROOT_PATH", "/api/v1/rules")
        cls.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Paths
        cls.basedir = os.getenv("APP_BASEDIR")
        cls.installdir = os.getenv("APP_INSTALLDIR")
        
        # S3 Configuration
        cls.aws_region = os.getenv("AWS_REGION", "us-east-1")
        cls.s3_endpoint_url = os.getenv("S3_ENDPOINT_URL") or None
        cls.default_newave_bucket = os.getenv("DEFAULT_NEWAVE_BUCKET", "newave-bucket")
        cls.default_decomp_bucket = os.getenv("DEFAULT_DECOMP_BUCKET", "decomp-bucket")
        
        # Processing
        cls.temp_dir = os.getenv("TEMP_DIR", "/tmp/regras-operativas")
        cls.zip_compression_level = int(os.getenv("ZIP_COMPRESSION_LEVEL", "6"))
        cls.max_temp_dir_age_hours = int(os.getenv("MAX_TEMP_DIR_AGE_HOURS", "24"))
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `ROOT_PATH` | `/api/v1/rules` | FastAPI root path for proxying |
| `LOG_LEVEL` | `INFO` | Logging level |
| `AWS_REGION` | `us-east-1` | AWS region for S3 |
| `S3_ENDPOINT_URL` | None | Custom S3 endpoint (LocalStack/MinIO) |
| `DEFAULT_NEWAVE_BUCKET` | `newave-bucket` | Default NEWAVE bucket |
| `DEFAULT_DECOMP_BUCKET` | `decomp-bucket` | Default DECOMP bucket |
| `TEMP_DIR` | `/tmp/regras-operativas` | Base temp directory |
| `ZIP_COMPRESSION_LEVEL` | `6` | Compression (0-9) |
| `MAX_TEMP_DIR_AGE_HOURS` | `24` | Age for orphan cleanup |

### Update .env.example

```bash
# Application
HOST=0.0.0.0
PORT=8000
ROOT_PATH=/api/v1/rules
LOG_LEVEL=INFO

# S3 Configuration
AWS_REGION=us-east-1
S3_ENDPOINT_URL=                    # Empty for real AWS, http://localhost:4566 for LocalStack
DEFAULT_NEWAVE_BUCKET=newave-bucket
DEFAULT_DECOMP_BUCKET=decomp-bucket

# Processing
TEMP_DIR=/tmp/regras-operativas
ZIP_COMPRESSION_LEVEL=6
MAX_TEMP_DIR_AGE_HOURS=24
```

## Acceptance Criteria

- [ ] Given no environment variables, when `read_environments()` is called, then defaults are used
- [ ] Given `AWS_REGION=sa-east-1`, when `read_environments()` is called, then `Settings.aws_region == "sa-east-1"`
- [ ] Given `S3_ENDPOINT_URL=http://localhost:4566`, when `read_environments()` is called, then `Settings.s3_endpoint_url == "http://localhost:4566"`
- [ ] Given empty `S3_ENDPOINT_URL`, when `read_environments()` is called, then `Settings.s3_endpoint_url is None`
- [ ] Given `PORT=9000`, when `read_environments()` is called, then `Settings.port == 9000` (int)
- [ ] `.env.example` updated with all new variables
- [ ] Deprecated settings removed: `clusterId`, `encoding_script`, `uri_pattern`

## Implementation Guide

### Suggested Approach

1. Open `app/internal/settings.py`
2. Add new class attributes with type hints and defaults
3. Update `read_environments()` to load new variables
4. Remove deprecated settings (clusterId, encoding_script, uri_pattern)
5. Update `.env.example`
6. Write unit tests

### Key Files to Read

- `app/internal/settings.py` - Current implementation
- `/home/rogerio/git/flexibilizador-service/app/internal/settings.py` - Reference

### Pitfalls to Avoid

- ⚠️ Empty string from env should become `None` for `s3_endpoint_url`
- ⚠️ Port must be converted to `int`
- ⚠️ Don't break existing code that uses old settings during transition

## Testing Requirements

### Unit Tests

Create `tests/unit/test_settings.py`:

```python
import pytest
import os
from app.internal.settings import Settings

@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings to defaults before each test."""
    # Store original values
    original = {k: getattr(Settings, k) for k in dir(Settings) if not k.startswith('_')}
    yield
    # Restore (in case test modified class attributes)
    for k, v in original.items():
        if hasattr(Settings, k):
            setattr(Settings, k, v)

def test_default_values():
    Settings.read_environments()
    
    assert Settings.host == "0.0.0.0"
    assert Settings.port == 8000
    assert Settings.aws_region == "us-east-1"
    assert Settings.s3_endpoint_url is None
    assert Settings.default_newave_bucket == "newave-bucket"
    assert Settings.temp_dir == "/tmp/regras-operativas"

def test_custom_aws_region(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "sa-east-1")
    
    Settings.read_environments()
    
    assert Settings.aws_region == "sa-east-1"

def test_s3_endpoint_url_set(monkeypatch):
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://localhost:4566")
    
    Settings.read_environments()
    
    assert Settings.s3_endpoint_url == "http://localhost:4566"

def test_s3_endpoint_url_empty_is_none(monkeypatch):
    monkeypatch.setenv("S3_ENDPOINT_URL", "")
    
    Settings.read_environments()
    
    assert Settings.s3_endpoint_url is None

def test_port_is_int(monkeypatch):
    monkeypatch.setenv("PORT", "9000")
    
    Settings.read_environments()
    
    assert Settings.port == 9000
    assert isinstance(Settings.port, int)
```

## Definition of Done

- [ ] `app/internal/settings.py` updated with all new settings
- [ ] Deprecated settings removed
- [ ] `.env.example` updated
- [ ] Unit tests passing
- [ ] Type hints on all attributes
- [ ] Class docstring explaining purpose

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Straightforward modifications to existing file
