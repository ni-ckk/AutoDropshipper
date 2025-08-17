"""
General application settings and environment variables.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .ebay_settings import EbayScraperConfig
from .idealo_settings import IdealoScraperConfig


class DatabaseConfig(BaseSettings):
    """
    Database configuration settings.
    
    Attributes:
        POSTGRES_DB: Database name
        POSTGRES_USER: Database username
        POSTGRES_PASSWORD: Database password
        POSTGRES_HOST: Database host
        DB_PORT: Database port
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    POSTGRES_DB: str = Field(default="autodropshipper", description="PostgreSQL database name")
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="", description="PostgreSQL password")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    DB_PORT: int = Field(default=5432, description="PostgreSQL port")


class AppConfig(BaseSettings):
    """
    Main application configuration combining all settings.
    
    Attributes:
        DEBUG: Debug mode flag
        SECRET_KEY: Django secret key
        PROFIT_PERCENTAGE_BASELINE: Baseline profit percentage for comparisons
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    DEBUG: bool = Field(default=False)
    SECRET_KEY: str = Field(default="django-insecure-dev-key", description="Django secret key")
    PROFIT_PERCENTAGE_BASELINE: float = Field(default=25.0, description="Baseline profit percentage for comparisons")
    EBAY_CHECK_THRESHOLD_DAYS: int = Field(default=14, description="Days after which eBay data is considered stale")
    
    @property
    def database(self) -> DatabaseConfig:
        """Gets database configuration."""
        return DatabaseConfig()
    
    @property
    def idealo(self) -> IdealoScraperConfig:
        """Gets Idealo scraper configuration."""
        from .idealo_settings import get_idealo_config
        return get_idealo_config()
    
    @property
    def ebay(self) -> EbayScraperConfig:
        """Gets eBay scraper configuration."""
        from .ebay_settings import get_ebay_config
        return get_ebay_config()


@lru_cache()
def get_app_config() -> AppConfig:
    """
    Get cached application configuration.
    
    Returns:
        Application configuration instance
    """
    return AppConfig()