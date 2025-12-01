# [TICKET-023] Create pyproject.toml

> **Epic**: [Epic 04: Docker & Deployment](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: None  
> **Blocks**: TICKET-024 (Dockerfile)

## Context

### Background

Replace the legacy `requirements.txt` with a modern `pyproject.toml` configuration. This enables better dependency management, dev dependencies, build configuration, and tool settings (pytest, ruff, mypy) in a single file.

### Current State

- `requirements.txt` exists with basic dependencies
- No build system configuration
- No tool configurations

## Specification

### File to Create

`pyproject.toml`

### Implementation

```toml
[project]
name = "regras-operativas-service"
version = "2.0.0"
description = "Reservoir operation rules service for NEWAVE/DECOMP energy planning models"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [
    { name = "Energy Planning Team" }
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering",
]
keywords = ["energy", "planning", "newave", "decomp", "reservoir", "rules"]

dependencies = [
    # Web framework
    "fastapi[standard]>=0.115.0",
    
    # AWS SDK
    "boto3>=1.34.0",
    
    # Data processing
    "pandas>=2.0.0",
    "pyarrow>=14.0.0",
    
    # NEWAVE/DECOMP libraries
    "inewave>=0.0.80",
    "idecomp>=0.0.64",
    
    # HTTP client
    "requests>=2.31.0",
    "aiohttp>=3.9.0",
    
    # Configuration
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    # Testing
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.27.0",
    
    # AWS mocking
    "moto[s3]>=5.0.0",
    
    # Linting & formatting
    "ruff>=0.4.0",
    "mypy>=1.8.0",
    
    # Type stubs
    "boto3-stubs[s3]>=1.34.0",
    "pandas-stubs>=2.0.0",
    "types-requests>=2.31.0",
]

[project.urls]
Repository = "https://github.com/your-org/regras-operativas-service"
Documentation = "https://github.com/your-org/regras-operativas-service#readme"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

# Pytest configuration
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
    "ignore::PendingDeprecationWarning",
]

# Coverage configuration
[tool.coverage.run]
source = ["app"]
branch = true
omit = [
    "*/tests/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]
fail_under = 80
show_missing = true

# Ruff configuration (linting & formatting)
[tool.ruff]
target-version = "py311"
line-length = 88
src = ["app", "tests"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # function call in default argument (FastAPI Depends)
    "B904",   # raise without from (sometimes intentional)
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["ARG001", "ARG002"]  # Unused arguments OK in tests

[tool.ruff.lint.isort]
known-first-party = ["app"]

# MyPy configuration
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
strict_optional = true
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = [
    "inewave.*",
    "idecomp.*",
    "moto.*",
]
ignore_missing_imports = true
```

### Files to Remove/Update

- **Remove**: `requirements.txt` (after migration verified)
- **Update**: `.gitignore` if needed for uv/hatch artifacts

### Migration Steps

1. Create `pyproject.toml`
2. Install with uv: `uv sync`
3. Verify imports work: `uv run python -c "from app.internal.settings import settings; print('OK')"`
4. Run existing tests: `uv run pytest`
5. After verification, remove `requirements.txt`

## Acceptance Criteria

- [ ] `pyproject.toml` created with all dependencies
- [ ] `uv sync` succeeds without errors
- [ ] `uv run python -c "import app"` works
- [ ] `uv run pytest` runs (even if tests fail due to missing code)
- [ ] `uv run ruff check app/` runs
- [ ] `uv run mypy app/` runs (may have errors for incomplete code)
- [ ] Dev dependencies available: `uv run pytest --version`

## Implementation Guide

### Step 1: Create pyproject.toml

Create the file with the content above.

### Step 2: Install Dependencies

```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install
uv sync

# Install dev dependencies
uv sync --extra dev
```

### Step 3: Verify Installation

```bash
# Check imports
uv run python -c "import fastapi; import boto3; import pandas; print('Core deps OK')"
uv run python -c "import inewave; import idecomp; print('Domain deps OK')"
uv run python -c "import pytest; import moto; print('Dev deps OK')"
```

### Step 4: Test Tools

```bash
# Linting
uv run ruff check app/

# Type checking
uv run mypy app/

# Tests
uv run pytest tests/ --collect-only
```

## Pitfalls to Avoid

- ⚠️ Don't remove `requirements.txt` until migration verified
- ⚠️ Pin major versions to avoid breaking changes
- ⚠️ Include `pydantic-settings` for Settings class
- ⚠️ Include type stubs for dev dependencies

## Definition of Done

- [ ] `pyproject.toml` created
- [ ] All dependencies install successfully
- [ ] Tools (pytest, ruff, mypy) run
- [ ] No import errors
- [ ] `requirements.txt` can be removed

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Standard pyproject.toml setup, clear dependency list from requirements.txt
