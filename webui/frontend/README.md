# Fauxnet Web UI - Frontend

React-based frontend for the Fauxnet Management Interface.

## Features

- **Dashboard**: Real-time system monitoring and status overview
- **Service Management**: Control systemd services and Docker containers
- **CORE Network**: Manage CORE topology sessions
- **Virtual Hosts**: Manage virtual hosts and web content (coming soon)
- **Settings**: User profile and system configuration

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **React Router** - Routing
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **Lucide React** - Icons

## Installation

### Prerequisites

- Node.js 18+ and npm

### Setup

1. Install dependencies:
```bash
cd webui/frontend
npm install
```

2. Configure API URL (optional):
```bash
# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env
```

## Running

### Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

### Production Build

```bash
npm run build
```

The built files will be in the `dist/` directory. Serve them with any static file server or reverse proxy.

## Project Structure

```
src/
├── components/       # Reusable UI components
│   └── Layout.jsx    # Main layout with sidebar
├── context/          # React context providers
│   └── AuthContext.jsx
├── pages/            # Page components
│   ├── Login.jsx
│   ├── Dashboard.jsx
│   ├── Services.jsx
│   ├── Core.jsx
│   ├── VirtualHosts.jsx
│   └── Settings.jsx
├── services/         # API and external services
│   └── api.js        # Axios instance with auth
├── App.jsx           # Main app component with routing
├── main.jsx          # Entry point
└── index.css         # Global styles
```

## Default Login

**Username**: admin
**Password**: admin

Change the password immediately after first login!

## API Integration

The frontend communicates with the FastAPI backend via `/api` endpoints. All requests include JWT authentication tokens.

Key API endpoints:
- `/api/auth/*` - Authentication
- `/api/services/*` - Service management
- `/api/core/*` - CORE network management
- `/api/system/*` - System information

## Development

### Adding a New Page

1. Create component in `src/pages/`
2. Add route in `src/App.jsx`
3. Add navigation link in `src/components/Layout.jsx`

### Adding a New API Call

1. Use the `api` instance from `src/services/api.js`
2. All requests automatically include auth headers
3. 401 responses automatically redirect to login

## Production Deployment

### Using Nginx

Build the app and serve with Nginx:

```bash
npm run build
```

Nginx config:
```nginx
server {
    listen 80;
    server_name fauxnet.local;

    root /home/fauxnet/fauxnet/webui/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Using Docker

Create a Dockerfile:
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Future Enhancements

- [ ] Virtual host management UI
- [ ] Real-time log streaming
- [ ] Topology visualization
- [ ] Configuration file editing
- [ ] User management (for superusers)
- [ ] Audit log viewer
- [ ] Dark/light theme toggle
