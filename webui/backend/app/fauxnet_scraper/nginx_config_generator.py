#!/usr/bin/env python3
"""
Fauxnet Nginx Configuration Generator
Generates standalone nginx configurations for vhosts
"""

import asyncio
import os
import glob
import socket
import logging
from string import Template

from .config import (FAUXNET_VHOSTS_WWW, FAUXNET_VHOSTS_CONFIG, FAUXNET_CONFIG, FAUXNET_TEMPLATES)

logger = logging.getLogger("fauxnet")

async def generate_hosts_nginx(progress_tracker=None):
    """Generate hosts entries for each vhost discovered in vhosts_www"""
    # Scan vhosts_www to find all discovered hosts
    vhosts_www = list(glob.glob(f"{FAUXNET_VHOSTS_WWW}/*"))

    logger.info(f'Generating hosts entries for {len(vhosts_www)} vhosts...')

    tasks = []
    for vhost_www_dir in vhosts_www:
        vhost_name = os.path.basename(vhost_www_dir)
        task = asyncio.create_task(generate_vhost_hosts_entry(vhost_name))
        tasks.append(task)

    if progress_tracker:
        completed = 0
        for task in asyncio.as_completed(tasks):
            await task
            completed += 1
            progress_tracker.update(4, "Generating hosts", completed, len(tasks),
                                   f"Generated {completed}/{len(tasks)} hosts entries")
    else:
        await asyncio.gather(*tasks)

    logger.info(f'Completed generating {len(tasks)} hosts entries')

async def generate_vhost_hosts_entry(vhost_name):
    """Generate host entry for a single vhost"""
    try:
        logger.debug(f"[{vhost_name}] Gathering IP Address from external DNS")
        vhost_ip = socket.gethostbyname(vhost_name)
    except socket.gaierror:
        vhost_ip = "1.0.0.0"
        logger.warning(f"[{vhost_name}] Unable to resolve IP address, using fallback IP {vhost_ip}")

    # Store hosts file in vhosts_config
    vhost_config_dir = os.path.join(FAUXNET_VHOSTS_CONFIG, vhost_name)
    os.makedirs(vhost_config_dir, exist_ok=True)

    hosts_file = os.path.join(vhost_config_dir, "hosts")
    with open(hosts_file, 'w') as f:
        f.write(f"{vhost_ip} {vhost_name}\n")
    logger.debug(f"[{vhost_name}] Wrote {vhost_ip} {vhost_name} to {hosts_file}")

async def generate_nginx_conf(site_urls=None, progress_tracker=None):
    """Generate nginx.conf for all vhosts discovered in vhosts_www"""
    # Scan vhosts_www to find all discovered hosts
    vhosts_www = list(glob.glob(f"{FAUXNET_VHOSTS_WWW}/*"))

    logger.info(f'Generating nginx configs for {len(vhosts_www)} vhosts...')

    nginx_conf = os.path.join(FAUXNET_CONFIG, "nginx.conf")
    if os.path.exists(nginx_conf):
        os.remove(nginx_conf)

    # Generate base nginx.conf
    try:
        with open(nginx_conf, 'w') as f:
            with open(os.path.join(FAUXNET_TEMPLATES, "nginx.conf_base"), 'r') as template:
                template_source = Template(template.read())
                template_result = template_source.substitute(
                    FAUXNET_CONFIG=FAUXNET_CONFIG,
                    FAUXNET_VHOSTS=FAUXNET_VHOSTS_WWW
                )
            f.write(template_result)
            f.write(f"\n    # Include all vhost configurations from vhosts_config\n")
            f.write(f"    include {FAUXNET_VHOSTS_CONFIG}/*/nginx.conf;\n")
            f.write("}\n")
            f.flush()
    except Exception as e:
        logger.error(f'Failed writing base for nginx.conf: {str(e)}')

    # Generate individual vhost configs
    try:
        with open(os.path.join(FAUXNET_TEMPLATES, "nginx.conf_vhost"), 'r') as template:
            template_source = Template(template.read())

            completed = 0
            for vhost_www_dir in vhosts_www:
                vhost_name = os.path.basename(vhost_www_dir)

                # Config files go in vhosts_config
                vhost_config_dir = os.path.join(FAUXNET_VHOSTS_CONFIG, vhost_name)
                os.makedirs(vhost_config_dir, exist_ok=True)

                cert_path = os.path.join(vhost_config_dir, f"{vhost_name}.cer")

                # Web content is in vhosts_www
                html_dir = os.path.join(FAUXNET_VHOSTS_WWW, vhost_name)

                vhost_nginx_conf = os.path.join(vhost_config_dir, "nginx.conf")
                with open(vhost_nginx_conf, 'w') as f:
                    nginx_block = template_source.substitute(
                        cert_path=cert_path,
                        vhost_base=vhost_name,
                        vhost=vhost_config_dir,
                        html_dir=html_dir,
                        vh_key=os.path.join(FAUXNET_CONFIG, "fauxnet_vh.key")
                    )
                    f.write(nginx_block)
                logger.debug(f"[{vhost_name}] Wrote {vhost_nginx_conf}")

                completed += 1
                if progress_tracker:
                    progress_tracker.update(5, "Generating nginx configs", completed, len(vhosts_www),
                                           f"Generated config for {vhost_name} ({completed}/{len(vhosts_www)})")
    except Exception as e:
        logger.error(f'Failed writing vhost nginx config: {str(e)}')

    logger.info(f'Completed generating nginx configs for {len(vhosts_www)} vhosts')