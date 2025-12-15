#!/usr/bin/env python3
"""
Fauxnet Website Scraper
Handles downloading and spidering of websites
"""

import asyncio
import os
import logging
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import defaultdict

from .config import FAUXNET_VHOSTS_WWW, FAUXNET_VHOSTS
from .utils import format_elapsed_time

logger = logging.getLogger("fauxnet")

# Store discovered URLs for each site
SITE_URLS = defaultdict(set)

async def download_websites(urls, options=None, progress_tracker=None):
    """Download all websites from URL list

    Args:
        urls: List of URLs to download
        options: Optional dict with scraping options (depth, page_requisites)
            Note: span_hosts and convert_links are always enabled (matching topgen-scrape.sh)
        progress_tracker: Optional progress tracker for reporting progress
    """

    # Set default options if not provided
    if options is None:
        options = {
            'depth': 1,
            'page_requisites': True,
        }

    tasks = []
    # Create task list
    for url in urls:
        if url.startswith('#'):
            continue
        task = asyncio.create_task(download_website(url, options, progress_tracker))
        tasks.append(task)

    logger.info(f'Scraping {len(tasks)} websites...')

    # Run all tasks and track completion
    if progress_tracker:
        completed = 0
        for task in asyncio.as_completed(tasks):
            await task
            completed += 1
            progress_tracker.update(2, "Downloading websites", completed, len(tasks),
                                   f"Downloaded {completed}/{len(tasks)} websites")
    else:
        await asyncio.gather(*tasks)

    logger.info(f'Completed scraping {len(tasks)} websites')

async def download_website(url, options, progress_tracker=None):
    """Download website with configurable options

    Args:
        url: URL to download
        options: Dict with scraping options (depth, page_requisites)
            Note: span_hosts (-H) and convert_links are always enabled
        progress_tracker: Optional progress tracker for reporting progress
    """
    url = url.strip()
    if not url:
        raise ValueError("URL is empty")

    hostname = urlparse(url).hostname
    import time
    start_time = time.time()

    try:
        logger.info(f'Scraping {hostname}...')
        # Download to vhosts_www - wget will create subdirectories for each host discovered
        # Use FAUXNET_VHOSTS which is aliased to FAUXNET_VHOSTS_WWW
        vhosts_www_dir = FAUXNET_VHOSTS
        os.makedirs(vhosts_www_dir, exist_ok=True)

        # Build wget command matching topgen-scrape.sh behavior
        wget_cmd = "/usr/bin/wget -v"

        # Add page requisites flag (-p)
        if options.get('page_requisites', True):
            wget_cmd += " -p"

        # Add recursive flag based on depth
        if options.get('depth', 1) == 0:
            wget_cmd += " -r"  # Unlimited recursion
        elif options.get('depth', 1) > 1:
            wget_cmd += f" -r -l {options['depth']}"  # Recursive with depth limit
        # If depth == 1, no -r flag (landing page only)

        # Common flags from topgen-scrape.sh
        # -E: adjust extension (.html)
        # -H: span hosts for CDN/external resources (creates subdirs per host)
        # -N: timestamping (don't re-download if not newer)
        # --convert-file-only: convert links for offline browsing
        # --no-check-certificate: ignore SSL cert errors
        # -e robots=off: ignore robots.txt
        # --random-wait: random wait between downloads
        # -t 2: retry 2 times
        wget_cmd += " -E -H -N --convert-file-only --no-check-certificate"
        wget_cmd += " -e robots=off --random-wait -t 2 -U 'Mozilla/5.0 (X11)'"
        wget_cmd += f" -P {vhosts_www_dir} {url}"

        logger.debug(f"[{hostname}] Running wget command: {wget_cmd}")

        proc = await asyncio.create_subprocess_shell(
            wget_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Process stdout and stderr streams
        async def read_stream(stream):
            while True:
                line = await stream.readline()
                if not line:
                    break
                logger.debug(f'[{hostname}] {line.decode().strip()}')
        
        stdout_task = asyncio.create_task(read_stream(proc.stdout))
        stderr_task = asyncio.create_task(read_stream(proc.stderr))
        
        await proc.wait()
        await stdout_task
        await stderr_task
        
        if proc.returncode != 0:
            logger.error(f'{hostname}: wget returned non-zero exit code {proc.returncode}')

        # After downloading, spider the page to discover URLs
        await spider_website(url, hostname)

        elapsed = time.time() - start_time
        logger.info(f'✓ {hostname} ({format_elapsed_time(elapsed)})')

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f'Failed {hostname} after {format_elapsed_time(elapsed)}: {str(e)}')

async def spider_website(url, hostname):
    """Spider the downloaded landing page to discover all links"""
    try:
        # With -P vhosts_www and -nH, wget creates: vhosts_www/hostname/index.html
        vhost_www_dir = os.path.join(FAUXNET_VHOSTS, hostname)

        # Look for index.html in the vhost directory
        index_path = os.path.join(vhost_www_dir, "index.html")

        if not os.path.exists(index_path):
            logger.warning(f'[{hostname}] No index.html found at {index_path}')
            return
        
        # Parse HTML to find all links
        with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        base_url = url.strip()
        discovered_urls = set()
        
        # Extract all URLs from various tags
        for tag in soup.find_all(['a', 'link', 'script', 'img', 'iframe']):
            href = tag.get('href') or tag.get('src')
            if href:
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                parsed = urlparse(absolute_url)
                
                # Only keep URLs from the same domain
                if parsed.hostname == hostname:
                    path = parsed.path or '/'
                    if parsed.query:
                        path += f'?{parsed.query}'
                    discovered_urls.add(path)
        
        # Store discovered URLs
        SITE_URLS[hostname] = discovered_urls
        logger.info(f'[{hostname}] Discovered {len(discovered_urls)} URLs')
        
    except Exception as e:
        logger.error(f'[{hostname}] Failed to spider website: {str(e)}')

def get_discovered_urls():
    """Get all discovered URLs"""
    return SITE_URLS