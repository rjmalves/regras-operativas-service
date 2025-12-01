# TICKET-017: Update main.py Application

> **Epic**: [Epic 02: API Modernization](../../00-epic-overview.md)  
> **Sprint**: [Sprint 02](./00-sprint-overview.md)  
> **Points**: 1  
> **Dependencies**: [TICKET-014](./ticket-014-implement-health-router.md)

## Context

Update main.py to include health router and use new settings.

## Specification

### File: `main.py`

```python
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI
from app.routers import reservoir, health
from app.internal.settings import Settings
from app.utils.log import Log

load_dotenv()
Settings.read_environments()

app = FastAPI(
    title="Regras Operativas Service",
    version="2.0.0",
    root_path=Settings.root_path,
)

# Include routers
app.include_router(reservoir.router)
app.include_router(health.router)

if __name__ == "__main__":
    Log.configure_logging()
    uvicorn.run(
        "main:app",
        host=Settings.host,
        port=Settings.port,
        log_level=Settings.log_level.lower(),
    )
```

## Changes

1. Add health router import
2. Include health router
3. Update app title and version
4. Use `log_level` from settings
5. Remove `BASEDIR` / `APP_INSTALLDIR` setup (not needed)

## Acceptance Criteria

- [ ] Health router included
- [ ] App version shows "2.0.0"
- [ ] Settings loaded correctly
- [ ] Application starts without errors

## Effort: 1 point
