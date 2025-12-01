# [TICKET-026] Create systemd service and deploy scripts

> **Epic**: [Epic 04: Docker & Deployment](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: TICKET-025 (docker-compose files)  
> **Blocks**: None

## Context

### Background

Create systemd service unit and deployment scripts for managing the containerized service on the HPC head node. This enables automatic startup, restart on failure, and standard Linux service management.

### Reference

Based on flexibilizador-service deployment pattern.

## Specification

### Files to Create

```
deploy/
├── regras-operativas.service    # systemd unit file
├── install.sh                   # Installation script
├── uninstall.sh                 # Uninstallation script
└── upgrade.sh                   # Upgrade script
```

### regras-operativas.service

```ini
[Unit]
Description=Regras Operativas Service - Reservoir operation rules for NEWAVE/DECOMP
Documentation=https://github.com/your-org/regras-operativas-service
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/regras-operativas-service

# Start command
ExecStart=/usr/bin/docker compose up -d --remove-orphans

# Stop command
ExecStop=/usr/bin/docker compose down

# Reload command (recreate containers)
ExecReload=/usr/bin/docker compose up -d --force-recreate

# Restart policy
Restart=on-failure
RestartSec=30

# Environment file
EnvironmentFile=-/opt/regras-operativas-service/.env

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=regras-operativas

# Security
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

### install.sh

```bash
#!/bin/bash
set -euo pipefail

# =============================================================================
# Regras Operativas Service Installation Script
# =============================================================================

SERVICE_NAME="regras-operativas"
INSTALL_DIR="/opt/regras-operativas-service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    if ! systemctl is-active --quiet docker; then
        log_error "Docker service is not running"
        exit 1
    fi
    
    log_info "Prerequisites OK"
}

# Create installation directory
create_install_dir() {
    log_info "Creating installation directory: ${INSTALL_DIR}"
    
    mkdir -p "${INSTALL_DIR}"
    
    # Copy necessary files
    cp "${PROJECT_DIR}/docker-compose.yml" "${INSTALL_DIR}/"
    cp "${PROJECT_DIR}/Dockerfile" "${INSTALL_DIR}/"
    cp "${PROJECT_DIR}/pyproject.toml" "${INSTALL_DIR}/"
    cp "${PROJECT_DIR}/README.md" "${INSTALL_DIR}/"
    cp "${PROJECT_DIR}/main.py" "${INSTALL_DIR}/"
    cp -r "${PROJECT_DIR}/app" "${INSTALL_DIR}/"
    
    # Copy environment template if .env doesn't exist
    if [[ ! -f "${INSTALL_DIR}/.env" ]]; then
        if [[ -f "${PROJECT_DIR}/.env.example" ]]; then
            cp "${PROJECT_DIR}/.env.example" "${INSTALL_DIR}/.env"
            log_warn "Created .env from template. Please configure it!"
        fi
    else
        log_info "Keeping existing .env file"
    fi
    
    log_info "Files copied to ${INSTALL_DIR}"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    cd "${INSTALL_DIR}"
    docker compose build --no-cache
    
    log_info "Docker image built successfully"
}

# Install systemd service
install_service() {
    log_info "Installing systemd service..."
    
    cp "${SCRIPT_DIR}/regras-operativas.service" "${SERVICE_FILE}"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable "${SERVICE_NAME}.service"
    
    log_info "Systemd service installed and enabled"
}

# Start service
start_service() {
    log_info "Starting service..."
    
    systemctl start "${SERVICE_NAME}.service"
    
    # Wait for health check
    log_info "Waiting for service to be healthy..."
    sleep 10
    
    if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
        log_info "Service started successfully"
    else
        log_error "Service failed to start. Check: journalctl -u ${SERVICE_NAME}.service"
        exit 1
    fi
}

# Main installation
main() {
    echo "========================================"
    echo "Regras Operativas Service Installation"
    echo "========================================"
    echo
    
    check_root
    check_prerequisites
    create_install_dir
    build_image
    install_service
    start_service
    
    echo
    echo "========================================"
    log_info "Installation complete!"
    echo "========================================"
    echo
    echo "Service commands:"
    echo "  systemctl status ${SERVICE_NAME}"
    echo "  systemctl restart ${SERVICE_NAME}"
    echo "  journalctl -u ${SERVICE_NAME} -f"
    echo
    echo "Configuration file: ${INSTALL_DIR}/.env"
    echo
}

main "$@"
```

### uninstall.sh

```bash
#!/bin/bash
set -euo pipefail

# =============================================================================
# Regras Operativas Service Uninstallation Script
# =============================================================================

SERVICE_NAME="regras-operativas"
INSTALL_DIR="/opt/regras-operativas-service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

stop_service() {
    log_info "Stopping service..."
    
    if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
        systemctl stop "${SERVICE_NAME}.service"
        log_info "Service stopped"
    else
        log_info "Service was not running"
    fi
}

disable_service() {
    log_info "Disabling service..."
    
    if systemctl is-enabled --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
        systemctl disable "${SERVICE_NAME}.service"
        log_info "Service disabled"
    fi
}

remove_service_file() {
    log_info "Removing systemd service file..."
    
    if [[ -f "${SERVICE_FILE}" ]]; then
        rm -f "${SERVICE_FILE}"
        systemctl daemon-reload
        log_info "Service file removed"
    fi
}

remove_docker_resources() {
    log_info "Removing Docker resources..."
    
    if [[ -d "${INSTALL_DIR}" ]]; then
        cd "${INSTALL_DIR}"
        
        # Remove containers and networks
        docker compose down --rmi local --volumes 2>/dev/null || true
        
        log_info "Docker resources removed"
    fi
}

remove_install_dir() {
    local keep_config="${1:-false}"
    
    if [[ -d "${INSTALL_DIR}" ]]; then
        if [[ "$keep_config" == "true" ]]; then
            log_info "Keeping configuration, removing application files..."
            find "${INSTALL_DIR}" -mindepth 1 ! -name '.env' -delete
        else
            log_info "Removing installation directory..."
            rm -rf "${INSTALL_DIR}"
        fi
        log_info "Installation directory cleaned"
    fi
}

main() {
    echo "========================================"
    echo "Regras Operativas Service Uninstallation"
    echo "========================================"
    echo
    
    check_root
    
    # Ask about keeping configuration
    read -p "Keep configuration file (.env)? [y/N] " -n 1 -r
    echo
    local keep_config="false"
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        keep_config="true"
    fi
    
    stop_service
    disable_service
    remove_service_file
    remove_docker_resources
    remove_install_dir "$keep_config"
    
    echo
    echo "========================================"
    log_info "Uninstallation complete!"
    echo "========================================"
}

main "$@"
```

### upgrade.sh

```bash
#!/bin/bash
set -euo pipefail

# =============================================================================
# Regras Operativas Service Upgrade Script
# =============================================================================

SERVICE_NAME="regras-operativas"
INSTALL_DIR="/opt/regras-operativas-service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

backup_config() {
    log_info "Backing up configuration..."
    
    if [[ -f "${INSTALL_DIR}/.env" ]]; then
        cp "${INSTALL_DIR}/.env" "${INSTALL_DIR}/.env.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Configuration backed up"
    fi
}

update_files() {
    log_info "Updating application files..."
    
    # Update files but keep .env
    cp "${PROJECT_DIR}/docker-compose.yml" "${INSTALL_DIR}/"
    cp "${PROJECT_DIR}/Dockerfile" "${INSTALL_DIR}/"
    cp "${PROJECT_DIR}/pyproject.toml" "${INSTALL_DIR}/"
    cp "${PROJECT_DIR}/README.md" "${INSTALL_DIR}/"
    cp "${PROJECT_DIR}/main.py" "${INSTALL_DIR}/"
    rm -rf "${INSTALL_DIR}/app"
    cp -r "${PROJECT_DIR}/app" "${INSTALL_DIR}/"
    
    log_info "Files updated"
}

rebuild_image() {
    log_info "Rebuilding Docker image..."
    
    cd "${INSTALL_DIR}"
    docker compose build --no-cache
    
    log_info "Image rebuilt"
}

restart_service() {
    log_info "Restarting service..."
    
    systemctl restart "${SERVICE_NAME}.service"
    
    sleep 10
    
    if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
        log_info "Service restarted successfully"
    else
        log_error "Service failed to restart. Check: journalctl -u ${SERVICE_NAME}.service"
        exit 1
    fi
}

main() {
    echo "========================================"
    echo "Regras Operativas Service Upgrade"
    echo "========================================"
    echo
    
    check_root
    
    if [[ ! -d "${INSTALL_DIR}" ]]; then
        log_error "Service not installed. Run install.sh first."
        exit 1
    fi
    
    backup_config
    update_files
    rebuild_image
    restart_service
    
    echo
    echo "========================================"
    log_info "Upgrade complete!"
    echo "========================================"
    echo
    echo "Check service status: systemctl status ${SERVICE_NAME}"
    echo
}

main "$@"
```

## Acceptance Criteria

- [ ] `deploy/regras-operativas.service` created
- [ ] `deploy/install.sh` created and executable
- [ ] `deploy/uninstall.sh` created and executable
- [ ] `deploy/upgrade.sh` created and executable
- [ ] `sudo ./deploy/install.sh` installs service
- [ ] `systemctl status regras-operativas` shows running
- [ ] `sudo ./deploy/uninstall.sh` removes service
- [ ] Scripts have proper error handling
- [ ] Scripts check for root permissions

## Implementation Guide

### Step 1: Create Deploy Directory

```bash
mkdir -p deploy
```

### Step 2: Create Files

Create all files as specified above.

### Step 3: Make Scripts Executable

```bash
chmod +x deploy/install.sh
chmod +x deploy/uninstall.sh
chmod +x deploy/upgrade.sh
```

### Step 4: Test Installation (on target system)

```bash
# Copy project to target
rsync -av --exclude '.git' . user@hpc-head:/tmp/regras-operativas-service/

# SSH to target and install
ssh user@hpc-head
cd /tmp/regras-operativas-service
sudo ./deploy/install.sh
```

## Pitfalls to Avoid

- ⚠️ Scripts must be run as root
- ⚠️ Keep `.env` during upgrades
- ⚠️ Ensure Docker service is running before install
- ⚠️ Test uninstall doesn't delete user data accidentally

## Definition of Done

- [ ] All deploy files created
- [ ] Scripts are executable
- [ ] Install script works
- [ ] Uninstall script works
- [ ] Upgrade script works
- [ ] Service starts on boot
- [ ] Documentation complete

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Standard systemd and shell script pattern, based on flexibilizador template
