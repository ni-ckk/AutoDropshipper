"""
Exceptions for scraping-related errors.
"""

from typing import Optional

from .base import AutoDropshipperError, ValidationError


class ScrapingError(AutoDropshipperError):
    """Base exception for scraping-related errors."""
    
    pass


class PageLoadError(ScrapingError):
    """Raised when a page fails to load."""
    
    def __init__(self, url: str, message: str):
        """
        Initialize page load error.
        
        Args:
            url: URL that failed to load
            message: Error message
        """
        self.url = url
        super().__init__(f"Failed to load {url}: {message}")


class ElementNotFoundError(ScrapingError):
    """Raised when an expected element is not found on page."""
    
    def __init__(self, selector: str, page_url: Optional[str] = None):
        """
        Initialize element not found error.
        
        Args:
            selector: CSS selector or XPath that wasn't found
            page_url: URL of the page if available
        """
        self.selector = selector
        self.page_url = page_url
        message = f"Element not found: {selector}"
        if page_url:
            message += f" on page {page_url}"
        super().__init__(message)


class CookieConsentError(ScrapingError):
    """Raised when cookie consent handling fails."""
    
    def __init__(self, message: str = "Failed to handle cookie consent"):
        """
        Initialize cookie consent error.
        
        Args:
            message: Error message
        """
        super().__init__(message)


class PriceParsingError(ValidationError):
    """Raised when price parsing fails."""
    
    def __init__(self, price_text: str):
        """
        Initialize price parsing error.
        
        Args:
            price_text: Raw price text that couldn't be parsed
        """
        super().__init__(
            field="price",
            value=price_text,
            message=f"Cannot parse price from '{price_text}'"
        )


class TimeoutError(ScrapingError):
    """Raised when a scraping operation times out."""
    
    def __init__(self, operation: str, timeout_seconds: int):
        """
        Initialize timeout error.
        
        Args:
            operation: Operation that timed out
            timeout_seconds: Timeout duration
        """
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Operation '{operation}' timed out after {timeout_seconds} seconds")