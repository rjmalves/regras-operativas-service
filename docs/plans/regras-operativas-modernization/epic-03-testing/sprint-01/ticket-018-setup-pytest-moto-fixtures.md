# [TICKET-018] Setup pytest and moto fixtures

> **Epic**: [Epic 03: Testing Infrastructure](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: TICKET-002 (S3Repository), TICKET-005 (Settings)  
> **Blocks**: TICKET-019, TICKET-020, TICKET-021, TICKET-022

## Context

### Background

The testing infrastructure must be established before writing unit and integration tests. This includes pytest configuration, moto-based S3 mocking fixtures, and test data fixtures for NEWAVE/DECOMP files.

### Current State

- Basic `test.py` exists but uses manual testing approach
- No pytest configuration
- No mocking infrastructure

## Specification

### Files to Create

```
tests/
├── __init__.py
├── conftest.py              # Main pytest fixtures
├── fixtures/
│   ├── __init__.py
│   ├── decomp/              # Minimal DECOMP test files
│   │   ├── caso.dat
│   │   └── dadger.rv0
│   └── newave/              # Minimal NEWAVE test files
│       ├── arquivos.dat
│       ├── re.dat
│       └── modif.dat
├── unit/
│   └── __init__.py
└── integration/
    └── __init__.py
```

### conftest.py Implementation

```python
"""Shared pytest fixtures for regras-operativas-service tests."""

import os
import pytest
import zipfile
import tempfile
from pathlib import Path
from typing import Generator

import boto3
from moto import mock_aws

# Test bucket names
TEST_DECOMP_BUCKET = "test-decomp-bucket"
TEST_NEWAVE_BUCKET = "test-newave-bucket"
TEST_REGION = "us-east-1"


@pytest.fixture(scope="function")
def aws_credentials() -> Generator[None, None, None]:
    """Mock AWS credentials for moto."""
    original_env = {
        "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "AWS_SECURITY_TOKEN": os.environ.get("AWS_SECURITY_TOKEN"),
        "AWS_SESSION_TOKEN": os.environ.get("AWS_SESSION_TOKEN"),
        "AWS_DEFAULT_REGION": os.environ.get("AWS_DEFAULT_REGION"),
    }
    
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = TEST_REGION
    
    yield
    
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    """Create mocked S3 client with test buckets."""
    with mock_aws():
        client = boto3.client("s3", region_name=TEST_REGION)
        
        # Create test buckets
        client.create_bucket(Bucket=TEST_DECOMP_BUCKET)
        client.create_bucket(Bucket=TEST_NEWAVE_BUCKET)
        
        yield client


@pytest.fixture(scope="function")
def s3_repo(s3_client, monkeypatch):
    """Create S3Repository instance with mocked S3."""
    from app.adapters.s3_repository import S3Repository, reset_s3_repository
    
    # Reset singleton state
    reset_s3_repository()
    
    # Create repository
    repo = S3Repository(region=TEST_REGION)
    
    yield repo
    
    # Cleanup
    repo.close()
    reset_s3_repository()


@pytest.fixture(scope="session")
def test_fixtures_path() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def decomp_fixtures_path(test_fixtures_path) -> Path:
    """Return path to DECOMP test fixtures."""
    return test_fixtures_path / "decomp"


@pytest.fixture(scope="session")
def newave_fixtures_path(test_fixtures_path) -> Path:
    """Return path to NEWAVE test fixtures."""
    return test_fixtures_path / "newave"


@pytest.fixture(scope="function")
def temp_directory() -> Generator[Path, None, None]:
    """Create and cleanup a temporary directory."""
    with tempfile.TemporaryDirectory(prefix="test_regras_") as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture(scope="function")
def decomp_zip_file(decomp_fixtures_path, temp_directory) -> Path:
    """Create a test DECOMP zip file."""
    zip_path = temp_directory / "deck_processado.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in decomp_fixtures_path.glob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.name)
    
    return zip_path


@pytest.fixture(scope="function")
def newave_zip_file(newave_fixtures_path, temp_directory) -> Path:
    """Create a test NEWAVE zip file."""
    zip_path = temp_directory / "deck_processado.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in newave_fixtures_path.glob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.name)
    
    return zip_path


@pytest.fixture(scope="function")
def s3_with_decomp_artifact(s3_client, decomp_zip_file) -> dict:
    """Upload DECOMP test artifact to mocked S3."""
    execution_hash = "test_decomp_hash_123"
    key = f"artifacts/{execution_hash}/entradas/deck_processado.zip"
    
    with open(decomp_zip_file, 'rb') as f:
        s3_client.put_object(
            Bucket=TEST_DECOMP_BUCKET,
            Key=key,
            Body=f.read()
        )
    
    return {
        "bucket": TEST_DECOMP_BUCKET,
        "execution_hash": execution_hash,
        "key": key
    }


@pytest.fixture(scope="function")
def s3_with_newave_artifact(s3_client, newave_zip_file) -> dict:
    """Upload NEWAVE test artifact to mocked S3."""
    execution_hash = "test_newave_hash_456"
    key = f"artifacts/{execution_hash}/entradas/deck_processado.zip"
    
    with open(newave_zip_file, 'rb') as f:
        s3_client.put_object(
            Bucket=TEST_NEWAVE_BUCKET,
            Key=key,
            Body=f.read()
        )
    
    return {
        "bucket": TEST_NEWAVE_BUCKET,
        "execution_hash": execution_hash,
        "key": key
    }


@pytest.fixture(scope="function")
def mock_settings(monkeypatch):
    """Override settings for testing."""
    monkeypatch.setenv("AWS_REGION", TEST_REGION)
    monkeypatch.setenv("DEFAULT_DECOMP_BUCKET", TEST_DECOMP_BUCKET)
    monkeypatch.setenv("DEFAULT_NEWAVE_BUCKET", TEST_NEWAVE_BUCKET)
    monkeypatch.setenv("S3_ENDPOINT_URL", "")
    monkeypatch.setenv("TEMP_DIR", "/tmp/test-regras-operativas")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
```

### pytest.ini / pyproject.toml Test Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "-ra",
]
markers = [
    "unit: Unit tests (fast, no external dependencies)",
    "integration: Integration tests (may use mocked AWS)",
    "slow: Slow tests (skipped by default)",
]
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

### Minimal Test Fixture Files

**tests/fixtures/decomp/caso.dat**:
```
TEST CASE FOR DECOMP
```

**tests/fixtures/decomp/dadger.rv0**:
```
 TITULO
 &
 CASO DE TESTE
 &
```

**tests/fixtures/newave/arquivos.dat**:
```
ARQUIVOS DE DADOS DO NEWAVE
```

**tests/fixtures/newave/re.dat**:
```
 RESTRICOES ELETRICAS
```

**tests/fixtures/newave/modif.dat**:
```
 MODIFICACOES
```

## Acceptance Criteria

- [ ] `pytest tests/ --collect-only` shows test discovery working
- [ ] `pytest tests/ -m unit` runs without errors (even if no tests yet)
- [ ] `s3_client` fixture creates mocked buckets
- [ ] `s3_repo` fixture returns working S3Repository
- [ ] Fixture files exist and can be zipped
- [ ] `s3_with_decomp_artifact` uploads test data to mocked S3
- [ ] `s3_with_newave_artifact` uploads test data to mocked S3
- [ ] `temp_directory` creates and cleans up temp dir

## Implementation Guide

### Step 1: Create Directory Structure

```bash
mkdir -p tests/{unit,integration,fixtures/{decomp,newave}}
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
touch tests/fixtures/__init__.py
```

### Step 2: Create Fixture Files

Create minimal test fixture files that represent valid DECOMP/NEWAVE structure.

### Step 3: Create conftest.py

Implement all fixtures as specified above.

### Step 4: Add Test Configuration

Add pytest configuration to `pyproject.toml`.

### Step 5: Verify Setup

```bash
uv run pytest tests/ --collect-only
uv run pytest tests/ -v
```

## Testing Requirements

### Self-Test

Create a simple test to verify fixtures work:

```python
# tests/test_fixtures.py
import pytest

def test_aws_credentials_fixture(aws_credentials):
    import os
    assert os.environ.get("AWS_ACCESS_KEY_ID") == "testing"

def test_s3_client_fixture(s3_client):
    buckets = s3_client.list_buckets()
    bucket_names = [b["Name"] for b in buckets["Buckets"]]
    assert "test-decomp-bucket" in bucket_names
    assert "test-newave-bucket" in bucket_names

def test_temp_directory_fixture(temp_directory):
    assert temp_directory.exists()
    test_file = temp_directory / "test.txt"
    test_file.write_text("test")
    assert test_file.exists()
```

## Definition of Done

- [ ] All directories created
- [ ] conftest.py with all fixtures
- [ ] Minimal fixture files for DECOMP/NEWAVE
- [ ] pytest configuration in pyproject.toml
- [ ] Self-test passes
- [ ] `pytest tests/ --collect-only` succeeds

## Effort Estimate

**Points**: 3  
**Confidence**: High  
**Rationale**: Standard pytest setup, fixtures copied from flexibilizador pattern
