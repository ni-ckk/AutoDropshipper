"""
Main eBay scraping orchestration and page navigation.
"""

import time
from typing import List

from seleniumbase import SB

from src.core.exceptions.scraping_errors import PageLoadError, ScrapingError
from src.core.models.ebay_listing import EbayListing
from src.shared.config.ebay_settings import get_ebay_config
from src.shared.logging.log_setup import get_logger, log_scraping_progress

from .ebay_parser import EbayParser
from .ebay_scraper_utils import EbayScraperUtils

logger = get_logger(__name__)


class EbayScraper:
    """
    Main eBay scraper for product search and extraction.
    
    Handles browser automation, page navigation, and coordinates
    with parser and utility modules for data extraction.
    """
    
    def __init__(self):
        """Initialize eBay scraper with configuration."""
        self.config = get_ebay_config()
        self.driver = None
        self.parser = EbayParser()
        self.utils = EbayScraperUtils()
        
    def __enter__(self):
        """Context manager entry."""
        self._setup_driver()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()
        
    def _setup_driver(self):
        """Set up SeleniumBase driver with eBay-specific configuration."""
        try:
            # SB context manager will be used in search_products method
            logger.info("ebay_scraper_initialized")
            
        except Exception as e:
            logger.error("ebay_driver_setup_failed", error=str(e))
            raise ScrapingError("Failed to initialize eBay scraper", str(e))
    
    def search_products(
        self,
        search_query: str,
        max_results: int = 20
    ) -> List[EbayListing]:
        """
        Search for products on eBay and extract listings.
        
        Args:
            search_query: Product search query
            max_results: Maximum number of results to extract
            
        Returns:
            List of EbayListing objects
        """
        logger.info("starting_ebay_search", query=search_query, max_results=max_results)
        
        with SB(uc=True, headless=self.config.HEADLESS_MODE) as sb:
            try:
                search_url = self._build_search_url(search_query)
                logger.debug("navigating_to_search", url=search_url)
                
                sb.get(search_url)
                self._wait_for_search_results(sb)
                
                # extract search result elements
                search_elements = self._get_search_result_elements(sb)
                logger.info("found_search_elements", count=len(search_elements))
                
                # find divider between best matches and less relevant
                divider_index = self.parser.find_divider_index(search_elements)
                
                # parse listings with simple progress tracking
                listings = []
                total_elements = len(search_elements[:max_results])
                print(f"Parsing {total_elements} eBay listings...")
                
                for i, element in enumerate(search_elements[:max_results]):
                    if i % 5 == 0 or i == total_elements - 1:  # Show progress every 5 items
                        print(f"Parsing listings: {i+1}/{total_elements}...")
                    
                    try:
                        # determine if this listing is in best match section
                        is_best_match = (divider_index == -1) or (i < divider_index)
                        listing = self.parser.parse_search_result_item(element, is_best_match)
                        if listing:
                            listings.append(listing)
                            
                    except Exception as e:
                        logger.warning("listing_parse_failed", index=i, error=str(e))
                        continue
                
                logger.info("ebay_search_completed", listings_found=len(listings))
                return listings
                
            except Exception as e:
                logger.error("ebay_search_failed", error=str(e))
                raise ScrapingError("eBay search failed", str(e))
    
    def _build_search_url(self, query: str) -> str:
        """
        Build eBay search URL from query.
        
        Args:
            query: Search query string
            
        Returns:
            Complete eBay search URL
        """
        # encode search query for URL
        encoded_query = query.replace(" ", "+")
        
        base_url = (
            f"https://www.ebay.de/sch/i.html"
            f"?_from=R40"
            f"&_nkw={encoded_query}"
            f"&_sacat=0"
            f"&_sop=15"  # sort by price + shipping
        )
        
        return base_url
    
    def _wait_for_search_results(self, sb):
        """Wait for search results to load."""
        try:
            # wait for results container
            sb.wait_for_element("ul.srp-results", timeout=10)
            
            # additional wait for dynamic content
            time.sleep(2)
            
        except Exception as e:
            logger.error("search_results_not_loaded", error=str(e))
            raise PageLoadError("eBay search results failed to load", str(e))
    
    def _get_search_result_elements(self, sb):
        """Get search result elements from the page."""
        try:
            # get all search result items
            elements = sb.find_elements("css selector", "ul.srp-results > li")
            
            # filter out non-product elements (ads, separators, etc.)
            product_elements = []
            for element in elements:
                data_view = element.get_attribute("data-view")
                if data_view and "item" in data_view.lower():
                    product_elements.append(element)
                    
            return product_elements
            
        except Exception as e:
            logger.error("failed_to_get_search_elements", error=str(e))
            raise ScrapingError("Failed to get eBay search elements", str(e))
    
    def close(self):
        """Clean up and close the scraper."""
        # SB context manager handles cleanup automatically
        logger.info("ebay_scraper_closed")