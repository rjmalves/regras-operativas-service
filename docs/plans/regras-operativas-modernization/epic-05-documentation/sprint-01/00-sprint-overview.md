# Sprint 01: Documentation & Release

> **Epic**: [Epic 05: Documentation & Release](../00-epic-overview.md)  
> **Duration**: 0.5 week  
> **Status**: ✅ Complete

## Tickets

| ID | Title | Points | Description |
|----|-------|--------|-------------|
| TICKET-027 | Update README.md | 2 | Rewrite for v2.0 API and Docker |
| TICKET-028 | Create MIGRATION.md | 2 | v1.x → v2.0 migration guide |
| TICKET-029 | Create DEPLOYMENT.md | 2 | Docker and systemd deployment |
| TICKET-030 | Create CHANGELOG.md and release | 1 | Document changes, create tag |

**Total Points**: 7

## README Structure

```markdown
# regras-operativas-service

Service for applying reservoir operation rules to NEWAVE/DECOMP.

## Quick Start

docker compose up -d

## API

POST /reservoir/

## Configuration

Environment variables...

## Development

uv sync
uv run pytest
```

## MIGRATION.md Key Sections

1. Overview of changes
2. Request format changes (base62 → S3)
3. Response format changes
4. Environment variable changes
5. Deployment changes (PM2 → Docker)
6. Rollback instructions

## CHANGELOG.md

```markdown
# Changelog

## [2.0.0] - 2024-XX-XX

### Added
- S3 integration
- Health endpoints
- Docker support
- Comprehensive tests

### Changed
- **BREAKING**: Request format (S3 instead of base62)
- **BREAKING**: Response format (includes output_key)
- **BREAKING**: Default port 5054 → 8000

### Removed
- Filesystem storage
- base62 encoding
- PM2 deployment
```

## Definition of Done

- [x] All docs reviewed
- [x] No broken links
- [x] Git tag v2.0.0 ready
