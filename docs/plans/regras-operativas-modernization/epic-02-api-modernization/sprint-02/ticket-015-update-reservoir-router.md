# TICKET-015: Update Reservoir Router for S3

> **Epic**: [Epic 02: API Modernization](../../00-epic-overview.md)  
> **Sprint**: [Sprint 02](./00-sprint-overview.md)  
> **Points**: 5  
> **Dependencies**: [TICKET-006](../../epic-01-s3-integration/sprint-02/ticket-006-create-s3-decomp-uow.md), [TICKET-007](../../epic-01-s3-integration/sprint-02/ticket-007-create-s3-newave-uow.md), [TICKET-011](../sprint-01/ticket-011-update-request-model.md)  
> **Status**: ✅ Complete

## Context

Update the reservoir router to use S3-based Unit of Work instead of filesystem paths.

## Implementation Summary

The router was updated to provide both V1 (legacy) and V2 (modern S3) endpoints:

### V1 Endpoint (Legacy - Deprecated)
- `POST /reservoir/` - Uses base62-encoded filesystem paths
- Preserved for backward compatibility
- Marked as deprecated in OpenAPI docs

### V2 Endpoint (Modern)
- `POST /reservoir/v2/` - Uses S3 bucket + execution_hash references
- Downloads source cases from S3 for prospection
- Downloads destination case from S3
- Applies rules using existing business logic
- Uploads modified deck back to S3
- Returns structured response with `output_key`

### Key Implementation Details

1. **Sync-Compatible Wrappers**: Created wrapper classes in `unitofwork.py` to bridge async S3 downloads with sync business logic:
   - `S3DecompUnitOfWorkSync` - Wraps S3DecompUnitOfWork
   - `S3NewaveUnitOfWorkSync` - Wraps S3NewaveUnitOfWork
   - `S3DecompProspectionSync` - Wraps individual repositories from prospection

2. **Exception Mapping**: Maps custom exceptions to HTTP status codes:
   - `ArtifactNotFoundError` → 404
   - `ParseError` → 422
   - `RuleApplicationError` → 500
   - `S3OperationError` → 500

3. **Preserved Business Logic**: The existing `reservoirrulerepository.py` business logic was NOT modified - only wrapped for S3 compatibility.

## Files Modified

| File | Changes |
|------|---------|
| `app/routers/reservoir.py` | Added V2 endpoint, preserved V1 as deprecated |
| `app/services/unitofwork.py` | Added sync wrapper classes for S3 UoW |

## Acceptance Criteria

- [x] Endpoint accepts new request format (bucket + hash)
- [x] Downloads sources from S3 for prospection
- [x] Downloads destination from S3
- [x] Applies rules using existing business logic
- [x] Uploads result to S3
- [x] Returns output_key in response
- [x] Maps exceptions to proper HTTP status codes
- [x] All 146 tests passing

## Routes Exposed

```
/reservoir/        - V1 (legacy, deprecated)
/reservoir/v2/     - V2 (modern, S3-based)
```

## Effort: 5 points (complex integration)
