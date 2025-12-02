#!/bin/bash
# =============================================================================
# Regras Operativas Service - Uninstall Script
# =============================================================================
# Usage: sudo ./uninstall.sh
# =============================================================================

set -e

SERVICE_NAME="regras-operativas"
INSTALL_DIR="/opt/regras-operativas-service"
SERVICE_FILE="${SERVICE_NAME}.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

log_info "Uninstalling ${SERVICE_NAME}..."

# Stop service
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    log_info "Stopping service..."
    systemctl stop "${SERVICE_NAME}"
fi

# Disable service
if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
    log_info "Disabling service..."
    systemctl disable "${SERVICE_NAME}"
fi

# Remove systemd service file
if [[ -f "/etc/systemd/system/${SERVICE_FILE}" ]]; then
    log_info "Removing systemd service..."
    rm -f "/etc/systemd/system/${SERVICE_FILE}"
    systemctl daemon-reload
fi

# Stop and remove Docker containers
if [[ -d "${INSTALL_DIR}" ]]; then
    log_info "Stopping Docker containers..."
    cd "${INSTALL_DIR}"
    docker compose down --volumes 2>/dev/null || true
fi

# Ask before removing installation directory
if [[ -d "${INSTALL_DIR}" ]]; then
    read -p "Remove installation directory ${INSTALL_DIR}? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Removing installation directory..."
        rm -rf "${INSTALL_DIR}"
    else
        log_warn "Installation directory preserved"
    fi
fi

# Remove Docker images (optional)
read -p "Remove Docker images? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Removing Docker images..."
    docker rmi regras-operativas-service:latest 2>/dev/null || true
    docker rmi regras-operativas-service:dev 2>/dev/null || true
fi

log_info "Uninstall complete!"
