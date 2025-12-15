"""
API routers
"""
from app.routers import auth, services, core, system, vhosts, dns

__all__ = ["auth", "services", "core", "system", "vhosts", "dns"]
