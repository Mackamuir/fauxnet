"""
DNS configuration management API endpoints
"""

import os
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from app.models import User
from app.schemas import (
    DNSConfiguration,
    DNSGenerationOptions,
    DNSHostsFile,
    DNSDelegationsConfig,
    DNSZoneInfo,
    DNSGenerationResult,
    DNSStatus,
    UpdateHostsFileRequest,
    UpdateDelegationsRequest,
    AddCustomDNSEntryRequest,
    RemoveCustomDNSEntryRequest,
    AddMailHostRequest,
    RemoveMailHostRequest
)
from app.services.dns import DNSService
from app.auth import get_current_active_user

router = APIRouter(prefix="/api/dns", tags=["DNS"])
dns_service = DNSService()


@router.get("/status", response_model=DNSStatus)
async def get_dns_status(current_user: User = Depends(get_current_active_user)):
    """Get current DNS configuration status"""
    try:
        return dns_service.get_status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting DNS status: {str(e)}"
        )


@router.get("/config", response_model=DNSConfiguration)
async def get_dns_config(current_user: User = Depends(get_current_active_user)):
    """Get current DNS configuration settings"""
    return dns_service.default_config


@router.put("/config", response_model=DNSConfiguration)
async def update_dns_config(
    config: DNSConfiguration,
    current_user: User = Depends(get_current_active_user)
):
    """Update DNS configuration settings"""
    # In a full implementation, this would persist to database
    # For now, we just validate and return
    dns_service.default_config = config
    return config


@router.get("/hosts", response_model=List[DNSHostsFile])
async def get_hosts_files(current_user: User = Depends(get_current_active_user)):
    """Get all configured hosts files with their contents"""
    try:
        return dns_service.get_hosts_files()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading hosts files: {str(e)}"
        )


@router.get("/hosts/{file_type}", response_model=DNSHostsFile)
async def get_hosts_file(
    file_type: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific hosts file (web, mail, or extra)"""
    try:
        hosts_files = dns_service.get_hosts_files()
        for hf in hosts_files:
            if hf.name == file_type:
                return hf

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hosts file '{file_type}' not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading hosts file: {str(e)}"
        )


@router.put("/hosts/{file_type}")
async def update_hosts_file(
    file_type: str,
    request: UpdateHostsFileRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Update a hosts file with new content

    For vhosts: file_type should be the vhost name (e.g., 'example.com')
    For backbone: file_type should be 'backbone'
    For mail: file_type should be 'mail'
    """
    try:
        config = dns_service.default_config

        # Determine file path based on type
        if file_type == "mail":
            file_path = config.mail_hosts_path
        elif file_type == "backbone":
            file_path = config.backbone_hosts_path
        else:
            # Assume it's a vhost name - look in vhosts_config directory
            file_path = os.path.join(config.vhosts_config_dir, file_type, "hosts")
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vhost '{file_type}' not found"
                )

        # Update the file
        dns_service.update_hosts_file(file_path, request.content)

        return {"success": True, "message": f"Hosts file '{file_type}' updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating hosts file: {str(e)}"
        )


@router.get("/delegations", response_model=DNSDelegationsConfig)
async def get_delegations(current_user: User = Depends(get_current_active_user)):
    """Get DNS delegations configuration"""
    try:
        config = dns_service.default_config
        return dns_service.parse_delegations_file(config.delegations_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading delegations: {str(e)}"
        )


@router.put("/delegations")
async def update_delegations(
    request: UpdateDelegationsRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Update DNS delegations configuration"""
    try:
        config = dns_service.default_config
        dns_service.update_delegations_file(config.delegations_path, request.delegations)

        return {"success": True, "message": "Delegations updated successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating delegations: {str(e)}"
        )


@router.get("/zones", response_model=List[DNSZoneInfo])
async def get_zones(current_user: User = Depends(get_current_active_user)):
    """Get list of generated DNS zone files"""
    try:
        return dns_service.get_zone_files()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading zones: {str(e)}"
        )


@router.get("/zones/{zone_name}/content")
async def get_zone_content(
    zone_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get content of a specific zone file"""
    try:
        # Find the zone file
        zones = dns_service.get_zone_files()
        zone_path = None

        for zone in zones:
            if zone.name == zone_name:
                zone_path = zone.path
                break

        if not zone_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{zone_name}' not found"
            )

        content = dns_service.get_zone_content(zone_path)
        return {"name": zone_name, "content": content}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading zone content: {str(e)}"
        )


@router.post("/generate", response_model=DNSGenerationResult)
async def generate_dns_config(
    options: DNSGenerationOptions = DNSGenerationOptions(),
    current_user: User = Depends(get_current_active_user)
):
    """Generate DNS configuration natively in Python"""
    try:
        result = dns_service.generate_dns_config(options=options)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating DNS configuration: {str(e)}"
        )


@router.get("/named-conf")
async def get_named_conf(current_user: User = Depends(get_current_active_user)):
    """Get content of generated named.conf file"""
    try:
        config = dns_service.default_config

        if not config.output_named_conf_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="named.conf path not configured"
            )

        content = dns_service.get_zone_content(config.output_named_conf_path)
        return {"path": config.output_named_conf_path, "content": content}

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="named.conf not found. Generate DNS configuration first."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading named.conf: {str(e)}"
        )


@router.get("/dns-hosts")
async def get_dns_hosts(current_user: User = Depends(get_current_active_user)):
    """Get content of generated hosts.named file"""
    try:
        config = dns_service.default_config

        if not config.output_dns_hosts_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="DNS hosts path not configured"
            )

        content = dns_service.get_zone_content(config.output_dns_hosts_path)
        return {"path": config.output_dns_hosts_path, "content": content}

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="hosts.named not found. Generate DNS configuration first."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading DNS hosts: {str(e)}"
        )


@router.post("/custom-hosts")
async def add_custom_dns_entry(
    request: AddCustomDNSEntryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Add a custom DNS entry"""
    try:
        dns_service.add_custom_dns_entry(request.ip_address, request.fqdn)
        return {"success": True, "message": f"Added DNS entry: {request.ip_address} {request.fqdn}"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding custom DNS entry: {str(e)}"
        )


@router.delete("/custom-hosts/{fqdn}")
async def remove_custom_dns_entry(
    fqdn: str,
    current_user: User = Depends(get_current_active_user)
):
    """Remove a custom DNS entry by FQDN"""
    try:
        success = dns_service.remove_custom_dns_entry(fqdn)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DNS entry for '{fqdn}' not found"
            )
        return {"success": True, "message": f"Removed DNS entry for {fqdn}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing custom DNS entry: {str(e)}"
        )


@router.post("/mail-hosts")
async def add_mail_host_entry(
    request: AddMailHostRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Add a mail host entry"""
    try:
        dns_service.add_mail_host_entry(request.ip_address, request.fqdn)
        return {"success": True, "message": f"Added mail host: {request.ip_address} {request.fqdn}"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding mail host entry: {str(e)}"
        )


@router.delete("/mail-hosts/{fqdn}")
async def remove_mail_host_entry(
    fqdn: str,
    current_user: User = Depends(get_current_active_user)
):
    """Remove a mail host entry by FQDN"""
    try:
        success = dns_service.remove_mail_host_entry(fqdn)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mail host entry for '{fqdn}' not found"
            )
        return {"success": True, "message": f"Removed mail host entry for {fqdn}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing mail host entry: {str(e)}"
        )
