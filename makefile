.PHONY: all install install-deps install-backend install-frontend clean uninstall

INSTALL_DIR = /opt/fauxnet
WEBUI_DIR = $(INSTALL_DIR)/webui
BACKEND_DIR = $(WEBUI_DIR)/backend
FRONTEND_DIR = $(WEBUI_DIR)/frontend

all: install

install-core:
	git clone https://github.com/coreemu/core.git /tmp/core
	cd /tmp/core
	sudo ./setup.sh

install-deps:
	@echo "Installing system dependencies..."
	sudo systemctl mask kea-dhcp4-server kea-dhcp6-server kea-ddns-server isc-dhcp-server isc-dhcp6-server nginx || true
	sudo apt update
	sudo apt install -y isc-dhcp-server isc-dhcp-client kea openssh-client openssh-server keepalived nginx python3 python3-pip python3-venv nodejs npm
	@echo "Configuring CORE custom services directory..."
	grep -q 'custom_services_dir = /opt/fauxnet/core/custom_services' /opt/core/etc/core.conf || \
	  sudo sed -i '/\[core-daemon\]/a custom_services_dir = /opt/fauxnet/core/custom_services' /opt/core/etc/core.conf

install-backend: install-deps
	@echo "Installing backend to $(BACKEND_DIR)..."
	sudo mkdir -p $(BACKEND_DIR)
	sudo cp -r webui/backend/* $(BACKEND_DIR)/
	sudo chown -R root:root $(BACKEND_DIR)
	@echo "Installing Python dependencies..."
	cd $(BACKEND_DIR) && sudo python3 -m pip install -r requirements.txt --break-system-packages
	@echo "Setting up backend environment..."
	sudo cp webui/backend/.env.example $(BACKEND_DIR)/.env
	@echo "Initializing database..."
	cd $(BACKEND_DIR) && sudo python3 init_admin.py

install-frontend: install-deps
	@echo "Installing frontend to $(FRONTEND_DIR)..."
	sudo mkdir -p $(FRONTEND_DIR)
	sudo cp -r webui/frontend/* $(FRONTEND_DIR)/
	sudo chown -R root:root $(FRONTEND_DIR)
	@echo "Installing Node.js dependencies..."
	cd $(FRONTEND_DIR) && sudo npm install

install: install-core install-backend install-frontend
	@echo "Installation complete!"
	@echo "Backend installed to: $(BACKEND_DIR)"
	@echo "Frontend installed to: $(FRONTEND_DIR)"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit $(BACKEND_DIR)/.env and update SECRET_KEY"
	@echo "2. Start backend: cd $(BACKEND_DIR) && python3 run.py"
	@echo "3. Start frontend dev server: cd $(FRONTEND_DIR) && npm run dev"

clean:
	@echo "Cleaning build artifacts..."
	sudo rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/dist
	sudo rm -rf $(BACKEND_DIR)/__pycache__ $(BACKEND_DIR)/.venv $(BACKEND_DIR)/fauxnet.db

uninstall:
	@echo "Uninstalling webui from $(WEBUI_DIR)..."
	sudo rm -rf $(WEBUI_DIR)
	@echo "Uninstall complete!"
