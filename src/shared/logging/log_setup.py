"""
Centralized logging configuration using structlog with colorful console output.
"""

import logging
import sys
from typing import Any, Optional

import colorama
import structlog
from structlog.dev import Column, ConsoleRenderer, KeyValueColumnFormatter


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
) -> None:
    """
    Configure clean, colorful structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for log output
    """
    # initialize colorama for cross-platform color support (especially Windows)
    colorama.init()
    
    # create custom colorful console renderer
    console_renderer = ConsoleRenderer(
        columns=[
            # log level at start - bright white
            Column(
                "level",
                KeyValueColumnFormatter(
                    key_style=None,  # hide 'level=' prefix
                    value_style=colorama.Style.BRIGHT + colorama.Fore.WHITE,
                    reset_style=colorama.Style.RESET_ALL,
                    value_repr=str,
                ),
            ),
            # timestamp - yellow, short format
            Column(
                "timestamp", 
                KeyValueColumnFormatter(
                    key_style=None,  # hide 'timestamp=' prefix
                    value_style=colorama.Fore.YELLOW,
                    reset_style=colorama.Style.RESET_ALL,
                    value_repr=str,
                ),
            ),
            # logger name - cyan
            Column(
                "logger",
                KeyValueColumnFormatter(
                    key_style=None,  # hide 'logger=' prefix  
                    value_style=colorama.Fore.CYAN,
                    reset_style=colorama.Style.RESET_ALL,
                    value_repr=str,
                ),
            ),
            # event - bright magenta
            Column(
                "event",
                KeyValueColumnFormatter(
                    key_style=None,  # hide 'event=' prefix
                    value_style=colorama.Style.BRIGHT + colorama.Fore.MAGENTA,
                    reset_style=colorama.Style.RESET_ALL,
                    value_repr=str,
                ),
            ),
            # other fields - green values, dim cyan keys
            Column(
                "",  # catch-all for other fields
                KeyValueColumnFormatter(
                    key_style=colorama.Style.DIM + colorama.Fore.CYAN,
                    value_style=colorama.Fore.GREEN,
                    reset_style=colorama.Style.RESET_ALL,
                    value_repr=str,
                ),
            ),
        ]
    )
    
    # store log level for filtering
    current_log_level = getattr(logging, log_level.upper())
    
    # custom processor to add logger name and level manually
    def add_logger_info(logger, name, event_dict):
        """Add logger name and level manually since WriteLogger doesn't have these attributes."""
        # add level from method name
        level_mapping = {
            "debug": "DEBUG",
            "info": "INFO", 
            "warning": "WARNING",
            "error": "ERROR",
            "critical": "CRITICAL"
        }
        event_dict["level"] = level_mapping.get(name, name.upper())
        
        # add logger name from the bound logger context if available
        # fallback to a simple name extraction
        if hasattr(logger, '_context') and 'logger' in logger._context:
            event_dict["logger"] = logger._context['logger']
        else:
            # extract logger name from the logger object or use a default
            event_dict["logger"] = getattr(logger, '_name', 'app')
        
        return event_dict
    
    # custom level filter
    def level_filter(logger, name, event_dict):
        """Filter events based on log level."""
        level_numbers = {
            "debug": 10,
            "info": 20,
            "warning": 30,
            "error": 40,
            "critical": 50
        }
        
        event_level = level_numbers.get(name.lower(), 20)
        if event_level < current_log_level:
            raise structlog.DropEvent
        
        return event_dict
    
    # build processor chain for console output
    console_processors = [
        level_filter,  # filter by log level first
        add_logger_info,  # custom processor for logger info
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),  # short time format
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        console_renderer,  # final colorful rendering
    ]
    
    # configure structlog
    structlog.configure(
        processors=console_processors,
        logger_factory=structlog.WriteLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
    
    # optional file output (if requested)
    if log_file:
        # create separate file logger with JSON format for structured logs
        file_processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
        
        # note: file logging would require additional configuration
        # for now, focusing on clean console output


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    # create logger with bound context containing the logger name
    logger = structlog.get_logger()
    # store the name in the logger for our custom processor
    logger._name = name.split('.')[-1] if '.' in name else name  # use just the module name
    return logger


def log_scraping_progress(
    logger: structlog.BoundLogger,
    action: str,
    page: Optional[int] = None,
    total_pages: Optional[int] = None,
    items_found: Optional[int] = None,
    **extra_context: Any
) -> None:
    """
    Log scraping progress with structured data.
    
    Args:
        logger: Logger instance
        action: Action being performed
        page: Current page number
        total_pages: Total pages to scrape
        items_found: Number of items found
        **extra_context: Additional context data
    """
    context = {
        "action": action,
        "scraper": "active",
    }
    
    if page is not None:
        context["page"] = str(page)
    if total_pages is not None:
        context["total_pages"] = str(total_pages)
        if page is not None:
            context["progress"] = f"{page}/{total_pages}"
    if items_found is not None:
        context["items_found"] = str(items_found)
    
    context.update(extra_context)
    
    logger.info("scraping_progress", **context)