"""
System information endpoints
"""
from fastapi import APIRouter, Depends
import psutil
import socket
import platform

from app.models import User
from app.schemas import SystemInfo
from app.auth import get_current_active_user

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/info", response_model=SystemInfo)
async def get_system_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get system information"""
    # Get CPU info
    cpu_count = psutil.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=1)

    # Get memory info
    memory = psutil.virtual_memory()
    memory_total = memory.total
    memory_used = memory.used
    memory_percent = memory.percent

    # Get disk info
    disk = psutil.disk_usage('/')
    disk_total = disk.total
    disk_used = disk.used
    disk_percent = disk.percent

    # Get hostname
    hostname = socket.gethostname()

    # Get platform
    platform_name = platform.system()

    return SystemInfo(
        hostname=hostname,
        platform=platform_name,
        cpu_count=cpu_count,
        cpu_percent=cpu_percent,
        memory_total=memory_total,
        memory_used=memory_used,
        memory_percent=memory_percent,
        disk_total=disk_total,
        disk_used=disk_used,
        disk_percent=disk_percent
    )
