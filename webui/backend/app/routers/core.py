"""
CORE network emulator management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List
import json
import uuid

from app.models import User
from app.schemas import CoreSessionInfo
from app.auth import get_current_active_user, get_current_user_from_query
from app.services import CoreManager

router = APIRouter(prefix="/api/core", tags=["CORE Network Emulator"])

core_manager = CoreManager()


async def event_stream(task_id: str):
    """SSE event stream generator"""
    async for progress in core_manager.stream_loading_progress(task_id):
        yield f"data: {json.dumps(progress)}\n\n"


@router.get("/session", response_model=CoreSessionInfo)
async def get_current_session(
    current_user: User = Depends(get_current_active_user)
):
    """Get information about the current CORE session"""
    return await core_manager.get_session_info()


@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_active_user)
):
    """List all CORE sessions"""
    sessions = await core_manager.list_sessions()
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a CORE session"""
    success = await core_manager.delete_session(session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session {session_id}"
        )

    return {"message": f"Session {session_id} deleted successfully"}


@router.post("/load")
async def load_topology(
    xml_file: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """Load a CORE topology from XML file in background with progress tracking

    Returns a task_id that can be used to monitor progress via SSE endpoint.
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())

    # Start background task
    background_tasks.add_task(
        core_manager.load_topology_background,
        xml_file,
        task_id
    )

    return {
        "message": "Topology loading started",
        "task_id": task_id,
        "file": xml_file
    }


@router.get("/load/progress/{task_id}")
async def get_load_progress(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get current progress of a topology loading task"""
    progress = core_manager.get_loading_progress(task_id)

    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    return progress


@router.get("/load/stream/{task_id}")
async def stream_load_progress(
    task_id: str,
    token: str,
    current_user: User = Depends(get_current_user_from_query)
):
    """Stream topology loading progress via Server-Sent Events (SSE)

    Note: Authentication is handled via token query parameter for SSE compatibility,
    since EventSource API doesn't support custom headers.
    """
    return StreamingResponse(
        event_stream(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.delete("/load/progress/{task_id}")
async def clear_load_progress(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Clear progress tracking for a completed task"""
    core_manager.clear_loading_progress(task_id)
    return {"message": f"Progress cleared for task {task_id}"}


@router.get("/topologies")
async def list_topologies(
    current_user: User = Depends(get_current_active_user)
):
    """List available topology XML files"""
    topologies = await core_manager.get_topology_files()
    return {"topologies": topologies}


@router.get("/daemon/logs")
async def get_daemon_logs(
    lines: int = 10,
    current_user: User = Depends(get_current_active_user)
):
    """Get recent logs from core-daemon systemd service"""
    logs = await core_manager.get_daemon_logs(lines)
    return {"logs": logs}
