#!/usr/bin/env python3
"""
Fauxnet Utilities
Helper functions and utilities
"""

import logging

logger = logging.getLogger("fauxnet")

def format_elapsed_time(seconds):
    """Format elapsed time showing only non-zero hours and minutes"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    elif minutes > 0:
        return f"{minutes}m {secs:02d}s"
    else:
        return f"{secs}s"

def setup_logging():
    """Configure logging for Fauxnet"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s: %(message)s',
    )

    logger = logging.getLogger("fauxnet")
    logger.addHandler(logging.StreamHandler())
    return logger