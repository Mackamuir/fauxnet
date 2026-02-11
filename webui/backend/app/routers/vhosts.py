"""
Virtual hosts management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from typing import List
import json
import asyncio

from app.models import User
from app.schemas import (
    VhostInfo,
    VhostDetailInfo,
    VhostStatistics,
    ScrapeSitesRequest,
    UpdateScrapeSitesRequest,
    ScrapeResult,
    NginxConfigUpdate,
    FileContentUpdate,
    ScrapeOptionsRequest,
    PhaseSelectionRequest,
    PhaseInfo,
    PhaseStatusResponse
)
from app.auth import get_current_active_user
from app.services.vhosts import VhostsManager
from app.services.progress import ProgressManager
from app.services.vhost_indexer import VhostIndexer

router = APIRouter(prefix="/api/vhosts", tags=["Virtual Hosts"])


@router.get("/list", response_model=List[VhostInfo])
async def list_vhosts(
    include_stats: bool = False,
    current_user: User = Depends(get_current_active_user)
):
    """
    List all virtual hosts

    Args:
        include_stats: If True, include size_bytes and file_count (slower for large datasets).
                      If False (default), these fields will be null for faster listing.
    """
    return await VhostsManager.list_vhosts(include_stats=include_stats)


@router.get("/statistics", response_model=VhostStatistics)
async def get_statistics(
    current_user: User = Depends(get_current_active_user)
):
    """Get vhosts statistics"""
    return await VhostsManager.get_statistics()


@router.get("/{vhost_name}", response_model=VhostDetailInfo)
async def get_vhost(
    vhost_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get details for a specific virtual host"""
    vhost = await VhostsManager.get_vhost(vhost_name)
    if not vhost:
        raise HTTPException(status_code=404, detail="Virtual host not found")
    return vhost


@router.delete("/{vhost_name}")
async def delete_vhost(
    vhost_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a virtual host"""
    deleted = await VhostsManager.delete_vhost(vhost_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Virtual host not found")
    return {"success": True, "message": f"Virtual host '{vhost_name}' deleted successfully"}


@router.get("/scrape/sites")
async def get_scrape_sites(
    current_user: User = Depends(get_current_active_user)
):
    """Get the list of sites configured for scraping"""
    sites = await VhostsManager.get_scrape_sites()
    return {"sites": sites}


@router.put("/scrape/sites")
async def update_scrape_sites(
    request: UpdateScrapeSitesRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Update the list of sites to scrape"""
    success = await VhostsManager.update_scrape_sites(request.sites)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update scrape sites")
    return {"success": True, "message": "Scrape sites updated successfully"}


@router.post("/scrape/start")
async def start_scrape(
    request: ScrapeSitesRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Start the scraping process in the background

    Returns an operation ID that can be used to track progress
    """
    if not request.sites:
        raise HTTPException(status_code=400, detail="No sites provided")

    operation_id = await VhostsManager.start_scrape_async(request.sites, request.options)
    return {"operation_id": operation_id, "message": "Scraping started"}


@router.get("/scrape/status/{operation_id}")
async def get_scrape_status(
    operation_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the current status of a scraping operation (single request)

    This endpoint returns the current state without streaming
    """
    tracker = ProgressManager.get_tracker(operation_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="Operation not found")

    return tracker.to_dict()


@router.get("/scrape/progress/{operation_id}")
async def get_scrape_progress(
    operation_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the current progress of a scraping operation using Server-Sent Events (SSE)

    This endpoint streams progress updates in real-time
    """
    tracker = ProgressManager.get_tracker(operation_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="Operation not found")

    async def event_generator():
        """Generate SSE events"""
        last_status = None
        while True:
            current_tracker = ProgressManager.get_tracker(operation_id)
            if not current_tracker:
                yield f"data: {json.dumps({'error': 'Operation not found'})}\n\n"
                break

            current_data = current_tracker.to_dict()

            # Send update if status changed or operation is still running
            if current_data != last_status:
                yield f"data: {json.dumps(current_data)}\n\n"
                last_status = current_data

            # Stop streaming if completed or error
            if current_tracker.status in ["completed", "error"]:
                break

            await asyncio.sleep(0.5)  # Poll every 500ms

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/scrape/phases/status", response_model=PhaseStatusResponse)
async def get_phases_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get completion status of all scraping phases

    Returns which phases have been completed based on filesystem detection
    """
    # Define phase metadata
    PHASE_METADATA = {
        1: {"name": "Generate CA", "description": "Generate Certificate Authority", "dependencies": []},
        2: {"name": "Download websites", "description": "Download website content", "dependencies": [1]},
        3: {"name": "Generate certificates", "description": "Generate SSL certificates", "dependencies": [1, 2]},
        4: {"name": "Generate hosts", "description": "Generate hosts entries", "dependencies": [2]},
        5: {"name": "Generate nginx configs", "description": "Generate nginx configurations", "dependencies": [2, 3, 4]},
        6: {"name": "Generate landing page", "description": "Generate fauxnet.info page", "dependencies": [3, 4, 5]},
        7: {"name": "Generate summary", "description": "Generate sites summary", "dependencies": [2]},
    }

    # Get completion state from filesystem
    completion_state = await VhostsManager.get_phase_completion_state()

    # Build response
    phases = []
    for phase_num in range(1, 8):
        meta = PHASE_METADATA[phase_num]
        phases.append(PhaseInfo(
            phase_number=phase_num,
            name=meta["name"],
            description=meta["description"],
            completed=completion_state.get(phase_num, False),
            dependencies=meta["dependencies"]
        ))

    return PhaseStatusResponse(phases=phases)


@router.post("/scrape/run-phases")
async def run_specific_phases(
    request: PhaseSelectionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Run specific scraping phases with dependency validation

    Returns operation_id for progress tracking
    """
    # Validate phase numbers are 1-7
    if not all(1 <= p <= 7 for p in request.phases):
        raise HTTPException(status_code=400, detail="Phase numbers must be between 1 and 7")

    # Check if phase 2 is included and sites are provided
    if 2 in request.phases and not request.sites:
        raise HTTPException(status_code=400, detail="Phase 2 (Download websites) requires 'sites' list")

    # Validate dependencies
    is_valid, error_msg = await VhostsManager.validate_phase_dependencies(request.phases)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Start phase execution
    operation_id = await VhostsManager.start_phases_async(
        request.phases,
        request.sites,
        request.options
    )

    return {
        "operation_id": operation_id,
        "message": f"Running phases: {sorted(request.phases)}"
    }


@router.get("/ca/certificate")
async def download_ca_certificate(
    current_user: User = Depends(get_current_active_user)
):
    """Download the CA certificate"""
    cert_path = await VhostsManager.get_ca_certificate_path()
    if not cert_path:
        raise HTTPException(status_code=404, detail="CA certificate not found")
    return FileResponse(cert_path, filename="fauxnet_ca.cer", media_type="application/x-x509-ca-cert")


@router.get("/ca/key")
async def download_ca_key(
    current_user: User = Depends(get_current_active_user)
):
    """Download the CA private key"""
    key_path = await VhostsManager.get_ca_key_path()
    if not key_path:
        raise HTTPException(status_code=404, detail="CA key not found")
    return FileResponse(key_path, filename="fauxnet_ca.key", media_type="application/x-pem-file")


@router.get("/{vhost_name}/nginx/config")
async def get_nginx_config(
    vhost_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get the nginx configuration for a vhost"""
    config = await VhostsManager.get_nginx_config(vhost_name)
    if config is None:
        raise HTTPException(status_code=404, detail="Nginx config not found")
    return {"content": config}


@router.put("/{vhost_name}/nginx/config")
async def update_nginx_config(
    vhost_name: str,
    request: NginxConfigUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update the nginx configuration for a vhost"""
    success = await VhostsManager.update_nginx_config(vhost_name, request.content)
    if not success:
        raise HTTPException(status_code=404, detail="Virtual host not found")
    return {"success": True, "message": "Nginx config updated successfully"}


@router.get("/{vhost_name}/files/{file_path:path}")
async def get_file_content(
    vhost_name: str,
    file_path: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get the content of a file in a vhost"""
    content = await VhostsManager.get_file_content(vhost_name, file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"content": content, "path": file_path}


@router.put("/{vhost_name}/files/{file_path:path}")
async def update_file_content(
    vhost_name: str,
    file_path: str,
    request: FileContentUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update the content of a file in a vhost"""
    success = await VhostsManager.update_file_content(vhost_name, file_path, request.content)
    if not success:
        raise HTTPException(status_code=404, detail="File or vhost not found")
    return {"success": True, "message": "File updated successfully"}


@router.post("/{vhost_name}/upload")
async def upload_file(
    vhost_name: str,
    file: UploadFile = File(...),
    target_path: str = Form(""),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a file to a vhost

    Args:
        vhost_name: Name of the virtual host
        file: File to upload
        target_path: Target directory path (e.g., 'images', 'css/vendor')
                    Leave empty to upload to root. Directories will be created if needed.
    """
    success = await VhostsManager.upload_file(vhost_name, file, target_path)
    if not success:
        raise HTTPException(status_code=404, detail="Virtual host not found or upload failed")

    upload_location = f"{target_path}/{file.filename}" if target_path else file.filename
    return {
        "success": True,
        "message": f"File '{file.filename}' uploaded successfully",
        "path": upload_location
    }


@router.get("/custom/templates")
async def list_custom_templates(
    current_user: User = Depends(get_current_active_user)
):
    """
    List all available custom vhost templates

    Returns a list of templates from /opt/fauxnet/custom_vhost_templates
    or falls back to built-in templates
    """
    templates = await VhostsManager.list_custom_vhost_templates()
    return {"templates": templates}


@router.post("/custom/create")
async def create_custom_vhost(
    request: dict,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a custom virtual host with specified template

    Request body:
    {
        "vhost_name": "example.custom.com",
        "template_type": "regular_website" or "c2_redirector",
        "backend_c2_server": "https://backend-c2.example.com" (optional, required for c2_redirector),
        "ip_address": "192.168.1.100" (optional, defaults to "1.0.0.0")
    }
    """
    vhost_name = request.get("vhost_name")
    template_type = request.get("template_type")
    backend_c2_server = request.get("backend_c2_server")
    ip_address = request.get("ip_address")

    if not vhost_name:
        raise HTTPException(status_code=400, detail="vhost_name is required")
    if not template_type:
        raise HTTPException(status_code=400, detail="template_type is required")

    result = await VhostsManager.create_custom_vhost(vhost_name, template_type, backend_c2_server, ip_address)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create custom vhost"))

    return result


@router.get("/{vhost_name}/logs/{log_type}")
async def get_vhost_logs(
    vhost_name: str,
    log_type: str,
    lines: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get nginx logs for a virtual host

    Args:
        vhost_name: Name of the virtual host
        log_type: Either 'access' or 'error'
        lines: Number of lines to return (default 100, max 1000)

    Returns:
        Log content as text
    """
    if log_type not in ['access', 'error']:
        raise HTTPException(status_code=400, detail="log_type must be 'access' or 'error'")

    # Limit lines to prevent excessive memory usage
    lines = min(lines, 1000)

    content = await VhostsManager.get_vhost_logs(vhost_name, log_type, lines)

    if content is None:
        raise HTTPException(status_code=404, detail="Log file not found")

    return {"content": content, "log_type": log_type, "lines": lines}


@router.post("/index/refresh")
async def refresh_index(
    include_stats: bool = True,
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually trigger a full refresh of the vhost index

    Args:
        include_stats: Whether to calculate size/file count (default: True)

    This will rebuild the entire vhost index from the filesystem.
    Use this when you want to ensure the index is completely up-to-date.
    """
    await VhostIndexer.rebuild_index(include_stats=include_stats)
    last_refresh = VhostIndexer.get_last_refresh_time()

    return {
        "success": True,
        "message": "Vhost index refreshed successfully",
        "last_refresh": last_refresh.isoformat() if last_refresh else None
    }


@router.get("/index/status")
async def get_index_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the status of the vhost index

    Returns information about when the index was last refreshed
    and how many vhosts are currently indexed.
    """
    last_refresh = VhostIndexer.get_last_refresh_time()
    stats = VhostIndexer.get_statistics()

    return {
        "last_refresh": last_refresh.isoformat() if last_refresh else None,
        "total_indexed": stats["total_vhosts"],
        "refresh_interval_hours": VhostIndexer.REFRESH_INTERVAL_HOURS
    }
