#!/usr/bin/env python3
"""
Fauxnet Scraper - Main Orchestrator
Coordinates all scraping, certificate generation, and nginx configuration
Integrated version for FastAPI backend
"""

import asyncio
import os
import logging
import shutil

from .config import setup_environment, FAUXNET_ORIG, FAUXNET_CONFIG
from .utils import setup_logging
from .scraper import download_websites, get_discovered_urls
from .certificates import generate_CA, generate_vhost_certificates
from .nginx_config_generator import generate_hosts_nginx, generate_nginx_conf
from .landing_page import generate_landing_page, generate_sites_summary
from .ncsi_generator import generate_ncsi_site

logger = logging.getLogger("fauxnet")


async def scrape_sites_async(sites_file=None, sites_list=None, options=None, progress_tracker=None):
    """
    Main orchestration function (async version for FastAPI)

    Args:
        sites_file: Path to file containing URLs to scrape (one per line)
        sites_list: List of URLs to scrape directly
        options: Optional dict with scraping options (depth, page_requisites)
            Note: span_hosts and convert_links are always enabled (matching topgen-scrape.sh)
        progress_tracker: Optional progress tracker for reporting progress

    Returns:
        Dict with success status and details
    """
    # Setup environment
    setup_environment()
    setup_logging()

    logger.info("Starting Fauxnet Scraper")

    # Determine which sites to scrape
    if sites_list:
        urls = sites_list
        logger.info(f"Scraping {len(urls)} sites from provided list")
    elif sites_file:
        if not os.path.exists(sites_file):
            logger.error(f"Sites file not found: {sites_file}")
            return {"success": False, "error": f"Sites file not found: {sites_file}"}

        with open(sites_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        logger.info(f"Scraping {len(urls)} sites from {sites_file}")
    else:
        # Use default file
        if not os.path.exists(FAUXNET_ORIG):
            logger.error(f"Default sites file not found: {FAUXNET_ORIG}")
            return {"success": False, "error": f"Default sites file not found: {FAUXNET_ORIG}"}

        with open(FAUXNET_ORIG, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        logger.info(f"Scraping {len(urls)} sites from default file")

    if not urls:
        logger.error("No URLs to scrape")
        return {"success": False, "error": "No URLs to scrape"}

    # Always ensure Microsoft NCSI (Network Connectivity Status Indicator) is included
    # This is used by Windows to check internet connectivity
    ncsi_url = "http://www.msftncsi.com"
    if ncsi_url not in urls and f"https://www.msftncsi.com" not in urls:
        urls.append(ncsi_url)
        logger.info(f"Added Microsoft NCSI site: {ncsi_url}")

    try:
        # Phase 1: Generate CA
        logger.info("Phase 1: Generating Certificate Authority")
        if progress_tracker:
            progress_tracker.update(1, "Generating CA", 0, 1, "Generating Certificate Authority...")
        await generate_CA()

        # Phase 2: Download websites
        logger.info("Phase 2: Downloading websites")
        if progress_tracker:
            progress_tracker.update(2, "Downloading websites", 0, len(urls), f"Downloading {len(urls)} websites...")
        await download_websites(urls, options, progress_tracker)

        # Get discovered URLs from scraping
        site_urls = get_discovered_urls()

        # Phase 2.5: Ensure Microsoft NCSI site is created before cert/config generation
        logger.info("Phase 2.5: Ensuring Microsoft NCSI site")
        if progress_tracker:
            progress_tracker.update(2, "NCSI site", 0, 1, "Ensuring Microsoft NCSI site...")
        generate_ncsi_site()

        # Phase 3: Generate certificates
        logger.info("Phase 3: Generating SSL certificates")
        if progress_tracker:
            progress_tracker.update(3, "Generating certificates", 0, 0, "Generating SSL certificates...")
        await generate_vhost_certificates(progress_tracker)

        # Phase 4: Generate hosts entries
        logger.info("Phase 4: Generating hosts entries")
        if progress_tracker:
            progress_tracker.update(4, "Generating hosts", 0, 0, "Generating hosts entries...")
        await generate_hosts_nginx(progress_tracker)

        # Phase 5: Generate nginx configs
        logger.info("Phase 5: Generating nginx configurations")
        if progress_tracker:
            progress_tracker.update(5, "Generating nginx configs", 0, 0, "Generating nginx configurations...")
        await generate_nginx_conf(site_urls, progress_tracker)

        # Phase 6: Generate landing page
        logger.info("Phase 6: Generating fauxnet.info landing page")
        if progress_tracker:
            progress_tracker.update(6, "Generating landing page", 0, 1, "Generating fauxnet.info landing page...")
        await generate_landing_page()

        # Phase 7: Generate sites summary (optional, for reference)
        logger.info("Phase 7: Generating sites summary")
        if progress_tracker:
            progress_tracker.update(7, "Generating summary", 0, 1, "Generating sites summary...")
        await generate_sites_summary(site_urls)

        # Cleanup temporary CA directory
        from . import config
        if config.TMP_CA_DIR and os.path.exists(config.TMP_CA_DIR):
            logger.debug(f"Cleaning up temporary CA directory: {config.TMP_CA_DIR}")
            shutil.rmtree(config.TMP_CA_DIR)

        logger.info("✓ Fauxnet Scraper completed successfully")

        if progress_tracker:
            progress_tracker.complete()

        return {
            "success": True,
            "sites_scraped": len(urls),
            "urls_discovered": sum(len(urls) for urls in site_urls.values()),
            "config_location": FAUXNET_CONFIG
        }

    except Exception as e:
        logger.error(f"Fauxnet Scraper failed: {str(e)}", exc_info=True)
        if progress_tracker:
            progress_tracker.error_occurred(str(e))
        return {"success": False, "error": str(e)}
