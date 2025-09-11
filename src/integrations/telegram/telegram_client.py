"""
Telegram Bot API client for sending messages and images.
"""

import requests
from typing import Optional

from src.core.exceptions.base import AutoDropshipperError
from src.shared.config.telegram_settings import get_telegram_config
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class TelegramNotificationError(AutoDropshipperError):
    """Raised when Telegram notification fails."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        """
        Initialize Telegram notification error.
        
        Args:
            message: Error message
            status_code: HTTP status code if available
        """
        self.status_code = status_code
        super().__init__(message)


class TelegramClient:
    """Handles Telegram Bot API operations."""
    
    def __init__(self):
        """Initialize Telegram client with configuration."""
        self.config = get_telegram_config()
    
    def send_notification(self, message: str) -> bool:
        """
        Send text notification to Telegram chat.
        
        Args:
            message: Message text to send
            
        Returns:
            True if sent successfully
            
        Raises:
            TelegramNotificationError: If sending fails
        """
        if not self.config.is_configured:
            logger.warning("telegram_not_configured", action="skip_notification")
            return False
        
        # validate message is not empty
        if not message or not message.strip():
            logger.error("telegram_empty_message", action="skip_notification")
            raise TelegramNotificationError("Cannot send empty message to Telegram")
        
        # telegram has a 4096 character limit for messages
        if len(message) > 4096:
            logger.warning("telegram_message_too_long", original_length=len(message))
            message = message[:4090] + "\n\n..."  # truncate with ellipsis
        
        url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': self.config.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            logger.info("telegram_notification_sent")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error("telegram_notification_failed", error=str(e))
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            raise TelegramNotificationError(
                f"Failed to send Telegram notification: {e}",
                status_code
            )
    
    def send_photo(self, photo_path: str, caption: str = "") -> bool:
        """
        Send photo with caption to Telegram chat.
        
        Args:
            photo_path: Path to photo file
            caption: Photo caption text
            
        Returns:
            True if sent successfully
            
        Raises:
            TelegramNotificationError: If sending fails
        """
        if not self.config.is_configured:
            logger.warning("telegram_not_configured", action="skip_photo")
            return False
        
        url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            'chat_id': self.config.TELEGRAM_CHAT_ID,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        
        try:
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                response = requests.post(url, data=payload, files=files)
                response.raise_for_status()
                logger.info("telegram_photo_sent", photo_path=photo_path)
                return True
                
        except FileNotFoundError:
            logger.error("telegram_photo_not_found", photo_path=photo_path)
            raise TelegramNotificationError(f"Screenshot file not found at {photo_path}")
            
        except requests.exceptions.RequestException as e:
            logger.error("telegram_photo_failed", error=str(e))
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            raise TelegramNotificationError(
                f"Failed to send Telegram photo: {e}",
                status_code
            )