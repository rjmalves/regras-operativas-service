# [TICKET-028] Create MIGRATION.md

> **Epic**: [Epic 05: Documentation & Release](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: All implementation tickets complete  
> **Blocks**: TICKET-030 (release)

## Context

### Background

Users upgrading from v1.x need a clear migration guide covering the breaking changes: S3 instead of filesystem, new request/response formats, Docker instead of PM2, and new configuration.

### Current State

No migration documentation exists.

## Specification

### File to Create

`docs/MIGRATION.md`

### Target Content

```markdown
# Migration Guide: v1.x to v2.0

This guide helps you migrate from regras-operativas-service v1.x (PM2 + filesystem) to v2.0 (Docker + S3).

## Overview of Changes

| Aspect | v1.x | v2.0 |
|--------|------|------|
| Storage | Shared filesystem | S3 buckets |
| Request format | base62-encoded paths | bucket + execution_hash |
| Response format | `{ result: [...] }` | `{ success, output_key, ... }` |
| Deployment | PM2 | Docker Compose |
| Port | 5054 | 8000 |
| Process manager | PM2 | systemd + Docker |
| Configuration | ecosystem.config.js | .env + docker-compose.yml |

## Breaking Changes

### 1. Request Format Change

**v1.x Request:**
```json
{
  "sources": [
    {
      "id": "L2Nhc2VzL2RlY29tcC9leGVjdXRpb25faGFzaA==",
      "program": "DECOMP"
    }
  ],
  "destination": {
    "id": "L2Nhc2VzL25ld2F2ZS9leGVjdXRpb25faGFzaA==",
    "program": "NEWAVE"
  },
  "rules": [...]
}
```

**v2.0 Request:**
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
  "rules": [...]
}
```

**Migration Action:**
- Replace `id` (base62 path) with `bucket` + `execution_hash`
- Add `output_prefix` to destination (typically "ingest")
- Update client code to construct S3 references

### 2. Response Format Change

**v1.x Response:**
```json
{
  "result": [
    { "reservoirCode": 156, "applied": true, ... }
  ]
}
```

**v2.0 Response:**
```json
{
  "success": true,
  "execution_hash": "xyz789ghi012",
  "output_key": "ingest/xyz789ghi012_regras.zip",
  "rules_applied": [
    { "reservoirCode": 156, "applied": true, ... }
  ],
  "message": "Applied 5 reservoir rules"
}
```

**Migration Action:**
- Update client code to read `rules_applied` instead of `result`
- Use `output_key` to locate the output artifact in S3
- Check `success` field for operation status

### 3. Error Response Change

**v1.x Error:**
```json
{
  "error": "File not found: /cases/decomp/..."
}
```

**v2.0 Error:**
```json
{
  "error_code": "ARTIFACT_NOT_FOUND",
  "message": "Object not found: s3://decomp-bucket/...",
  "details": {
    "bucket": "decomp-bucket",
    "key": "artifacts/abc123/entradas/deck_processado.zip"
  }
}
```

**Migration Action:**
- Update error handling to parse `error_code`
- Use `details` for debugging information

### 4. Port Change

| Version | Default Port |
|---------|-------------|
| v1.x | 5054 |
| v2.0 | 8000 |

**Migration Action:**
- Update reverse proxy configuration
- Update client base URLs
- Update firewall rules if needed

### 5. Endpoint Path Change

The endpoint remains `/reservoir/` but the root path configuration has changed.

**v1.x:** `ROOT_PATH=/api/v1/rules`
**v2.0:** Same, configured via environment variable

## Migration Steps

### Step 1: Prepare Infrastructure

1. **S3 Buckets**: Ensure S3 buckets exist:
   - `decomp-bucket` (or your custom name)
   - `newave-bucket` (or your custom name)

2. **IAM Role**: Create IAM role with S3 permissions:
   ```json
   {
     "Effect": "Allow",
     "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
     "Resource": ["arn:aws:s3:::*-bucket", "arn:aws:s3:::*-bucket/*"]
   }
   ```

3. **Docker**: Install Docker and Docker Compose on the host

### Step 2: Migrate Data (if needed)

If you have existing case data on the filesystem that needs to be in S3:

```bash
# Upload existing cases to S3
aws s3 sync /cases/decomp/ s3://decomp-bucket/artifacts/
aws s3 sync /cases/newave/ s3://newave-bucket/artifacts/
```

### Step 3: Deploy v2.0

1. **Stop v1.x service:**
   ```bash
   pm2 stop regras-operativas
   pm2 delete regras-operativas
   ```

2. **Deploy v2.0:**
   ```bash
   cd /opt/regras-operativas-service
   git pull origin main
   
   # Configure environment
   cp .env.example .env
   # Edit .env with your settings
   
   # Install and start
   sudo ./deploy/install.sh
   ```

3. **Verify deployment:**
   ```bash
   curl http://localhost:8000/health/live
   curl http://localhost:8000/health/ready
   ```

### Step 4: Update Reverse Proxy

**Traefik (recommended):**
The docker-compose.yml includes Traefik labels. Ensure Traefik network exists:
```bash
docker network create traefik-public
```

**Nginx (manual):**
```nginx
location /api/v1/rules/ {
    proxy_pass http://localhost:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Step 5: Update Clients

Update all client applications to:
1. Use new request format (bucket + execution_hash)
2. Handle new response format
3. Update error handling
4. Update base URL port if needed

### Step 6: Verify Integration

Test the complete workflow:
```bash
curl -X POST http://localhost:8000/reservoir/ \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [{
      "bucket": "decomp-bucket",
      "execution_hash": "test_hash",
      "program": "DECOMP"
    }],
    "destination": {
      "bucket": "newave-bucket",
      "execution_hash": "dest_hash",
      "program": "NEWAVE",
      "output_prefix": "ingest"
    },
    "rules": []
  }'
```

## Rollback Procedure

If you need to rollback to v1.x:

1. **Stop v2.0:**
   ```bash
   sudo systemctl stop regras-operativas
   sudo ./deploy/uninstall.sh
   ```

2. **Restore v1.x:**
   ```bash
   cd /path/to/v1.x
   pm2 start ecosystem.config.js
   ```

3. **Revert proxy configuration** to port 5054

## Configuration Mapping

| v1.x (ecosystem.config.js) | v2.0 (.env) |
|---------------------------|-------------|
| `PORT: 5054` | `PORT=8000` |
| `ROOT_PATH: "/api/v1/rules"` | `ROOT_PATH=/api/v1/rules` |
| `CLUSTER_ID: 1` | _(removed)_ |
| _(none)_ | `AWS_REGION=us-east-1` |
| _(none)_ | `DEFAULT_DECOMP_BUCKET=decomp-bucket` |
| _(none)_ | `DEFAULT_NEWAVE_BUCKET=newave-bucket` |
| _(none)_ | `S3_ENDPOINT_URL=` |

## Troubleshooting

### Service won't start

Check Docker and logs:
```bash
docker compose logs -f
journalctl -u regras-operativas -f
```

### S3 access denied

Verify IAM permissions and credentials:
```bash
# Test S3 access from container
docker compose exec regras-operativas python -c "
import boto3
s3 = boto3.client('s3')
print(s3.list_buckets())
"
```

### Artifact not found errors

Verify the S3 path structure matches expected format:
```
artifacts/<execution_hash>/entradas/deck_processado.zip
```

## Support

For issues during migration:
1. Check logs: `journalctl -u regras-operativas -f`
2. Verify S3 connectivity: `aws s3 ls s3://your-bucket/`
3. Test health endpoints: `curl http://localhost:8000/health/ready`
```

## Acceptance Criteria

- [ ] MIGRATION.md created in docs/
- [ ] All breaking changes documented
- [ ] Step-by-step migration procedure
- [ ] Request/response format changes clear
- [ ] Rollback procedure included
- [ ] Troubleshooting section helpful

## Implementation Guide

### Step 1: Create docs Directory (if needed)

```bash
mkdir -p docs
```

### Step 2: Write MIGRATION.md

Follow the structure above.

### Step 3: Review for Accuracy

Ensure all v1.x references are accurate based on existing code.

## Definition of Done

- [ ] MIGRATION.md created
- [ ] Breaking changes documented
- [ ] Migration steps clear
- [ ] Rollback documented
- [ ] Reviewed by team

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Documentation writing, clear structure provided
