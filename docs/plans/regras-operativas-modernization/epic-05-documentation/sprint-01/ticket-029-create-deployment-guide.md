# [TICKET-029] Create DEPLOYMENT.md

> **Epic**: [Epic 05: Documentation & Release](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: TICKET-024 (Dockerfile), TICKET-025 (docker-compose), TICKET-026 (systemd)  
> **Blocks**: TICKET-030 (release)

## Context

### Background

Create comprehensive deployment documentation covering Docker Compose deployment, systemd service management, Traefik integration, and operational procedures.

### Current State

No deployment documentation exists.

## Specification

### File to Create

`docs/DEPLOYMENT.md`

### Target Content

```markdown
# Deployment Guide

This guide covers deploying regras-operativas-service in production environments.

## Prerequisites

- Docker 24.0+ and Docker Compose v2
- Linux host (Ubuntu 22.04+ or RHEL 8+ recommended)
- AWS credentials with S3 access
- Network access to S3 endpoints

## Deployment Options

| Option | Use Case | Complexity |
|--------|----------|------------|
| Docker Compose | Single host, production | Low |
| Docker Compose + Traefik | Single host with reverse proxy | Medium |
| systemd Service | Production with auto-start | Medium |

## Docker Compose Deployment

### 1. Clone Repository

```bash
cd /opt
git clone https://github.com/your-org/regras-operativas-service.git
cd regras-operativas-service
```

### 2. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env
```

**Required settings:**
```bash
AWS_REGION=us-east-1
DEFAULT_DECOMP_BUCKET=your-decomp-bucket
DEFAULT_NEWAVE_BUCKET=your-newave-bucket
```

**For AWS IAM Role (EC2/ECS):**
Leave `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` unset.

**For explicit credentials:**
```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### 3. Build and Start

```bash
# Build image
docker compose build

# Start service
docker compose up -d

# Verify
docker compose ps
curl http://localhost:8000/health/live
```

### 4. View Logs

```bash
# Follow logs
docker compose logs -f regras-operativas

# Last 100 lines
docker compose logs --tail=100 regras-operativas
```

## Traefik Integration

The docker-compose.yml includes Traefik labels for automatic reverse proxy configuration.

### Prerequisites

1. Traefik running on the host
2. `traefik-public` Docker network exists

### Setup

```bash
# Create Traefik network (if not exists)
docker network create traefik-public

# Start service
docker compose up -d
```

### Traefik Labels Explained

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.regras-operativas.rule=PathPrefix(`/api/v1/rules`)"
  - "traefik.http.routers.regras-operativas.entrypoints=web,websecure"
  - "traefik.http.services.regras-operativas.loadbalancer.server.port=8000"
```

This routes `/api/v1/rules/*` to the service on port 8000.

## systemd Service Deployment

For production environments with automatic startup and restart.

### 1. Run Installation Script

```bash
sudo ./deploy/install.sh
```

This will:
- Copy files to `/opt/regras-operativas-service`
- Build Docker image
- Install systemd service
- Enable auto-start on boot
- Start the service

### 2. Manage Service

```bash
# Status
sudo systemctl status regras-operativas

# Start/Stop/Restart
sudo systemctl start regras-operativas
sudo systemctl stop regras-operativas
sudo systemctl restart regras-operativas

# Enable/Disable auto-start
sudo systemctl enable regras-operativas
sudo systemctl disable regras-operativas
```

### 3. View Logs

```bash
# Follow system logs
journalctl -u regras-operativas -f

# Last hour
journalctl -u regras-operativas --since "1 hour ago"

# Docker logs
docker compose -f /opt/regras-operativas-service/docker-compose.yml logs -f
```

### 4. Upgrade Service

```bash
cd /path/to/new/version
sudo ./deploy/upgrade.sh
```

### 5. Uninstall Service

```bash
sudo ./deploy/uninstall.sh
```

## Health Checks

### Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health/live` | Liveness probe | `{"status": "ok"}` |
| `/health/ready` | Readiness probe | `{"status": "ok", "checks": {...}}` |
| `/health/version` | Version info | `{"version": "2.0.0", ...}` |

### Monitoring

```bash
# Simple health check
curl -f http://localhost:8000/health/live || echo "Service unhealthy!"

# Readiness (checks S3 connectivity)
curl http://localhost:8000/health/ready | jq .

# Continuous monitoring
watch -n 5 'curl -s http://localhost:8000/health/ready | jq .'
```

### Docker Health Check

The container includes a built-in health check:

```bash
# Check container health status
docker inspect regras-operativas-service --format='{{.State.Health.Status}}'
```

## Resource Limits

### Docker Compose Limits

```yaml
deploy:
  resources:
    limits:
      cpus: "2.0"
      memory: 2G
    reservations:
      cpus: "0.5"
      memory: 512M
```

### Adjusting Limits

Edit `docker-compose.yml` and restart:

```bash
docker compose down
docker compose up -d
```

## Logging

### Log Levels

Set via `LOG_LEVEL` environment variable:
- `DEBUG`: Verbose debugging
- `INFO`: Normal operation (default)
- `WARNING`: Warnings only
- `ERROR`: Errors only

### Log Format

Logs are JSON-structured for easy parsing:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Processing request",
  "correlation_id": "abc123",
  "execution_hash": "xyz789"
}
```

### Log Rotation

Docker handles log rotation via logging driver:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## Security

### Non-Root User

The container runs as non-root user (uid 1000):

```bash
docker compose exec regras-operativas id
# uid=1000(app) gid=1000(app) groups=1000(app)
```

### Network Security

- Service only exposes port 8000
- Use firewall to restrict access
- Use Traefik/nginx for TLS termination

### Secrets Management

**DO NOT** commit `.env` with credentials. Options:
1. Use IAM roles (EC2/ECS)
2. Use Docker secrets
3. Use AWS Secrets Manager
4. Mount credentials file

## Troubleshooting

### Service Won't Start

1. Check Docker:
   ```bash
   sudo systemctl status docker
   docker ps
   ```

2. Check logs:
   ```bash
   journalctl -u regras-operativas -n 50
   docker compose logs --tail=50
   ```

3. Check configuration:
   ```bash
   docker compose config
   ```

### S3 Connection Issues

1. Test credentials:
   ```bash
   aws sts get-caller-identity
   aws s3 ls s3://your-bucket/
   ```

2. Check endpoint:
   ```bash
   # From inside container
   docker compose exec regras-operativas python -c "
   import boto3
   s3 = boto3.client('s3')
   print(s3.list_buckets())
   "
   ```

3. Check network:
   ```bash
   docker compose exec regras-operativas curl -I https://s3.amazonaws.com
   ```

### High Memory Usage

1. Check container stats:
   ```bash
   docker stats regras-operativas-service
   ```

2. Increase memory limit or investigate memory leaks

### Container Keeps Restarting

1. Check exit code:
   ```bash
   docker inspect regras-operativas-service --format='{{.State.ExitCode}}'
   ```

2. Check OOM killer:
   ```bash
   dmesg | grep -i oom
   ```

## Backup and Recovery

### Configuration Backup

```bash
# Backup
cp /opt/regras-operativas-service/.env /backup/regras-operativas.env.$(date +%Y%m%d)

# Restore
cp /backup/regras-operativas.env.YYYYMMDD /opt/regras-operativas-service/.env
```

### Disaster Recovery

1. S3 data is the source of truth - ensure S3 bucket versioning/backup
2. Service is stateless - can be redeployed from scratch
3. Keep `.env` backed up securely

## Scaling Considerations

### Vertical Scaling

Increase resource limits in docker-compose.yml:
```yaml
resources:
  limits:
    cpus: "4.0"
    memory: 4G
```

### Horizontal Scaling

For multiple instances:
1. Use a load balancer (Traefik, nginx, ALB)
2. Service is stateless - can run multiple instances
3. Each instance needs S3 access

## Maintenance

### Regular Tasks

| Task | Frequency | Command |
|------|-----------|---------|
| Check logs | Daily | `journalctl -u regras-operativas --since today` |
| Disk cleanup | Weekly | `docker system prune -f` |
| Image update | As needed | `docker compose pull && docker compose up -d` |

### Updating the Service

```bash
cd /opt/regras-operativas-service
git pull origin main
docker compose build --no-cache
docker compose up -d
```

Or use the upgrade script:
```bash
sudo ./deploy/upgrade.sh
```
```

## Acceptance Criteria

- [ ] DEPLOYMENT.md created in docs/
- [ ] Docker Compose deployment documented
- [ ] systemd service documented
- [ ] Traefik integration documented
- [ ] Health checks documented
- [ ] Troubleshooting section included
- [ ] Security considerations documented

## Implementation Guide

### Step 1: Create docs Directory (if needed)

```bash
mkdir -p docs
```

### Step 2: Write DEPLOYMENT.md

Follow the structure above.

### Step 3: Verify Commands

Test key commands work as documented.

## Definition of Done

- [ ] DEPLOYMENT.md created
- [ ] All deployment methods documented
- [ ] Commands verified
- [ ] Troubleshooting helpful
- [ ] Reviewed by team

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Documentation writing, clear structure provided
