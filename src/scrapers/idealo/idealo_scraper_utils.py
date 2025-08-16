"""
Handle Idealo-specific scenarios like pagination, filters, and cookie consent.
"""

import time
from pathlib import Path
from typing import Optional

from seleniumbase import SB

from src.core.exceptions.scraping_errors import CookieConsentError, ElementNotFoundError
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class IdealoScraperUtils:
    """Handles Idealo-specific browser interactions."""
    
    @staticmethod
    def ensure_screenshot_dir() -> Path:
        """
        Ensure screenshot directory exists.
        
        Returns:
            Path to the screenshot directory
        """
        screenshot_dir = Path("temp/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        return screenshot_dir
    
    @staticmethod
    def handle_cookie_consent(sb) -> bool:
        """
        Handle cookie consent banner on Idealo.
        
        Args:
            sb: SeleniumBase driver instance
            
        Returns:
            True if cookie consent was handled successfully
            
        Raises:
            CookieConsentError: If cookie consent fails
        """
        logger.info("handling_cookie_consent")
        
        try:
            # pierce the Shadow DOM for Idealo's cookie banner
            accept_button_selector = "aside#usercentrics-cmp-ui::shadow button#accept"
            
            sb.click(accept_button_selector, timeout=10)
            logger.info("cookie_consent_accepted")
            
            sb.wait_for_element_not_visible("aside#usercentrics-cmp-ui", timeout=5)
            logger.info("cookie_banner_dismissed")
            return True
            
        except Exception as e:
            # ensure screenshot directory exists and save error screenshot
            screenshot_dir = IdealoScraperUtils.ensure_screenshot_dir()
            screenshot_path = str(screenshot_dir / "cookie_error.png")
            
            logger.warning(
                "cookie_consent_failed",
                error=str(e),
                screenshot_saved=screenshot_path
            )
            sb.save_screenshot(screenshot_path)
            
            # wait a bit before raising error
            time.sleep(5)
            raise CookieConsentError(f"Failed to handle cookie consent: {str(e)}")
    
    @staticmethod
    def navigate_to_next_page(sb) -> bool:
        """
        Navigate to the next page of results.
        
        Args:
            sb: SeleniumBase driver instance
            
        Returns:
            True if navigation was successful, False if no next page
        """
        try:
            # scroll to pagination area first
            sb.slow_scroll_to('a[aria-label="Nächste Seite"]')
            time.sleep(2)
            
            # check if next page button exists and is clickable
            next_button = sb.find_element('a[aria-label="Nächste Seite"]')
            if next_button and "disabled" not in next_button.get_attribute("class"):
                sb.click('a[aria-label="Nächste Seite"]')
                time.sleep(3)  # wait for page load
                logger.info("navigated_to_next_page")
                return True
            else:
                logger.info("no_next_page_available")
                return False
                
        except Exception as e:
            logger.error("next_page_navigation_failed", error=str(e))
            return False
    
    @staticmethod
    def wait_for_page_load(sb, timeout: int = 30) -> bool:
        """
        Wait for the Idealo page to fully load.
        
        Args:
            sb: SeleniumBase driver instance
            timeout: Timeout in seconds
            
        Returns:
            True if page loaded successfully
        """
        try:
            # wait for product container to be visible (using correct selector)
            sb.wait_for_element_present('div[class*="sr-resultList"]', timeout=timeout)
            
            # additional wait for dynamic content
            time.sleep(2)
            
            logger.info("page_loaded_successfully")
            return True
            
        except Exception as e:
            logger.error("page_load_timeout", error=str(e), timeout=timeout)
            return False
    
    @staticmethod
    def scroll_to_load_products(sb) -> None:
        """
        Scroll down the page to trigger lazy loading of products.
        
        Args:
            sb: SeleniumBase driver instance
        """
        logger.debug("scrolling_to_load_products")
        
        # scroll slowly to the bottom to load all products (following working code pattern)
        time.sleep(2)
        sb.slow_scroll_to('a[aria-label="Nächste Seite"]')
        time.sleep(2)
        
        logger.debug("scrolling_completed")
    
    @staticmethod
    def get_current_page_number(sb) -> Optional[int]:
        """
        Get the current page number from pagination.
        
        Args:
            sb: SeleniumBase driver instance
            
        Returns:
            Current page number or None if not found
        """
        try:
            current_page_elem = sb.find_element('span.pagination-current')
            if current_page_elem:
                return int(current_page_elem.text.strip())
        except Exception as e:
            logger.debug("current_page_detection_failed", error=str(e))
        
        return None
    
    @staticmethod
    def save_page_screenshot(sb, page_num: int, suffix: str = "") -> None:
        """
        Save a screenshot of the current page for debugging.
        
        Args:
            sb: SeleniumBase driver instance
            page_num: Current page number
            suffix: Optional suffix for the filename
        """
        try:
            screenshot_dir = IdealoScraperUtils.ensure_screenshot_dir()
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"page_{page_num}_{timestamp}"
            if suffix:
                filename += f"_{suffix}"
            screenshot_path = str(screenshot_dir / f"{filename}.png")
            
            sb.save_screenshot(screenshot_path)
            logger.debug("screenshot_saved", path=screenshot_path, page=page_num)
            
        except Exception as e:
            logger.warning("screenshot_save_failed", error=str(e))