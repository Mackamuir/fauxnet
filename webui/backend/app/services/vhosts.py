"""
Virtual hosts management utilities
"""
import os
import subprocess
import json
import shutil
import logging
import io
import sys
import asyncio
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

from app.fauxnet_scraper import scrape_sites_async
from app.services.progress import ProgressManager

logger = logging.getLogger(__name__)


class VhostsManager:
    """Manager for virtual hosts"""

    # Base paths
    FAUXNET_BASE = "/opt/fauxnet"
    VHOSTS_WWW_DIR = f"{FAUXNET_BASE}/vhosts_www"  # Web content
    VHOSTS_CONFIG_DIR = f"{FAUXNET_BASE}/vhosts_config"  # Certs, nginx configs, hosts files
    CONFIG_DIR = f"{FAUXNET_BASE}/config"  # Global config
    TEMPLATES_DIR = f"{FAUXNET_BASE}/templates"
    CUSTOM_VHOST_TEMPLATES_DIR = f"{FAUXNET_BASE}/custom_vhost_templates"  # Custom nginx templates

    # Fallback templates (in app/templates directory)
    FALLBACK_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

    # Config files
    SCRAPE_SITES_FILE = f"{CONFIG_DIR}/scrape_sites.txt"
    CUSTOM_SITES_FILE = f"{CONFIG_DIR}/custom_sites.txt"
    HOSTS_NGINX_FILE = f"{CONFIG_DIR}/hosts.nginx"

    @staticmethod
    def ensure_directories():
        """Ensure all required directories exist"""
        directories = [
            VhostsManager.FAUXNET_BASE,
            VhostsManager.VHOSTS_WWW_DIR,
            VhostsManager.VHOSTS_CONFIG_DIR,
            VhostsManager.CONFIG_DIR,
            VhostsManager.TEMPLATES_DIR,
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    @staticmethod
    async def list_vhosts() -> List[Dict]:
        """List all virtual hosts (scans vhosts_www for content)"""
        VhostsManager.ensure_directories()
        vhosts = []

        if not os.path.exists(VhostsManager.VHOSTS_WWW_DIR):
            return vhosts

        # Load scraped sites list to identify directly scraped vhosts
        scraped_sites = set()
        if os.path.exists(VhostsManager.SCRAPE_SITES_FILE):
            try:
                with open(VhostsManager.SCRAPE_SITES_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Extract hostname from URL
                            from urllib.parse import urlparse
                            parsed = urlparse(line if '://' in line else f'http://{line}')
                            hostname = parsed.netloc or parsed.path
                            if hostname:
                                scraped_sites.add(hostname)
            except Exception:
                pass

        # Load custom sites
        custom_sites = set()
        if os.path.exists(VhostsManager.CUSTOM_SITES_FILE):
            print("here1")
            try:
                with open(VhostsManager.CUSTOM_SITES_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Extract hostname from URL
                            from urllib.parse import urlparse
                            parsed = urlparse(line if '://' in line else f'http://{line}')
                            hostname = parsed.netloc or parsed.path
                            if hostname:
                                custom_sites.add(hostname)
            except Exception:
                pass
        else:
            print("uh0h1")

        # Fauxnet infrastructure sites
        fauxnet_sites = {'fauxnet.info', 'www.msftncsi.com'}

        # Iterate through vhost directories in vhosts_www
        for vhost_name in os.listdir(VhostsManager.VHOSTS_WWW_DIR):
            vhost_www_path = os.path.join(VhostsManager.VHOSTS_WWW_DIR, vhost_name)

            if not os.path.isdir(vhost_www_path):
                continue

            # Config files are in vhosts_config
            vhost_config_path = os.path.join(VhostsManager.VHOSTS_CONFIG_DIR, vhost_name)
            cert_path = os.path.join(vhost_config_path, f"{vhost_name}.cer")
            nginx_config_path = os.path.join(vhost_config_path, "nginx.conf")

            # Determine vhost type
            if vhost_name in custom_sites:
                vhost_type = "custom"
            elif vhost_name in fauxnet_sites:
                vhost_type = "fauxnet"
            elif vhost_name in scraped_sites:
                vhost_type = "scraped"
            else:
                vhost_type = "discovered"

            # Calculate directory size for www content
            total_size = 0
            file_count = 0
            try:
                for dirpath, dirnames, filenames in os.walk(vhost_www_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        if os.path.exists(filepath):
                            total_size += os.path.getsize(filepath)
                            file_count += 1
            except Exception:
                pass

            # Get modification time from www directory
            try:
                mtime = os.path.getmtime(vhost_www_path)
                modified_date = datetime.fromtimestamp(mtime).isoformat()
            except Exception:
                modified_date = None

            vhosts.append({
                "name": vhost_name,
                "path": vhost_www_path,  # Points to web content
                "config_path": vhost_config_path,  # Points to config
                "type": vhost_type,  # NEW: scraped, custom, or discovered
                "has_cert": os.path.exists(cert_path),
                "has_nginx_config": os.path.exists(nginx_config_path),
                "cert_path": cert_path if os.path.exists(cert_path) else None,
                "nginx_config_path": nginx_config_path if os.path.exists(nginx_config_path) else None,
                "size_bytes": total_size,
                "file_count": file_count,
                "modified": modified_date,
            })
        # Sort by name
        vhosts.sort(key=lambda x: x["name"])
        return vhosts

    @staticmethod
    async def get_vhost(vhost_name: str) -> Optional[Dict]:
        """Get details for a specific virtual host"""
        VhostsManager.ensure_directories()
        vhost_www_path = os.path.join(VhostsManager.VHOSTS_WWW_DIR, vhost_name)

        if not os.path.exists(vhost_www_path) or not os.path.isdir(vhost_www_path):
            return None

        # Get all vhosts and find the matching one
        vhosts = await VhostsManager.list_vhosts()
        for vhost in vhosts:
            if vhost["name"] == vhost_name:
                # Add file listing from www directory
                files = []
                try:
                    for root, dirs, filenames in os.walk(vhost_www_path):
                        for filename in filenames:
                            filepath = os.path.join(root, filename)
                            relpath = os.path.relpath(filepath, vhost_www_path)
                            files.append({
                                "name": filename,
                                "path": relpath,
                                "size": os.path.getsize(filepath),
                            })
                except Exception:
                    pass

                vhost["files"] = files
                return vhost

        return None

    @staticmethod
    async def delete_vhost(vhost_name: str) -> bool:
        """Delete a virtual host and all associated files"""
        VhostsManager.ensure_directories()

        vhost_www_path = os.path.join(VhostsManager.VHOSTS_WWW_DIR, vhost_name)
        vhost_config_path = os.path.join(VhostsManager.VHOSTS_CONFIG_DIR, vhost_name)

        deleted = False

        # Delete www directory
        if os.path.exists(vhost_www_path):
            shutil.rmtree(vhost_www_path)
            deleted = True

        # Delete config directory (contains cert, nginx.conf, hosts file)
        if os.path.exists(vhost_config_path):
            shutil.rmtree(vhost_config_path)
            deleted = True

        # Remove from hosts.nginx file
        if os.path.exists(VhostsManager.HOSTS_NGINX_FILE):
            try:
                with open(VhostsManager.HOSTS_NGINX_FILE, 'r') as f:
                    lines = f.readlines()

                with open(VhostsManager.HOSTS_NGINX_FILE, 'w') as f:
                    for line in lines:
                        if vhost_name not in line:
                            f.write(line)
            except Exception:
                pass

        return deleted

    @staticmethod
    async def get_ca_certificate_path() -> Optional[str]:
        """Get the path to the CA certificate"""
        VhostsManager.ensure_directories()
        cert_path = os.path.join(VhostsManager.CONFIG_DIR, "fauxnet_ca.cer")
        if os.path.exists(cert_path):
            return cert_path
        return None

    @staticmethod
    async def get_ca_key_path() -> Optional[str]:
        """Get the path to the CA private key"""
        VhostsManager.ensure_directories()
        key_path = os.path.join(VhostsManager.CONFIG_DIR, "fauxnet_ca.key")
        if os.path.exists(key_path):
            return key_path
        return None

    @staticmethod
    async def get_nginx_config(vhost_name: str) -> Optional[str]:
        """Get the nginx configuration for a vhost"""
        VhostsManager.ensure_directories()
        vhost_config_path = os.path.join(VhostsManager.VHOSTS_CONFIG_DIR, vhost_name)
        nginx_config_path = os.path.join(vhost_config_path, "nginx.conf")

        if not os.path.exists(nginx_config_path):
            return None

        try:
            with open(nginx_config_path, 'r') as f:
                return f.read()
        except Exception:
            return None

    @staticmethod
    async def update_nginx_config(vhost_name: str, content: str) -> bool:
        """Update the nginx configuration for a vhost"""
        VhostsManager.ensure_directories()
        vhost_config_path = os.path.join(VhostsManager.VHOSTS_CONFIG_DIR, vhost_name)

        if not os.path.exists(vhost_config_path) or not os.path.isdir(vhost_config_path):
            return False

        nginx_config_path = os.path.join(vhost_config_path, "nginx.conf")

        try:
            with open(nginx_config_path, 'w') as f:
                f.write(content)
            return True
        except Exception:
            return False

    @staticmethod
    async def get_file_content(vhost_name: str, file_path: str) -> Optional[str]:
        """Get the content of a file in a vhost (from vhosts_www)"""
        VhostsManager.ensure_directories()
        vhost_www_path = os.path.join(VhostsManager.VHOSTS_WWW_DIR, vhost_name)
        full_path = os.path.join(vhost_www_path, file_path)

        # Security: ensure the path is within the vhost www directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(vhost_www_path)):
            return None

        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            return None

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return None

    @staticmethod
    async def update_file_content(vhost_name: str, file_path: str, content: str) -> bool:
        """Update the content of a file in a vhost (in vhosts_www)"""
        VhostsManager.ensure_directories()
        vhost_www_path = os.path.join(VhostsManager.VHOSTS_WWW_DIR, vhost_name)
        full_path = os.path.join(vhost_www_path, file_path)

        # Security: ensure the path is within the vhost www directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(vhost_www_path)):
            return False

        if not os.path.exists(vhost_www_path) or not os.path.isdir(vhost_www_path):
            return False

        # Create parent directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False

    @staticmethod
    async def upload_file(vhost_name: str, file, target_path: str = "") -> bool:
        """
        Upload a file to a vhost (in vhosts_www)

        Args:
            vhost_name: Name of the virtual host
            file: File to upload
            target_path: Target directory path within vhost (e.g., 'images', 'css/vendor')
                        Will be created if it doesn't exist

        Returns:
            bool: True if successful, False otherwise
        """
        VhostsManager.ensure_directories()
        vhost_www_path = os.path.join(VhostsManager.VHOSTS_WWW_DIR, vhost_name)

        if not os.path.exists(vhost_www_path) or not os.path.isdir(vhost_www_path):
            return False

        # Normalize target_path (remove leading/trailing slashes, handle ..)
        if target_path:
            # Remove leading/trailing slashes and normalize
            target_path = target_path.strip('/')
            # Split and rejoin to remove any '..' or '.' components for security
            parts = [p for p in target_path.split('/') if p and p != '.' and p != '..']
            target_path = '/'.join(parts) if parts else ''

        # Determine destination path
        if target_path:
            # Create the target directory path
            target_dir = os.path.join(vhost_www_path, target_path)
            dest_path = os.path.join(target_dir, file.filename)
        else:
            # Upload to root of vhost www directory
            dest_path = os.path.join(vhost_www_path, file.filename)

        # Security: ensure the path is within the vhost www directory
        if not os.path.abspath(dest_path).startswith(os.path.abspath(vhost_www_path)):
            logger.warning(f"Attempted path traversal attack: {dest_path}")
            return False

        # Create all parent directories if needed (including target_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        try:
            with open(dest_path, 'wb') as f:
                content = await file.read()
                f.write(content)
            logger.info(f"Uploaded file to {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            return False

    @staticmethod
    async def start_scrape_async(sites: List[str], options=None) -> str:
        """
        Start scraping process in the background and return operation ID

        Args:
            sites: List of URLs to scrape
            options: Scraping options (depth, page_requisites, etc.)

        Returns:
            Operation ID for tracking progress
        """
        VhostsManager.ensure_directories()

        # Create progress tracker
        progress_tracker = ProgressManager.create_tracker(total_phases=7)
        operation_id = progress_tracker.operation_id

        # Write sites to scrape_sites.txt
        header = (
            "# Sites to scrape for virtual hosts\n"
            "# Generated by Fauxnet WebUI\n\n"
        )

        try:
            with open(VhostsManager.SCRAPE_SITES_FILE, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            content = ""

        # Ensure header once
        if header not in content:
            content = header + content

        existing = set(content.splitlines())

        with open(VhostsManager.SCRAPE_SITES_FILE, 'a') as f:
            for site in sites:
                if site not in existing:
                    f.write(f"{site}\n")

        # Convert Pydantic model to dict if needed
        if options is not None and hasattr(options, 'model_dump'):
            options_dict = options.model_dump()
        elif options is not None:
            options_dict = options
        else:
            options_dict = None

        # Start scraping in background task
        asyncio.create_task(VhostsManager._run_scrape_with_progress(
            sites, options_dict, progress_tracker
        ))

        return operation_id

    @staticmethod
    async def _run_scrape_with_progress(sites: List[str], options: dict, progress_tracker):
        """Run scraping with progress tracking"""
        try:
            # Call integrated scraper with progress tracker
            result = await scrape_sites_async(
                sites_list=sites,
                options=options,
                progress_tracker=progress_tracker
            )

            logger.info(f"Scraping completed: {result}")

        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}", exc_info=True)
            progress_tracker.error_occurred(str(e))

    @staticmethod
    async def get_scrape_sites() -> List[str]:
        """Get list of sites configured for scraping"""
        VhostsManager.ensure_directories()

        if not os.path.exists(VhostsManager.SCRAPE_SITES_FILE):
            return []

        try:
            with open(VhostsManager.SCRAPE_SITES_FILE, 'r') as f:
                sites = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            return sites
        except Exception:
            return []

    @staticmethod
    async def update_scrape_sites(sites: List[str]) -> bool:
        """Update the list of sites to scrape"""
        VhostsManager.ensure_directories()

        try:
            with open(VhostsManager.SCRAPE_SITES_FILE, 'w') as f:
                f.write("# Sites to scrape for virtual hosts\n")
                f.write("# One URL per line\n\n")
                for site in sites:
                    f.write(f"{site}\n")
            return True
        except Exception:
            return False

    @staticmethod
    async def list_custom_vhost_templates() -> List[Dict]:
        """
        List all available custom vhost templates

        Returns:
            List of template info dictionaries with name, path, and description
        """
        templates = []

        # Check custom templates directory first
        if os.path.exists(VhostsManager.CUSTOM_VHOST_TEMPLATES_DIR):
            for filename in os.listdir(VhostsManager.CUSTOM_VHOST_TEMPLATES_DIR):
                if filename.endswith('.conf'):
                    template_name = filename.replace('.conf', '').replace('nginx_', '')
                    template_path = os.path.join(VhostsManager.CUSTOM_VHOST_TEMPLATES_DIR, filename)

                    # Try to extract description from template file
                    description = None
                    try:
                        with open(template_path, 'r') as f:
                            first_line = f.readline().strip()
                            # Look for comment with description
                            if first_line.startswith('#'):
                                description = first_line.lstrip('#').strip()
                    except Exception:
                        pass

                    templates.append({
                        "name": template_name,
                        "filename": filename,
                        "path": template_path,
                        "description": description or f"Custom nginx template: {template_name}",
                        "source": "custom"
                    })

        # If no custom templates, fall back to built-in templates
        if not templates:
            for filename in os.listdir(VhostsManager.FALLBACK_TEMPLATES_DIR):
                if filename.startswith('nginx_') and filename.endswith('.conf'):
                    template_name = filename.replace('.conf', '').replace('nginx_', '')
                    template_path = os.path.join(VhostsManager.FALLBACK_TEMPLATES_DIR, filename)

                    # Default descriptions for built-in templates
                    descriptions = {
                        "regular_website": "Standard web server configuration for hosting static or dynamic content. Includes SSL/TLS support and basic nginx configuration.",
                        "c2_redirector": "Command & Control redirector configuration. Proxies traffic to a backend C2 server with header preservation and optional security scanner blocking."
                    }

                    templates.append({
                        "name": template_name,
                        "filename": filename,
                        "path": template_path,
                        "description": descriptions.get(template_name, f"Nginx template: {template_name}"),
                        "source": "builtin"
                    })

        return templates

    @staticmethod
    async def get_statistics() -> Dict:
        """Get overall vhosts statistics"""
        VhostsManager.ensure_directories()

        vhosts = await VhostsManager.list_vhosts()

        total_size = sum(v["size_bytes"] for v in vhosts)
        total_files = sum(v["file_count"] for v in vhosts)
        vhosts_with_certs = sum(1 for v in vhosts if v["has_cert"])
        vhosts_with_nginx = sum(1 for v in vhosts if v["has_nginx_config"])

        return {
            "total_vhosts": len(vhosts),
            "total_size_bytes": total_size,
            "total_files": total_files,
            "vhosts_with_certs": vhosts_with_certs,
            "vhosts_with_nginx_config": vhosts_with_nginx,
        }

    @staticmethod
    async def create_custom_vhost(vhost_name: str, template_type: str, backend_c2_server: Optional[str] = None, ip_address: Optional[str] = None) -> Dict:
        """
        Create a custom virtual host with specified template

        Args:
            vhost_name: Hostname for the vhost
            template_type: Either 'regular_website' or 'c2_redirector'
            backend_c2_server: Backend C2 server URL (required for c2_redirector template)
            ip_address: IP address for the hosts file (defaults to "1.0.0.0")

        Returns:
            Dict with success status and details
        """
        VhostsManager.ensure_directories()

        # Validate vhost name (basic validation)
        if not vhost_name or '/' in vhost_name or '..' in vhost_name:
            return {"success": False, "error": "Invalid vhost name"}

        # Check if vhost already exists
        vhost_www_path = os.path.join(VhostsManager.VHOSTS_WWW_DIR, vhost_name)
        vhost_config_path = os.path.join(VhostsManager.VHOSTS_CONFIG_DIR, vhost_name)

        if os.path.exists(vhost_www_path) or os.path.exists(vhost_config_path):
            return {"success": False, "error": "Virtual host already exists"}

        # Validate template type
        if template_type not in ['regular_website', 'c2_redirector']:
            return {"success": False, "error": "Invalid template type"}

        # Validate C2 server for redirector
        if template_type == 'c2_redirector' and not backend_c2_server:
            return {"success": False, "error": "Backend C2 server required for redirector template"}

        try:
            # Create directories
            os.makedirs(vhost_www_path, exist_ok=True)
            os.makedirs(vhost_config_path, exist_ok=True)

            # Create default index.html for regular website
            if template_type == 'regular_website':
                index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{vhost_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            text-align: center;
        }}
        h1 {{
            color: #333;
        }}
        p {{
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>Welcome to {vhost_name}</h1>
    <p>This is a custom virtual host created via Fauxnet WebUI.</p>
    <p>Edit the files in the vhost directory to customize this site.</p>
</body>
</html>"""
                with open(os.path.join(vhost_www_path, "index.html"), 'w') as f:
                    f.write(index_html)

            # Generate SSL certificate for this vhost
            # Use the same CA and shared key as scraped vhosts
            ca_cert = os.path.join(VhostsManager.CONFIG_DIR, "fauxnet_ca.cer")
            ca_key = os.path.join(VhostsManager.CONFIG_DIR, "fauxnet_ca.key")
            vh_key = os.path.join(VhostsManager.CONFIG_DIR, "fauxnet_vh.key")
            cert_path = os.path.join(vhost_config_path, f"{vhost_name}.cer")

            # Check if CA exists, if not generate it
            if not os.path.exists(ca_cert) or not os.path.exists(ca_key):
                # Generate CA
                proc = await asyncio.create_subprocess_exec(
                    'openssl', 'req', '-newkey', 'rsa:2048', '-nodes',
                    '-keyout', ca_key,
                    '-days', '7300', '-x509',
                    '-out', ca_cert,
                    '-subj', '/C=US/ST=PA/L=Pgh/O=CMU/OU=CERT/CN=fauxnet_ca',
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.communicate()

            # Generate shared vhost key if not exists
            if not os.path.exists(vh_key):
                proc = await asyncio.create_subprocess_exec(
                    'openssl', 'genrsa',
                    '-out', vh_key,
                    '2048',
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.communicate()

            # Generate certificate (simplified version without full CA setup)
            # Use self-signed cert for now
            proc = await asyncio.create_subprocess_exec(
                'openssl', 'req', '-new', '-x509',
                '-key', vh_key,
                '-out', cert_path,
                '-days', '3650',
                '-subj', f'/C=US/ST=PA/L=Pgh/O=CMU/OU=CERT/CN={vhost_name}',
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.communicate()

            # Generate hosts entry
            # Use provided IP address or default to "1.0.0.0"
            if ip_address:
                vhost_ip = ip_address
            else:
                vhost_ip = "1.0.0.0"

            hosts_file = os.path.join(vhost_config_path, "hosts")
            with open(hosts_file, 'w') as f:
                f.write(f"{vhost_ip} {vhost_name}\n")

            # Generate nginx config from template
            # First check if template_type already includes 'nginx_' prefix
            if template_type.startswith('nginx_'):
                template_file = f"{template_type}.conf"
            else:
                template_file = f"nginx_{template_type}.conf"

            # Try custom templates directory first
            template_path = os.path.join(VhostsManager.CUSTOM_VHOST_TEMPLATES_DIR, template_file)
            if not os.path.exists(template_path):
                # Fall back to built-in templates
                template_path = os.path.join(VhostsManager.FALLBACK_TEMPLATES_DIR, template_file)

            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Template not found: {template_file}")

            with open(template_path, 'r') as f:
                from string import Template
                template = Template(f.read())

                # Prepare substitutions
                subs = {
                    'vhost_base': vhost_name,
                    'cert_path': cert_path,
                    'vh_key': vh_key,
                    'html_dir': vhost_www_path,
                }

                # For C2 redirector, add backend server
                if template_type == 'c2_redirector' and backend_c2_server:
                    # Replace the placeholder in the template
                    nginx_config = template.safe_substitute(subs)
                    nginx_config = nginx_config.replace('$$backend_c2_server', backend_c2_server)
                else:
                    nginx_config = template.safe_substitute(subs)

            nginx_config_path = os.path.join(vhost_config_path, "nginx.conf")
            with open(nginx_config_path, 'w') as f:
                f.write(nginx_config)

            # Create .custom marker file to identify this as a custom vhost
            custom_marker = os.path.join(vhost_config_path, ".custom")
            with open(custom_marker, 'w') as f:
                f.write(f"Created: {datetime.now().isoformat()}\nTemplate: {template_type}\n")

            logger.info(f"Created custom vhost: {vhost_name} (template: {template_type})")

            # Create custom_sites.txt to keep record of our custom sites
            header = (
                "# Custom virtual hosts created by users\n"
                "# Generated by Fauxnet WebUI\n\n"
            )

            # Read existing content (if any)
            try:
                with open(VhostsManager.CUSTOM_SITES_FILE, 'r') as f:
                    content = f.read()
            except FileNotFoundError:
                content = ""
            # Ensure header exists
            if header not in content:
                content = header + content
            # Convert existing sites to a set for quick lookup
            existing_sites = {line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")}

            # Append new sites
            new_lines = []
            if vhost_name not in existing_sites:
                new_lines.append(vhost_name)
                existing_sites.add(vhost_name)

            # Write updated content only once
            if new_lines or header not in content:
                with open(VhostsManager.CUSTOM_SITES_FILE, 'w') as f:
                    f.write(header)
                    for site in sorted(existing_sites):
                        f.write(f"{site}\n")

            return {
                "success": True,
                "vhost_name": vhost_name,
                "template_type": template_type,
                "www_path": vhost_www_path,
                "config_path": vhost_config_path,
            }

        except Exception as e:
            logger.error(f"Failed to create custom vhost: {str(e)}", exc_info=True)
            # Cleanup on failure
            if os.path.exists(vhost_www_path):
                shutil.rmtree(vhost_www_path)
            if os.path.exists(vhost_config_path):
                shutil.rmtree(vhost_config_path)
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_vhost_logs(vhost_name: str, log_type: str = "access", lines: int = 100) -> Optional[str]:
        """
        Get nginx logs for a virtual host

        Args:
            vhost_name: Hostname of the vhost
            log_type: Either 'access' or 'error'
            lines: Number of lines to return (default 100)

        Returns:
            String containing log content or None if log doesn't exist
        """
        VhostsManager.ensure_directories()

        # Validate log_type
        if log_type not in ['access', 'error']:
            return None

        # Construct log file path
        log_file = f"/var/log/nginx/{vhost_name}-{log_type}.log"

        # Check if log file exists
        if not os.path.exists(log_file):
            return f"Log file not found: {log_file}\n\nThis may be normal if nginx hasn't written any logs yet."

        try:
            # Use tail to get last N lines
            proc = await asyncio.create_subprocess_exec(
                'tail', '-n', str(lines), log_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                content = stdout.decode('utf-8', errors='replace')
                if not content.strip():
                    return f"Log file is empty: {log_file}"
                return content
            else:
                error_msg = stderr.decode('utf-8', errors='replace')
                return f"Error reading log file: {error_msg}"

        except Exception as e:
            logger.error(f"Failed to read log file {log_file}: {str(e)}")
            return f"Error reading log file: {str(e)}"
