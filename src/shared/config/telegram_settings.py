"""
Telegram notification configuration.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramConfig(BaseSettings):
    """
    Configuration for Telegram notifications.
    
    Attributes:
        TELEGRAM_BOT_TOKEN: Bot API token
        TELEGRAM_CHAT_ID: Chat ID for notifications
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(None, description="Telegram bot token")
    TELEGRAM_CHAT_ID: Optional[str] = Field(None, description="Telegram chat ID")
    
    @property
    def is_configured(self) -> bool:
        """
        Checks if Telegram is properly configured.
        
        Returns:
            True if both token and chat ID are set
        """
        return bool(self.TELEGRAM_BOT_TOKEN and self.TELEGRAM_CHAT_ID)


@lru_cache()
def get_telegram_config() -> TelegramConfig:
    """
    Get cached Telegram configuration.
    
    Returns:
        Telegram configuration instance
    """
    return TelegramConfig()