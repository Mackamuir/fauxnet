#!/bin/bash
set -e

# Fauxnet Uninstallation Script

INSTALL_DIR="/opt/fauxnet"

echo "=== Fauxnet Uninstallation ==="

echo "Stopping and disabling services..."
sudo systemctl disable fauxnet.target || true
sudo systemctl stop fauxnet.target || true

echo "Removing systemd service files..."
sudo rm -f /etc/systemd/system/fauxnet.target
sudo rm -f /etc/systemd/system/fauxnet@api.service
sudo rm -f /etc/systemd/system/fauxnet@webui.service
sudo systemctl daemon-reload

echo "Removing installation directory..."
sudo rm -rf "$INSTALL_DIR"

echo ""
echo "=== Uninstall Complete! ==="
