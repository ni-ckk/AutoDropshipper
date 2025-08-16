"""
Handle eBay-specific elements like cookie consent and search parameters.
"""

import time
from typing import Optional
from urllib.parse import urlencode

from seleniumbase import SB

from src.core.exceptions.scraping_errors import CookieConsentError, PageLoadError
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class EbayScraperUtils:
    """Handles eBay-specific browser interactions and search logic."""
    
    BASE_URL = "https://www.ebay.de/sch/i.html"
    
    @staticmethod
    def handle_cookie_consent(sb) -> bool:
        """
        Handle eBay cookie consent banner using original logic.
        
        Args:
            sb: SeleniumBase driver instance
            
        Returns:
            True if cookie consent was handled successfully
        """
        logger.info("handling_ebay_cookie_consent")
        
        try:
            sb.click('button#gdpr-banner-accept', timeout=15)
            logger.info("ebay_cookie_consent_accepted")
            return True
            
        except Exception:
            logger.info("ebay_cookie_consent_not_found_or_already_accepted")
            return True  # not finding the button is often normal
    
    @staticmethod
    def build_search_url(
        search_term: str,
        min_price: Optional[int] = None
    ) -> str:
        """
        Build eBay search URL with parameters using original logic.
        
        Args:
            search_term: Product search term
            min_price: Minimum price filter
            
        Returns:
            Complete eBay search URL
        """
        # use exact parameters from original code
        params = {
            '_nkw': search_term, 
            '_from': 'R40', 
            '_sacat': '0', 
            'LH_PrefLoc': '6', 
            'LH_BIN': '1', 
            '_sop': '15'
        }
        
        if min_price:
            params['_udlo'] = str(min_price)
        
        url = f"{EbayScraperUtils.BASE_URL}?{urlencode(params)}"
        logger.debug("ebay_search_url_built", url=url)
        return url
    
    @staticmethod
    def load_search_page(sb, search_url: str) -> bool:
        """
        Load eBay search page using original timing.
        
        Args:
            sb: SeleniumBase driver instance
            search_url: Complete search URL
            
        Returns:
            True if page loaded successfully
            
        Raises:
            PageLoadError: If page fails to load
        """
        logger.info("loading_ebay_search_page", url=search_url)
        
        try:
            sb.open(search_url)
            time.sleep(2)  # original timing
            
            logger.info("ebay_search_page_loaded")
            return True
            
        except Exception as e:
            logger.error("ebay_page_load_failed", error=str(e))
            raise PageLoadError(search_url, str(e))
    
    @staticmethod
    def check_result_divider(soup) -> tuple[int, int]:
        """
        Check for result divider and count items using original logic.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Tuple of (divider_index, item_count)
        """
        from bs4 import BeautifulSoup
        
        list_items = soup.select('ul.srp-results > li')
        divider_index = -1
        item_count = 0
        
        for item in list_items:
            class_list = item.get('class')
            if (class_list and 
                'srp-river-answer--REWRITE_START' in class_list and 
                "Ergebnisse für weniger Suchbegriffe" in item.get_text()):
                divider_index = item_count
                break
            if isinstance(class_list, list) and 's-item' in class_list:
                item_count += 1
        
        logger.debug("result_analysis", divider_index=divider_index, item_count=item_count)
        return divider_index, item_count