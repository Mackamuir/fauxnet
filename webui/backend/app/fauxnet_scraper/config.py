#!/usr/bin/env python3
"""
Fauxnet Configuration
Central configuration for all Fauxnet modules
"""

import os
import resource

# Fauxnet paths
FAUXNET_BASE = os.path.realpath("/opt/fauxnet")
FAUXNET_VHOSTS_WWW = os.path.join(FAUXNET_BASE, "vhosts_www")  # Web content only
FAUXNET_VHOSTS_CONFIG = os.path.join(FAUXNET_BASE, "vhosts_config")  # Certs, nginx configs, hosts files
FAUXNET_CONFIG = os.path.join(FAUXNET_BASE, "config")

# Legacy compatibility
FAUXNET_VHOSTS = FAUXNET_VHOSTS_WWW  # For backward compatibility with existing code

# Templates are relative to this config file
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FAUXNET_TEMPLATES = os.path.join(_THIS_DIR, "templates")

FAUXNET_ORIG = os.path.join(FAUXNET_CONFIG, "scrape_sites.txt")
FAUXNET_CUSTOM_VHOSTS = os.path.join(FAUXNET_BASE, "custom_vhosts")

# fauxnet.info vhost directory:
FAUXNET_SITE = os.path.join(FAUXNET_VHOSTS_WWW, "fauxnet.info")

# The maximum number of open file descriptors
FAUXNET_NOFILE = 8192

# Global state
TMP_CA_DIR = None
CA_CONF_PATH = None

def setup_environment():
    """Setup environment and ensure directories exist"""
    # Set file descriptor limits
    try:
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (FAUXNET_NOFILE, FAUXNET_NOFILE)
        )
    except Exception:
        # If we can't set limits, just continue
        pass

    # Ensure directories exist
    os.makedirs(FAUXNET_VHOSTS_WWW, exist_ok=True)
    os.makedirs(FAUXNET_VHOSTS_CONFIG, exist_ok=True)
    os.makedirs(FAUXNET_CONFIG, exist_ok=True)
