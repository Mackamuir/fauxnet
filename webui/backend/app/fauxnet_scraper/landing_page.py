#!/usr/bin/env python3
"""
Fauxnet Landing Page Generator
Generates the fauxnet.info landing page
"""

import os
import glob
import json
import logging
from string import Template

from .config import (FAUXNET_VHOSTS_WWW, FAUXNET_VHOSTS_CONFIG, FAUXNET_SITE, FAUXNET_VARETC,
                   FAUXNET_TEMPLATES)

logger = logging.getLogger("fauxnet")

async def generate_landing_page():
    """Generate the fauxnet.info landing page"""
    os.makedirs(FAUXNET_SITE, exist_ok=True)

    # Get list of vhosts from vhosts_www (excluding fauxnet.info itself)
    vhosts = [os.path.basename(v) for v in glob.glob(f"{FAUXNET_VHOSTS_WWW}/*")
            if not v.endswith('fauxnet.info')]

    html_content = ""
    for vhost in sorted(vhosts):
        html_content += f'      <li><a href="//{vhost}">{vhost}</a>\n'

    # Write file from Template
    index_path = os.path.join(FAUXNET_SITE, "index.html")
    with open(index_path, 'w') as f:
        with open(os.path.join(FAUXNET_TEMPLATES, "fauxnet.info"), 'r') as template:
            template_source = Template(template.read())
            template_result = template_source.substitute(vhosts=html_content)
        f.write(template_result)

    logger.info(f"Generated landing page with {len(vhosts)} vhosts")

async def generate_sites_summary(site_urls):
    """Generate summary of scraped sites (for reference)"""
    config = {
        "_comment": "Summary of scraped virtual hosts",
        "vhost_structure": "Web content in vhosts_www/, config files in vhosts_config/",
        "sites": {}
    }

    for hostname, urls in site_urls.items():
        vhost_www_path = os.path.join(FAUXNET_VHOSTS_WWW, hostname)
        vhost_config_path = os.path.join(FAUXNET_VHOSTS_CONFIG, hostname)
        config["sites"][hostname] = {
            "www_directory": vhost_www_path,
            "config_directory": vhost_config_path,
            "files": {
                "nginx_config": f"{vhost_config_path}/nginx.conf",
                "ssl_certificate": f"{vhost_config_path}/{hostname}.cer",
                "hosts_entry": f"{vhost_config_path}/hosts",
                "html_content": f"{vhost_www_path}/"
            },
            "total_urls_discovered": len(urls),
            "urls": sorted(urls)
        }

    config_path = os.path.join(FAUXNET_VARETC, "sites_summary.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    total_urls = sum(len(urls) for urls in site_urls.values())
    logger.info(f"Generated sites summary with {len(config['sites'])} sites, {total_urls} total URLs")