"""
Service management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models import User, ServiceLog
from app.schemas import ServiceStatus, ServiceAction, ServiceLogSchema
from app.auth import get_current_active_user
from app.services import SystemdManager, DockerManager

router = APIRouter(prefix="/api/services", tags=["Services"])

systemd = SystemdManager()
docker = DockerManager()


@router.get("/systemd/{service_name}", response_model=ServiceStatus)
async def get_systemd_service_status(
    service_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get status of a systemd service"""
    return await systemd.get_service_status(service_name)


@router.post("/systemd/{service_name}/action")
async def control_systemd_service(
    service_name: str,
    action: ServiceAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Control a systemd service (start, stop, restart, enable, disable)"""
    success = False
    message = ""

    if action.action == "start":
        success = await systemd.start_service(service_name)
        message = f"Started {service_name}" if success else f"Failed to start {service_name}"
    elif action.action == "stop":
        success = await systemd.stop_service(service_name)
        message = f"Stopped {service_name}" if success else f"Failed to stop {service_name}"
    elif action.action == "restart":
        success = await systemd.restart_service(service_name)
        message = f"Restarted {service_name}" if success else f"Failed to restart {service_name}"
    elif action.action == "enable":
        success = await systemd.enable_service(service_name)
        message = f"Enabled {service_name}" if success else f"Failed to enable {service_name}"
    elif action.action == "disable":
        success = await systemd.disable_service(service_name)
        message = f"Disabled {service_name}" if success else f"Failed to disable {service_name}"

    # Log the action
    log_entry = ServiceLog(
        service_name=service_name,
        action=action.action,
        status="success" if success else "failed",
        message=message,
        user_id=current_user.id
    )
    db.add(log_entry)
    await db.commit()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"message": message, "success": success}


@router.get("/systemd/{service_name}/logs")
async def get_systemd_service_logs(
    service_name: str,
    lines: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """Get logs for a systemd service"""
    logs = await systemd.get_service_logs(service_name, lines)
    return {"logs": logs}


@router.get("/docker/containers")
async def list_docker_containers(
    all: bool = False,
    current_user: User = Depends(get_current_active_user)
):
    """List all Docker containers"""
    containers = docker.list_containers(all=all)
    return {"containers": containers}


@router.get("/docker/containers/{container_name}")
async def get_docker_container_status(
    container_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get status of a Docker container"""
    status = docker.get_container_status(container_name)
    return status


@router.post("/docker/containers/{container_name}/start")
async def start_docker_container(
    container_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Start a Docker container"""
    success = docker.start_container(container_name)
    message = f"Started container {container_name}" if success else f"Failed to start container {container_name}"

    # Log the action
    log_entry = ServiceLog(
        service_name=f"docker:{container_name}",
        action="start",
        status="success" if success else "failed",
        message=message,
        user_id=current_user.id
    )
    db.add(log_entry)
    await db.commit()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"message": message, "success": success}


@router.post("/docker/containers/{container_name}/stop")
async def stop_docker_container(
    container_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Stop a Docker container"""
    success = docker.stop_container(container_name)
    message = f"Stopped container {container_name}" if success else f"Failed to stop container {container_name}"

    # Log the action
    log_entry = ServiceLog(
        service_name=f"docker:{container_name}",
        action="stop",
        status="success" if success else "failed",
        message=message,
        user_id=current_user.id
    )
    db.add(log_entry)
    await db.commit()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"message": message, "success": success}


@router.post("/docker/containers/{container_name}/restart")
async def restart_docker_container(
    container_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Restart a Docker container"""
    success = docker.restart_container(container_name)
    message = f"Restarted container {container_name}" if success else f"Failed to restart container {container_name}"

    # Log the action
    log_entry = ServiceLog(
        service_name=f"docker:{container_name}",
        action="restart",
        status="success" if success else "failed",
        message=message,
        user_id=current_user.id
    )
    db.add(log_entry)
    await db.commit()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"message": message, "success": success}


@router.get("/docker/containers/{container_name}/logs")
async def get_docker_container_logs(
    container_name: str,
    lines: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """Get logs from a Docker container"""
    logs = docker.get_container_logs(container_name, lines)
    return {"logs": logs}


@router.get("/logs", response_model=List[ServiceLogSchema])
async def get_service_logs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get service management logs"""
    from sqlalchemy import select, desc

    result = await db.execute(
        select(ServiceLog)
        .order_by(desc(ServiceLog.timestamp))
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()
    return logs
