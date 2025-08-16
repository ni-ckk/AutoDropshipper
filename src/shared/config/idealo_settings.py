"""
Idealo-specific configuration settings.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class IdealoScraperConfig(BaseSettings):
    """
    Configuration for Idealo scraper.
    
    Attributes:
        SCRAPE_URL_IDEALO: Base URL for Idealo scraping
        MAX_PAGES_TO_SCRAPE: Maximum number of pages to scrape
        IS_HEADLESS_IDEALO: Whether to run browser in headless mode
        PAGE_LOAD_TIMEOUT: Timeout for page loading in seconds
        ELEMENT_WAIT_TIMEOUT: Timeout for element waiting in seconds
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    SCRAPE_URL_IDEALO: str = Field(default="https://www.idealo.de/preisvergleich/MainSearchProductCategory.html", description="Idealo search URL")
    MAX_PAGES_TO_SCRAPE: int = Field(default=2, ge=1, le=100)
    IS_HEADLESS_IDEALO: bool = Field(default=False)
    PAGE_LOAD_TIMEOUT: int = Field(default=30, ge=5, le=120)
    ELEMENT_WAIT_TIMEOUT: int = Field(default=10, ge=1, le=60)
    
    @field_validator("MAX_PAGES_TO_SCRAPE")
    @classmethod
    def validate_max_pages(cls, v: int) -> int:
        """
        Validates maximum pages to scrape.
        
        Args:
            v: Number of pages
            
        Returns:
            Validated page count
            
        Raises:
            ValueError: If page count is invalid
        """
        if v < 1:
            raise ValueError("Must scrape at least 1 page")
        if v > 100:
            raise ValueError("Cannot scrape more than 100 pages")
        return v
    
    @field_validator("SCRAPE_URL_IDEALO")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """
        Validates Idealo URL.
        
        Args:
            v: URL string
            
        Returns:
            Validated URL
            
        Raises:
            ValueError: If URL is invalid
        """
        if not v.startswith("https://www.idealo.de"):
            raise ValueError("URL must be from idealo.de domain")
        return v


@lru_cache()
def get_idealo_config() -> IdealoScraperConfig:
    """
    Get cached Idealo configuration.
    
    Returns:
        Idealo scraper configuration instance
    """
    return IdealoScraperConfig()