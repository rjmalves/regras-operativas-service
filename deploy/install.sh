#!/bin/bash
# =============================================================================
# Regras Operativas Service - Install Script
# =============================================================================
# Usage: sudo ./install.sh
# =============================================================================

set -e

SERVICE_NAME="regras-operativas"
INSTALL_DIR="/opt/regras-operativas-service"
SERVICE_FILE="${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    log_error "Docker Compose is not installed"
    exit 1
fi

log_info "Installing ${SERVICE_NAME}..."

# Create installation directory
log_info "Creating installation directory: ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"

# Copy application files
log_info "Copying application files..."
cp -r "${PROJECT_DIR}/app" "${INSTALL_DIR}/"
cp "${PROJECT_DIR}/main.py" "${INSTALL_DIR}/"
cp "${PROJECT_DIR}/pyproject.toml" "${INSTALL_DIR}/"
cp "${PROJECT_DIR}/Dockerfile" "${INSTALL_DIR}/"
cp "${PROJECT_DIR}/docker-compose.yml" "${INSTALL_DIR}/"
cp "${PROJECT_DIR}/README.md" "${INSTALL_DIR}/" 2>/dev/null || true
cp "${PROJECT_DIR}/regras.json" "${INSTALL_DIR}/" 2>/dev/null || true
cp "${PROJECT_DIR}/regras_reservatorios.csv" "${INSTALL_DIR}/" 2>/dev/null || true

# Copy environment file template if not exists
if [[ ! -f "${INSTALL_DIR}/.env" ]]; then
    if [[ -f "${PROJECT_DIR}/.env.example" ]]; then
        cp "${PROJECT_DIR}/.env.example" "${INSTALL_DIR}/.env"
        log_warn "Created .env from template - please configure!"
    else
        log_warn "No .env file found - please create one"
    fi
fi

# Install systemd service
log_info "Installing systemd service..."
cp "${SCRIPT_DIR}/${SERVICE_FILE}" "/etc/systemd/system/"
systemctl daemon-reload

# Build Docker image
log_info "Building Docker image..."
cd "${INSTALL_DIR}"
docker compose build

# Enable and start service
log_info "Enabling and starting service..."
systemctl enable "${SERVICE_NAME}"
systemctl start "${SERVICE_NAME}"

# Check status
sleep 3
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    log_info "Service started successfully!"
    log_info "Check status: systemctl status ${SERVICE_NAME}"
    log_info "View logs: journalctl -u ${SERVICE_NAME} -f"
else
    log_error "Service failed to start. Check logs:"
    journalctl -u "${SERVICE_NAME}" --no-pager -n 20
    exit 1
fi

log_info "Installation complete!"
