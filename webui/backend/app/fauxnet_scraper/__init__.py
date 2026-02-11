"""
Fauxnet Scraper Package
Modular website scraping and virtual host generation
"""

from .main import scrape_sites_async, scrape_phases_async

__all__ = ['scrape_sites_async', 'scrape_phases_async']
