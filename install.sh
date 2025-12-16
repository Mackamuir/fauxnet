#!/bin/bash
set -e

# Fauxnet Installation Script

INSTALL_DIR="/opt/fauxnet"
WEBUI_DIR="$INSTALL_DIR/webui"
BACKEND_DIR="$WEBUI_DIR/backend"
FRONTEND_DIR="$WEBUI_DIR/frontend"
TEMPLATES_DIR="$INSTALL_DIR/templates"
TOPOLOGIES_DIR="$INSTALL_DIR/topologies"
CORE_DIR="$INSTALL_DIR/core"

echo "=== Fauxnet Installation ==="

# Install CORE
install_core() {
    if ! [ -f "/usr/lib/systemd/system/core-daemon.service" ]; then
        echo "Installing CORE..."
        git clone https://github.com/coreemu/core.git /tmp/core || true
        cd /tmp/core && ./setup.sh
        grep -q "custom_services_dir = $CORE_DIR/custom_services" /opt/core/etc/core.conf || \
            sudo sed -i "/\[core-daemon\]/a custom_services_dir = $CORE_DIR/custom_services" /opt/core/etc/core.conf
    fi
}

# Install system dependencies
install_deps() {
    echo "Installing system dependencies..."
    sudo systemctl mask kea-dhcp4-server kea-dhcp6-server kea-ddns-server isc-dhcp-server isc-dhcp6-server nginx || true
    sudo apt update
    sudo apt install -y isc-dhcp-server isc-dhcp-client kea openssh-client openssh-server keepalived nginx python3 python3-pip python3-venv nodejs npm pipx
}

# Copy files to installation directories
install_folders() {
    echo "Creating directories and copying files..."
    sudo mkdir -p "$BACKEND_DIR"
    sudo cp -r webui/backend/* "$BACKEND_DIR/"
    sudo mkdir -p "$FRONTEND_DIR"
    sudo cp -r webui/frontend/* "$FRONTEND_DIR/"
    sudo mkdir -p "$TEMPLATES_DIR"
    sudo cp -r templates/* "$TEMPLATES_DIR/"
    sudo mkdir -p "$TOPOLOGIES_DIR"
    sudo cp -r topologies/* "$TOPOLOGIES_DIR/"
    sudo mkdir -p "$CORE_DIR"
    sudo cp -r core/* "$CORE_DIR/"
    # Folders that will eventually be used, but just not quite yet.
    sudo mkdir -p "$INSTALL_DIR/config"
    sudo mkdir -p "$INSTALL_DIR/named"
    sudo mkdir -p "$INSTALL_DIR/vhosts_config"
    sudo mkdir -p "$INSTALL_DIR/vhosts_www"
}

# Install backend
install_backend() {
    echo "Installing backend..."
    pipx install uvicorn --include-deps || pipx upgrade uvicorn
    pipx runpip uvicorn install -r "$BACKEND_DIR/requirements.txt"
    sudo cp .env.example "$BACKEND_DIR/.env"
    echo "Initializing database..."
    cd "$BACKEND_DIR" && ~/.local/pipx/venvs/uvicorn/bin/python init_admin.py
}

# Install frontend
install_frontend() {
    echo "Installing frontend..."
    sudo chown -R root:root "$FRONTEND_DIR"
    cd "$FRONTEND_DIR" && sudo npm install
}

# Install systemd services
install_services() {
    echo "Installing systemd services..."
    sudo cp systemd/* /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now fauxnet.target
}

# Main installation
install_deps
install_core
install_folders
install_backend
install_frontend
install_services

echo ""
echo "=== Installation Complete! ==="
echo "Backend installed to: $BACKEND_DIR"
echo "Frontend installed to: $FRONTEND_DIR"
echo ""
echo "Next steps:"
echo "1. Edit $BACKEND_DIR/.env and update SECRET_KEY"
echo "2. Start backend: cd $BACKEND_DIR && python3 run.py"
echo "3. Start frontend dev server: cd $FRONTEND_DIR && npm run dev"
