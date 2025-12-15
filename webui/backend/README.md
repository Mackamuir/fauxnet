# Fauxnet Web UI - Backend

FastAPI-based backend for the Fauxnet Management Interface.

## Features

- **Authentication & Authorization**: JWT-based auth with role-based access control
- **Service Management**: Control systemd services and Docker containers
- **CORE Network Management**: Manage CORE topology sessions
- **System Monitoring**: Real-time system information
- **Audit Logging**: Track all service management actions

## Installation

### Prerequisites

- Python 3.12+
- systemd (for service management)
- Docker (for container management)
- CORE Network Emulator

### Setup

1. Install dependencies:
```bash
cd webui/backend
pip install -r requirements.txt
```

2. Create configuration file:
```bash
cp .env.example .env
# Edit .env and change SECRET_KEY and other settings
```

3. Initialize database and create admin user:
```bash
python init_admin.py
```

## Running

### Development Server

```bash
python run.py
```

The API will be available at http://localhost:8000

### Production Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or use systemd service (create `/etc/systemd/system/fauxnet-webui.service`):

```ini
[Unit]
Description=Fauxnet Web UI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/fauxnet/fauxnet/webui/backend
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## API Documentation

Once running, visit:
- Interactive API docs: http://localhost:8000/docs
- Alternative API docs: http://localhost:8000/redoc

## Default Credentials

**Username**: admin
**Password**: admin

**IMPORTANT**: Change the default password immediately after first login!

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login and get access token
- `POST /api/auth/register` - Register new user (admin only)
- `GET /api/auth/me` - Get current user info

### Services
- `GET /api/services/systemd/{service_name}` - Get service status
- `POST /api/services/systemd/{service_name}/action` - Control service
- `GET /api/services/systemd/{service_name}/logs` - Get service logs
- `GET /api/services/docker/containers` - List Docker containers
- `POST /api/services/docker/containers/{name}/start` - Start container
- `POST /api/services/docker/containers/{name}/stop` - Stop container
- `POST /api/services/docker/containers/{name}/restart` - Restart container

### CORE Network
- `GET /api/core/session` - Get current CORE session info
- `GET /api/core/sessions` - List all sessions
- `DELETE /api/core/sessions/{id}` - Delete a session
- `POST /api/core/load` - Load a topology
- `GET /api/core/topologies` - List available topologies

### System
- `GET /api/system/info` - Get system information

## Security Notes

1. **Change the SECRET_KEY** in `.env` to a random string in production
2. **Change default admin password** immediately
3. Use HTTPS in production (configure reverse proxy like Nginx)
4. Restrict CORS origins in production
5. Run with appropriate user permissions (requires root for systemd/CORE management)

## Development

### Database Migrations

The application uses SQLAlchemy. To modify the database schema:

1. Edit models in `app/models.py`
2. The database will auto-create tables on startup
3. For production, consider using Alembic for migrations

### Adding New Endpoints

1. Create a new router in `app/routers/`
2. Add business logic in `app/services/`
3. Define schemas in `app/schemas.py`
4. Register router in `app/main.py`
