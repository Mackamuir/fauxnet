"""
Community service management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models import User, ServiceLog
from app.schemas import (
    CommunityServiceStatus,
    CommunityNodeStatus,
    CommunityNodeAction,
    CommunityConfig,
    CommunityConfigUpdate
)
from app.auth import get_current_active_user
from app.services.community import CommunityManager

router = APIRouter(prefix="/api/community", tags=["Community"])

community = CommunityManager()


async def get_node_name(node_id: str) -> str:
    """Helper function to get node name from node ID"""
    nodes = await community.get_community_nodes()
    node_name = next((n["name"] for n in nodes if n["id"] == node_id), None)
    if not node_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found or does not have Community service"
        )
    return node_name


@router.get("/status", response_model=CommunityServiceStatus)
async def get_community_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get status of Community service across all nodes"""
    return await community.get_service_status()


@router.get("/nodes/{node_id}/status", response_model=CommunityNodeStatus)
async def get_node_status(
    node_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get status of Community service on a specific node"""
    session_id = await community.get_session_id()
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CORE session found"
        )

    # Get node name (simplified - in production you might want to cache this)
    nodes = await community.get_community_nodes()
    node_name = next((n["name"] for n in nodes if n["id"] == node_id), f"Node-{node_id}")

    node_status = await community.get_node_status(session_id, node_id, node_name)
    return node_status


@router.post("/nodes/{node_id}/action")
async def control_node_service(
    node_id: str,
    action: CommunityNodeAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Control Community service on a specific node (start, stop, restart)"""
    session_id = await community.get_session_id()
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CORE session found"
        )

    # Get node name
    node_name = await get_node_name(node_id)

    success = False
    message = ""

    if action.action == "start":
        success = await community.start_service(node_id, node_name)
        message = f"Started Community service on node {node_id}" if success else f"Failed to start Community service on node {node_id}"
    elif action.action == "stop":
        success = await community.stop_service(node_id, node_name)
        message = f"Stopped Community service on node {node_id}" if success else f"Failed to stop Community service on node {node_id}"
    elif action.action == "restart":
        success = await community.restart_service(node_id, node_name)
        message = f"Restarted Community service on node {node_id}" if success else f"Failed to restart Community service on node {node_id}"

    # Log the action
    log_entry = ServiceLog(
        service_name=f"community:node-{node_id}",
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


@router.get("/nodes/{node_id}/config", response_model=CommunityConfig)
async def get_node_config(
    node_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get Community configuration from a specific node"""
    session_id = await community.get_session_id()
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CORE session found"
        )

    # Get node name
    node_name = await get_node_name(node_id)

    config = await community.get_config(node_id, node_name)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found for node {node_id}"
        )

    return config


@router.put("/nodes/{node_id}/config")
async def update_node_config(
    node_id: str,
    config_update: CommunityConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update Community configuration on a specific node"""
    session_id = await community.get_session_id()
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CORE session found"
        )

    # Get node name
    node_name = await get_node_name(node_id)

    success = await community.update_config(node_id, node_name, config_update.config)

    # Log the action
    log_entry = ServiceLog(
        service_name=f"community:node-{node_id}",
        action="update_config",
        status="success" if success else "failed",
        message=f"Updated Community configuration on node {node_id}" if success else f"Failed to update Community configuration on node {node_id}",
        user_id=current_user.id
    )
    db.add(log_entry)
    await db.commit()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration for node {node_id}"
        )

    return {"message": f"Configuration updated for node {node_id}", "success": success}


@router.get("/nodes/{node_id}/logs")
async def get_node_logs(
    node_id: str,
    lines: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """Get logs from Community service on a specific node"""
    session_id = await community.get_session_id()
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CORE session found"
        )

    # Get node name
    node_name = await get_node_name(node_id)

    logs = await community.get_logs(node_id, node_name, lines)
    return {"logs": logs}


@router.get("/config/base", response_model=CommunityConfig)
async def get_base_config(
    current_user: User = Depends(get_current_active_user)
):
    """Get base Community configuration from /opt/fauxnet/core/community/community.conf

    This is the template config file. Can be accessed without nodes being online.
    """
    config = await community.get_base_config()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base configuration file not found at /opt/fauxnet/core/community/community.conf"
        )
    return config


@router.put("/config/base")
async def update_base_config(
    config_update: CommunityConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update base Community configuration at /opt/fauxnet/core/community/community.conf

    This updates the template config file. Does not require nodes to be online.
    """
    success = await community.update_base_config(config_update.config)

    # Log the action
    log_entry = ServiceLog(
        service_name="community:base-config",
        action="update_config",
        status="success" if success else "failed",
        message="Updated base Community configuration" if success else "Failed to update base Community configuration",
        user_id=current_user.id
    )
    db.add(log_entry)
    await db.commit()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update base configuration"
        )

    return {"message": "Base configuration updated successfully", "success": success}


@router.put("/config/all-nodes")
async def update_all_nodes_config(
    config_update: CommunityConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update Community configuration on all nodes at once

    This will apply the same configuration to all nodes with the Community service.
    Requires an active CORE session.
    """
    result = await community.update_all_nodes_config(config_update.config)

    # Log the action
    log_entry = ServiceLog(
        service_name="community:all-nodes",
        action="update_config",
        status="success" if result["success"] else "partial" if result["success_count"] > 0 else "failed",
        message=result["message"],
        user_id=current_user.id
    )
    db.add(log_entry)
    await db.commit()

    return result
