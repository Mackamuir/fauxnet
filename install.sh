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
        (cd /tmp/core && ./setup.sh)
        grep -q "custom_services_dir = $CORE_DIR/custom_services" /opt/core/etc/core.conf || \
            sudo sed -i "/\[core-daemon\]/a custom_services_dir = $CORE_DIR/custom_services" /opt/core/etc/core.conf
    fi
}

# Install system dependencies
install_deps() {
    echo "Installing system dependencies..."
    sudo systemctl mask kea-dhcp4-server kea-dhcp6-server kea-ddns-server isc-dhcp-server isc-dhcp-server6 kea-dhcp-ddns-server nginx || true
    sudo apt update
    # Core Packages
    sudo apt install -y isc-dhcp-server isc-dhcp-client kea openssh-client openssh-server keepalived nginx apparmor-utils
    # Fauxnet Packages
    sudo apt install -y python3 python3-pip python3-venv nodejs npm
    # Community Packages
    sudo apt install -y nmap curl
}

# System config changes to allow all features of core and fauxnet to work
make_system_changes() {
    sudo aa-disable /etc/apparmor.d/usr.sbin.kea-dhcp4
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
    sudo python3 -m venv "$BACKEND_DIR/venv"
    sudo "$BACKEND_DIR/venv/bin/pip" install --upgrade pip
    sudo "$BACKEND_DIR/venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
    sudo cp .env.example "$BACKEND_DIR/.env"
    echo "Initializing database..."
    (cd "$BACKEND_DIR" && "$BACKEND_DIR/venv/bin/python" init_admin.py)
}

# Install frontend
install_frontend() {
    echo "Installing frontend..."
    sudo chown -R root:root "$FRONTEND_DIR"
    (cd "$FRONTEND_DIR" && sudo npm install)
}

# Install systemd services
install_services() {
    echo "Installing systemd services..."
    sudo cp ./systemd/* /etc/systemd/system/
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
echo "visit https://localhost/ to get started"
