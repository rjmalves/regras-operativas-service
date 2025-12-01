# [TICKET-025] Create docker-compose files

> **Epic**: [Epic 04: Docker & Deployment](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: TICKET-024 (Dockerfile)  
> **Blocks**: TICKET-026 (systemd service)

## Context

### Background

Create Docker Compose configurations for production and development environments. Production uses Traefik labels for reverse proxy integration. Development includes LocalStack for S3 mocking.

### Reference

Based on flexibilizador-service docker-compose pattern.

## Specification

### Files to Create

1. `docker-compose.yml` - Production configuration
2. `docker-compose.dev.yml` - Development configuration  
3. `.env.example` - Environment variable template

### docker-compose.yml (Production)

```yaml
version: "3.9"

services:
  regras-operativas:
    image: regras-operativas-service:${IMAGE_TAG:-2.0.0}
    build:
      context: .
      target: production
    container_name: regras-operativas-service
    restart: unless-stopped
    
    # Environment configuration
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - S3_ENDPOINT_URL=${S3_ENDPOINT_URL:-}
      - DEFAULT_DECOMP_BUCKET=${DEFAULT_DECOMP_BUCKET:-decomp-bucket}
      - DEFAULT_NEWAVE_BUCKET=${DEFAULT_NEWAVE_BUCKET:-newave-bucket}
      - TEMP_DIR=/tmp/regras-operativas
      - ZIP_COMPRESSION_LEVEL=${ZIP_COMPRESSION_LEVEL:-6}
      - MAX_TEMP_DIR_AGE_HOURS=${MAX_TEMP_DIR_AGE_HOURS:-24}
    
    # AWS credentials (mounted from host or use IAM role)
    env_file:
      - .env
    
    # Port mapping (internal only when using Traefik)
    expose:
      - "8000"
    
    # Traefik integration labels
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.regras-operativas.rule=PathPrefix(`/api/v1/rules`)"
      - "traefik.http.routers.regras-operativas.entrypoints=web,websecure"
      - "traefik.http.services.regras-operativas.loadbalancer.server.port=8000"
      - "traefik.http.routers.regras-operativas.middlewares=strip-rules-prefix"
      - "traefik.http.middlewares.strip-rules-prefix.stripprefix.prefixes=/api/v1/rules"
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 512M
    
    # Health check
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    
    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    # Network
    networks:
      - traefik-public
      - default

networks:
  traefik-public:
    external: true
  default:
    driver: bridge
```

### docker-compose.dev.yml (Development)

```yaml
version: "3.9"

services:
  regras-operativas:
    build:
      context: .
      target: development
    container_name: regras-operativas-dev
    
    # Override for development
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - LOG_LEVEL=DEBUG
      - AWS_REGION=us-east-1
      - S3_ENDPOINT_URL=http://localstack:4566
      - DEFAULT_DECOMP_BUCKET=decomp-bucket
      - DEFAULT_NEWAVE_BUCKET=newave-bucket
      - TEMP_DIR=/tmp/regras-operativas
      - AWS_ACCESS_KEY_ID=test
      - AWS_SECRET_ACCESS_KEY=test
    
    # Expose port directly for development
    ports:
      - "8000:8000"
    
    # Mount source code for live reload
    volumes:
      - ./app:/app/app:ro
      - ./main.py:/app/main.py:ro
    
    # Development command with reload
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    
    # Depend on LocalStack
    depends_on:
      localstack:
        condition: service_healthy
    
    networks:
      - dev

  localstack:
    image: localstack/localstack:3.0
    container_name: regras-localstack
    environment:
      - SERVICES=s3
      - DEBUG=0
      - PERSISTENCE=1
      - DOCKER_HOST=unix:///var/run/docker.sock
    ports:
      - "4566:4566"
    volumes:
      - localstack-data:/var/lib/localstack
      - ./scripts/localstack-init.sh:/etc/localstack/init/ready.d/init.sh:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/_localstack/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - dev

volumes:
  localstack-data:

networks:
  dev:
    driver: bridge
```

### .env.example

```bash
# =============================================================================
# Regras Operativas Service Configuration
# =============================================================================
# Copy this file to .env and adjust values for your environment

# Application
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# AWS Configuration
AWS_REGION=us-east-1
# AWS_ACCESS_KEY_ID=        # Use IAM role in production
# AWS_SECRET_ACCESS_KEY=    # Use IAM role in production

# S3 Configuration
# S3_ENDPOINT_URL=          # Leave empty for real AWS, set for LocalStack/MinIO
DEFAULT_DECOMP_BUCKET=decomp-bucket
DEFAULT_NEWAVE_BUCKET=newave-bucket

# Processing Configuration
TEMP_DIR=/tmp/regras-operativas
ZIP_COMPRESSION_LEVEL=6
MAX_TEMP_DIR_AGE_HOURS=24

# Docker Configuration
IMAGE_TAG=2.0.0
```

### LocalStack Init Script

Create `scripts/localstack-init.sh`:

```bash
#!/bin/bash
set -e

echo "Creating S3 buckets for development..."

# Create buckets
awslocal s3 mb s3://decomp-bucket --region us-east-1 || true
awslocal s3 mb s3://newave-bucket --region us-east-1 || true

echo "S3 buckets created successfully!"

# List buckets to verify
awslocal s3 ls
```

## Usage Commands

### Production

```bash
# Start production stack
docker compose up -d

# View logs
docker compose logs -f regras-operativas

# Stop
docker compose down
```

### Development

```bash
# Start development stack with LocalStack
docker compose -f docker-compose.dev.yml up -d

# View logs
docker compose -f docker-compose.dev.yml logs -f regras-operativas

# Rebuild after code changes
docker compose -f docker-compose.dev.yml build

# Stop
docker compose -f docker-compose.dev.yml down
```

### Testing LocalStack Connection

```bash
# List buckets in LocalStack
aws --endpoint-url=http://localhost:4566 s3 ls

# Upload test file
aws --endpoint-url=http://localhost:4566 s3 cp test.txt s3://decomp-bucket/test.txt
```

## Acceptance Criteria

- [ ] `docker compose up -d` starts service (production)
- [ ] `docker compose -f docker-compose.dev.yml up -d` starts service with LocalStack
- [ ] Health check passes in both configurations
- [ ] LocalStack buckets created automatically
- [ ] Live reload works in development (code changes reflected)
- [ ] Traefik labels correct for production routing
- [ ] Resource limits defined
- [ ] Logging configured

## Implementation Guide

### Step 1: Create Directory Structure

```bash
mkdir -p scripts
```

### Step 2: Create Configuration Files

Create all files as specified above.

### Step 3: Make Init Script Executable

```bash
chmod +x scripts/localstack-init.sh
```

### Step 4: Test Development Setup

```bash
# Start development stack
docker compose -f docker-compose.dev.yml up -d

# Wait for health
sleep 15

# Test endpoint
curl http://localhost:8000/health/live

# Test LocalStack
aws --endpoint-url=http://localhost:4566 s3 ls
```

### Step 5: Test Production Setup

```bash
# Create .env from example
cp .env.example .env

# Start production
docker compose up -d

# Check health
curl http://localhost:8000/health/live
```

## Pitfalls to Avoid

- ⚠️ Don't commit `.env` with real credentials
- ⚠️ Ensure `traefik-public` network exists in production
- ⚠️ LocalStack init script needs executable permission
- ⚠️ Mount volumes read-only in development to prevent accidental writes

## Definition of Done

- [ ] `docker-compose.yml` created
- [ ] `docker-compose.dev.yml` created
- [ ] `.env.example` created
- [ ] `scripts/localstack-init.sh` created
- [ ] Production stack starts
- [ ] Development stack starts with LocalStack
- [ ] Health checks pass
- [ ] Documentation complete

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Standard docker-compose pattern, based on flexibilizador template
