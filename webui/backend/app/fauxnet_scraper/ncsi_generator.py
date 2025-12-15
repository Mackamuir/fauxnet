#!/usr/bin/env python3
"""
Microsoft NCSI (Network Connectivity Status Indicator) Generator

Windows uses NCSI to detect internet connectivity. This module ensures
the proper NCSI files are generated for www.msftncsi.com
"""

import os
import logging
from .config import FAUXNET_VHOSTS_WWW, FAUXNET_VHOSTS_CONFIG

logger = logging.getLogger("fauxnet")


def generate_ncsi_site():
    """
    Generate the Microsoft NCSI site with proper content

    Windows checks:
    - HTTP: http://www.msftncsi.com/ncsi.txt (should return "Microsoft NCSI")
    - HTTPS: https://www.msftncsi.com/ncsi.txt (should return "Microsoft NCSI")
    - DNS: dns.msftncsi.com (should resolve to 131.107.255.255)

    This function creates the necessary files for HTTP/HTTPS checks and DNS resolution.
    """
    ncsi_vhost = os.path.join(FAUXNET_VHOSTS_WWW, "www.msftncsi.com")
    ncsi_config = os.path.join(FAUXNET_VHOSTS_CONFIG, "www.msftncsi.com")

    # Create vhost directories if they don't exist
    os.makedirs(ncsi_vhost, exist_ok=True)
    os.makedirs(ncsi_config, exist_ok=True)

    # Create ncsi.txt with exact content Windows expects
    ncsi_txt_path = os.path.join(ncsi_vhost, "ncsi.txt")
    with open(ncsi_txt_path, 'w') as f:
        f.write("Microsoft NCSI")

    logger.info(f"Generated NCSI content at {ncsi_txt_path}")

    # Create a simple index.html for the NCSI site
    index_html_path = os.path.join(ncsi_vhost, "index.html")
    if not os.path.exists(index_html_path):
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Microsoft Network Connectivity Status Indicator</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f0f0f0;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #0078d4;
            border-bottom: 3px solid #0078d4;
            padding-bottom: 10px;
        }
        .info-box {
            background: #e7f3ff;
            border-left: 4px solid #0078d4;
            padding: 15px;
            margin: 20px 0;
        }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        .status {
            color: #107c10;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Microsoft Network Connectivity Status Indicator (NCSI)</h1>

        <div class="info-box">
            <p><strong>Status:</strong> <span class="status">Active</span></p>
        </div>

        <h2>About NCSI</h2>
        <p>
            This site provides the Network Connectivity Status Indicator service used by Windows
            to detect internet connectivity and captive portals.
        </p>

        <h2>Connectivity Checks</h2>
        <p>Windows performs the following checks:</p>
        <ul>
            <li><strong>HTTP:</strong> <code>http://www.msftncsi.com/ncsi.txt</code> - Should return "Microsoft NCSI"</li>
            <li><strong>HTTPS:</strong> <code>https://www.msftncsi.com/ncsi.txt</code> - Should return "Microsoft NCSI"</li>
            <li><strong>DNS:</strong> <code>dns.msftncsi.com</code> - Should resolve to 131.107.255.255</li>
        </ul>

        <h2>Files Available</h2>
        <ul>
            <li><a href="/ncsi.txt">ncsi.txt</a> - NCSI probe file</li>
            <li><a href="/connecttest.txt">connecttest.txt</a> - Alternative connectivity test</li>
        </ul>

        <div class="info-box">
            <p><strong>Note:</strong> This is a simulated NCSI service running in Fauxnet for training and testing purposes.</p>
        </div>
    </div>
</body>
</html>"""
        with open(index_html_path, 'w') as f:
            f.write(index_html)
        logger.info(f"Generated NCSI index.html at {index_html_path}")

    # Create connecttest.txt (alternative connectivity check)
    connecttest_path = os.path.join(ncsi_vhost, "connecttest.txt")
    with open(connecttest_path, 'w') as f:
        f.write("Microsoft Connect Test")

    logger.info(f"Generated connecttest.txt at {connecttest_path}")

    # Create hosts file with DNS entry for dns.msftncsi.com
    # Windows expects dns.msftncsi.com to resolve to 131.107.255.255
    hosts_path = os.path.join(ncsi_config, "hosts")
    with open(hosts_path, 'w') as f:
        # Add www.msftncsi.com (try to resolve or use fallback)
        try:
            import socket
            www_ip = socket.gethostbyname("www.msftncsi.com")
        except socket.gaierror:
            www_ip = "131.107.255.255"  # Fallback to Microsoft's NCSI IP

        f.write(f"{www_ip} www.msftncsi.com\n")

        # Add dns.msftncsi.com - this is the DNS probe Windows uses
        # Must resolve to 131.107.255.255 for Windows to detect connectivity
        f.write("131.107.255.255 dns.msftncsi.com\n")

    logger.info(f"Generated NCSI hosts file at {hosts_path} with DNS entry for dns.msftncsi.com")

    return True
