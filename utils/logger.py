"""
Logging utilities for the car deals scraper
"""

import logging
import sys
from typing import Optional


def setup_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """
    Set up a logger with console output
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers
    if logger.handlers:
        return logger
    
    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Create console handler with stderr instead of stdout
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(numeric_level)
    
    # Create simple formatter
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger
