"""
eBay-specific configuration settings.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EbayScraperConfig(BaseSettings):
    """
    Configuration for eBay scraper.
    
    Attributes:
        IS_HEADLESS_EBAY: Whether to run browser in headless mode
        MAX_BESTMATCH_ITEMS: Maximum number of best match items to collect
        MAX_LEASTMATCH_ITEMS: Maximum number of less relevant items to collect
        EBAY_MIN_PRICE: Minimum price filter for eBay searches
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    IS_HEADLESS_EBAY: bool = Field(default=True)
    PAGE_LOAD_TIMEOUT: int = Field(default=30, ge=5, le=120)
    MAX_BESTMATCH_ITEMS: int = Field(default=10, ge=1, le=50)
    MAX_LEASTMATCH_ITEMS: int = Field(default=10, ge=1, le=20)
    EBAY_MIN_PRICE: int = Field(default=50, ge=0)


@lru_cache()
def get_ebay_config() -> EbayScraperConfig:
    """
    Get cached eBay configuration.
    
    Returns:
        eBay scraper configuration instance
    """
    return EbayScraperConfig()