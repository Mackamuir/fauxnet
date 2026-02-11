"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    username: str
    email: str  # Changed from EmailStr to str to allow .local domains
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str] = None  # Changed from EmailStr to str
    full_name: Optional[str] = None
    password: Optional[str] = None


class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Virtual Host Schemas
class VirtualHostBase(BaseModel):
    hostname: str
    ip_address: Optional[str] = None
    scrape_url: Optional[str] = None
    is_custom: bool = False


class VirtualHostCreate(VirtualHostBase):
    pass


class VirtualHostUpdate(BaseModel):
    ip_address: Optional[str] = None
    status: Optional[str] = None
    scrape_url: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class VirtualHost(VirtualHostBase):
    id: int
    status: str
    last_scraped: Optional[datetime] = None
    has_ssl: bool
    has_nginx_config: bool
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Vhosts Management Schemas (filesystem-based)
class VhostInfo(BaseModel):
    name: str
    path: str
    config_path: str
    type: str
    has_cert: bool
    has_nginx_config: bool
    cert_path: Optional[str] = None
    nginx_config_path: Optional[str] = None
    size_bytes: Optional[int] = None  # Optional for performance - only included when include_stats=True
    file_count: Optional[int] = None  # Optional for performance - only included when include_stats=True
    modified: Optional[str] = None


class VhostDetailInfo(VhostInfo):
    files: list[Dict[str, Any]] = []


class VhostStatistics(BaseModel):
    total_vhosts: int
    total_size_bytes: int
    total_files: int
    vhosts_with_certs: int
    vhosts_with_nginx_config: int


class ScrapeOptions(BaseModel):
    depth: int = 1  # Scraping depth (default: 1 for landing page only, 0 for unlimited)
    page_requisites: bool = True  # Download CSS, JS, images (-p flag)
    # Note: span_hosts and convert_links are always enabled in wget (matching topgen-scrape.sh)
    # These fields are kept for backward compatibility but are ignored
    span_hosts: bool = True  # Always enabled (-H flag)
    convert_links: bool = True  # Always enabled (--convert-file-only)


class ScrapeSitesRequest(BaseModel):
    sites: list[str]
    options: Optional[ScrapeOptions] = None


class UpdateScrapeSitesRequest(BaseModel):
    sites: list[str]


class ScrapeResult(BaseModel):
    success: bool
    returncode: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error: Optional[str] = None


class NginxConfigUpdate(BaseModel):
    content: str


class FileContentUpdate(BaseModel):
    content: str


class ScrapeOptionsRequest(BaseModel):
    depth: int = 1  # Scraping depth (1 = landing page, 0 = unlimited)
    page_requisites: bool = True  # Download CSS, JS, images
    # Note: span_hosts and convert_links are always enabled (matching topgen-scrape.sh)
    span_hosts: bool = True  # Always enabled (-H flag)
    convert_links: bool = True  # Always enabled (--convert-file-only)


# Service Schemas
class ServiceStatus(BaseModel):
    name: str
    status: str  # running, stopped, error
    active: bool
    enabled: bool
    uptime: Optional[str] = None
    pid: Optional[int] = None


class ServiceAction(BaseModel):
    action: str = Field(..., pattern="^(start|stop|restart|enable|disable)$")


class ServiceLogSchema(BaseModel):
    id: int
    service_name: str
    action: str
    status: str
    message: Optional[str] = None
    user_id: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# System Schemas
class SystemInfo(BaseModel):
    hostname: str
    platform: str
    cpu_count: int
    cpu_percent: float
    memory_total: int
    memory_used: int
    memory_percent: float
    disk_total: int
    disk_used: int
    disk_percent: float


# CORE Topology Schemas
class CoreSessionInfo(BaseModel):
    session_id: Optional[int] = None
    state: str
    nodes: int
    file: Optional[str] = None


# Configuration Schemas
class ConfigurationSchema(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


# DNS Configuration Schemas
class DNSHostEntry(BaseModel):
    ip_address: str
    fqdn: str


class DNSHostsFile(BaseModel):
    name: str  # e.g., "web", "mail", "extra1"
    path: str
    entries: list[DNSHostEntry]
    line_count: int


class DNSDelegationEntry(BaseModel):
    domain_or_network: str  # e.g., "example.com" or "192.168.1"
    nameservers: list[str]  # e.g., ["ns1.example.com", "ns2.example.com"]


class DNSNameserverEntry(BaseModel):
    hostname: str  # e.g., "ns1.example.com"
    ip_address: str


class DNSDelegationsConfig(BaseModel):
    forward: list[DNSDelegationEntry]  # Forward delegations (domains)
    reverse: list[DNSDelegationEntry]  # Reverse delegations (networks)
    nameservers: list[DNSNameserverEntry]  # NS IP addresses


class DNSConfiguration(BaseModel):
    vhosts_config_dir: str = "/opt/fauxnet/vhosts_config"  # Directory containing vhost config subdirectories with hosts files
    mail_hosts_path: Optional[str] = "/opt/fauxnet/config/hosts.vmail"
    custom_hosts_path: str = "/opt/fauxnet/config/dns.custom"  # Custom DNS entries
    backbone_hosts_path: Optional[str] = "/opt/fauxnet/config/backbone.hosts"  # Backbone network infrastructure
    extra_hosts_paths: list[str] = []
    delegations_path: str = "/opt/fauxnet/config/delegations.dns"
    output_dns_hosts_path: str = "/opt/fauxnet/config/hosts.named"
    output_named_conf_path: str = "/opt/fauxnet/config/named.conf"
    output_zone_folder: str = "/opt/fauxnet/named"
    force_overwrite: bool = False
    quiet_mode: bool = False


class DNSGenerationOptions(BaseModel):
    force_overwrite: bool = False
    quiet_mode: bool = False


class DNSZoneInfo(BaseModel):
    name: str  # e.g., "com", "net", "1" (reverse)
    type: str  # "forward" or "reverse"
    path: str
    record_count: int
    size_bytes: int
    modified: Optional[str] = None


class DNSGenerationResult(BaseModel):
    success: bool
    zones_created: int
    hosts_processed: int
    hosts_skipped: int
    warnings: list[str] = []
    errors: list[str] = []
    output_files: list[str] = []
    message: Optional[str] = None


class DNSStatus(BaseModel):
    configured: bool
    web_hosts_exists: bool
    mail_hosts_exists: bool
    backbone_hosts_exists: bool = False
    delegations_exists: bool
    named_conf_exists: bool
    zone_count: int
    web_hosts_count: int
    mail_hosts_count: int
    backbone_hosts_count: int = 0
    needs_regeneration: bool  # True if config files are newer than generated files


class UpdateHostsFileRequest(BaseModel):
    content: str  # Raw content of hosts file (IP FQDN per line)


class UpdateDelegationsRequest(BaseModel):
    delegations: DNSDelegationsConfig


class AddCustomDNSEntryRequest(BaseModel):
    ip_address: str
    fqdn: str


class RemoveCustomDNSEntryRequest(BaseModel):
    fqdn: str


class AddMailHostRequest(BaseModel):
    ip_address: str
    fqdn: str


class RemoveMailHostRequest(BaseModel):
    fqdn: str


# Community Service Schemas
class CommunityTarget(BaseModel):
    target: str
    probability: Optional[int] = None  # Optional weight/probability


class CommunityAction(BaseModel):
    action: str
    probability: Optional[int] = None  # Optional weight/probability


class CommunitySleepConfig(BaseModel):
    Min: int = 30
    Max: int = 120


class CommunityConfig(BaseModel):
    Enable: bool = True
    Targets: list  # Can be strings or dicts with probabilities
    Actions: Optional[list] = None  # Can be strings or dicts with probabilities
    Sleep: Optional[CommunitySleepConfig] = None


class CommunityNodeStatus(BaseModel):
    node_id: str
    node_name: str
    is_running: bool
    pid: Optional[int] = None
    uptime: Optional[str] = None
    config_path: str
    log_path: Optional[str] = None


class CommunityServiceStatus(BaseModel):
    session_active: bool
    nodes: list[CommunityNodeStatus]
    total_nodes: int
    running_nodes: int


class CommunityNodeAction(BaseModel):
    node_id: str
    action: str = Field(..., pattern="^(start|stop|restart)$")


class CommunityConfigUpdate(BaseModel):
    config: CommunityConfig


# Phase-based Scraping Schemas
class PhaseSelectionRequest(BaseModel):
    """Request to run specific scraping phases"""
    phases: list[int] = Field(..., min_length=1, max_length=7)
    sites: Optional[list[str]] = None  # Required if phase 2 is included
    options: Optional[ScrapeOptions] = None


class PhaseInfo(BaseModel):
    """Information about a scraping phase"""
    phase_number: int
    name: str
    description: str
    completed: bool
    dependencies: list[int]


class PhaseStatusResponse(BaseModel):
    """Status of all phases"""
    phases: list[PhaseInfo]
