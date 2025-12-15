#!/usr/bin/env python3
"""
Fauxnet Certificate Management
Handles CA and vhost certificate generation
"""

import asyncio
import os
import glob
import tempfile
import shutil
import logging
from string import Template

from .config import (FAUXNET_VARETC, FAUXNET_VHOSTS_WWW, FAUXNET_VHOSTS_CONFIG,
                   FAUXNET_SITE, FAUXNET_TEMPLATES)
from . import config

logger = logging.getLogger("fauxnet")

async def generate_CA():
    """Generate SSL certificates for Fauxnet"""
    logger.debug("Checking for existing CA certificates")
    ca_key = os.path.join(FAUXNET_VARETC, "fauxnet_ca.key")
    ca_cert = os.path.join(FAUXNET_VARETC, "fauxnet_ca.cer")

    # Generate CA if not exists
    if not (os.path.exists(ca_key) and os.path.exists(ca_cert)):
        logger.debug("Not Found, Generating CA")
        proc = await asyncio.create_subprocess_exec(
            'openssl', 'req', '-newkey', 'rsa:2048', '-nodes',
            '-keyout', ca_key,
            '-days', '7300', '-x509',
            '-out', ca_cert,
            '-subj', '/C=US/ST=PA/L=Pgh/O=CMU/OU=CERT/CN=fauxnet_ca',
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()

    # Copy CA cert to fauxnet.info site
    os.makedirs(FAUXNET_SITE, exist_ok=True)
    shutil.copy2(ca_cert, FAUXNET_SITE)
    logger.debug("Copied CA cert to fauxnet.info site")

    # Generate shared vhost key
    vh_key = os.path.join(FAUXNET_VARETC, "fauxnet_vh.key")
    if not os.path.exists(vh_key):
        logger.debug("Generating shared vhost key")
        proc = await asyncio.create_subprocess_exec(
            'openssl', 'genrsa',
            '-out', vh_key,
            '2048',
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()

    # Create temporary CA directory
    logger.debug("Creating temporary CA directory")
    tmp_ca_dir = tempfile.mkdtemp(prefix='FauxnetCA.')

    # Create serial and index files
    with open(os.path.join(tmp_ca_dir, "serial"), 'w') as f:
        f.write("000a")
    with open(os.path.join(tmp_ca_dir, "index"), 'w') as f:
        pass

    # Write CA configuration
    ca_conf_path = os.path.join(tmp_ca_dir, "ca.conf")
    ca_dict = {
        'tmp_ca_dir': tmp_ca_dir,
        'ca_cert': ca_cert,
        'ca_key': ca_key
    }

    with open(ca_conf_path, 'w') as f:
        with open(os.path.join(FAUXNET_TEMPLATES, "CertificateAuthority.conf"), 'r') as template:
            template_source = Template(template.read())
            template_result = template_source.substitute(ca_dict)
        f.write(template_result)

    # Store paths in config module
    config.TMP_CA_DIR = tmp_ca_dir
    config.CA_CONF_PATH = ca_conf_path

    logger.debug(f"Certificate generation complete. Temporary CA dir: {tmp_ca_dir}")

async def generate_vhost_certificates(progress_tracker=None):
    """Generate certificates for all vhosts discovered in vhosts_www"""
    # Scan vhosts_www to find all discovered hosts (including CDN hosts from -H flag)
    vhosts_www = list(glob.glob(f"{FAUXNET_VHOSTS_WWW}/*"))

    logger.info(f'Generating certificates for {len(vhosts_www)} vhosts...')

    completed = 0
    for vhost_www_dir in vhosts_www:
        vhost_base = os.path.basename(vhost_www_dir)
        logger.debug(f"[{vhost_base}] Generating Certificate")

        # Create config directory for this vhost
        vhost_config_dir = os.path.join(FAUXNET_VHOSTS_CONFIG, vhost_base)
        os.makedirs(vhost_config_dir, exist_ok=True)

        # Store certificate in the vhost config directory
        cert_path = os.path.join(vhost_config_dir, f"{vhost_base}.cer")

        # Generate certificate (CSR will be created inline)
        proc = await asyncio.create_subprocess_exec(
            'openssl', 'ca', '-batch', '-notext',
            '-config', config.CA_CONF_PATH,
            '-out', cert_path,
            '-in', '-',
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )

        # Generate CSR
        csr_cmd = [
            'openssl', 'req', '-new',
            '-key', os.path.join(FAUXNET_VARETC, "fauxnet_vh.key"),
            '-subj', '/C=US/ST=PA/L=Pgh/O=CMU/OU=CERT/CN=fauxnet_vh',
            '-addext', f'subjectAltName = DNS:{vhost_base}'
        ]

        csr_proc = await asyncio.create_subprocess_exec(
            *csr_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )

        # Get CSR output (no stdin needed - config comes from -subj and -addext)
        csr, _ = await csr_proc.communicate()

        # Sign the CSR with CA
        await proc.communicate(csr)

        logger.debug(f"[{vhost_base}] Wrote certificate to {cert_path}")

        completed += 1
        if progress_tracker:
            progress_tracker.update(3, "Generating certificates", completed, len(vhosts_www),
                                   f"Generated certificate for {vhost_base} ({completed}/{len(vhosts_www)})")

    logger.info(f'Completed generating {len(vhosts_www)} certificates')