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
from .ebay_selectors import selector_manager

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
        self.selector_manager = selector_manager
        
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
        
        Flow:
        - Single search with filters applied upfront (min price, sorted by price)
        - If best matches exist → take MAX_BESTMATCH_ITEMS
        - If no best matches → take MAX_LEASTMATCH_ITEMS
        
        Args:
            search_query: Product search query
            max_results: Maximum number of results (ignored, uses config values)
            
        Returns:
            List of EbayListing objects
        """
        logger.info(
            "starting_ebay_search", 
            query=search_query,
            max_bestmatch=self.config.MAX_BESTMATCH_ITEMS,
            max_leastmatch=self.config.MAX_LEASTMATCH_ITEMS,
            min_price=self.config.EBAY_MIN_PRICE
        )
        print(f"--- Starting eBay scrape for '{search_query}' ---")
        
        with SB(uc=True, headless=self.config.IS_HEADLESS_EBAY) as sb:
            try:
                # build and navigate to search URL with all filters
                search_url = self._build_search_url(search_query)
                print(f"\n--- Opening URL: {search_url} ---")
                logger.debug("navigating_to_search", url=search_url)
                
                sb.open(search_url)
                logger.debug("page_loaded", current_url=sb.get_current_url())
                time.sleep(2)
                
                # handle cookie consent
                logger.debug("handling_cookie_consent")
                self.utils.handle_cookie_consent(sb)
                logger.debug("cookie_consent_handled")
                time.sleep(1)
                
                # analyze search results
                logger.info("analyzing_search_results")
                has_no_best_matches, divider_index, item_count = self._analyze_search_results(sb)
                
                # two-branch logic
                if has_no_best_matches or divider_index == -1:
                    # no best matches found - take least relevant items
                    logger.info(
                        "no_best_matches_branch",
                        item_count=item_count,
                        will_take=min(item_count, self.config.MAX_LEASTMATCH_ITEMS)
                    )
                    print(f"--- No best matches found. Taking up to {self.config.MAX_LEASTMATCH_ITEMS} items ---")
                    
                    elements = self._get_search_result_elements(sb)
                    listings = self._parse_elements(
                        elements[:self.config.MAX_LEASTMATCH_ITEMS],
                        is_best_match=False
                    )
                    
                    logger.info(
                        "search_completed",
                        branch="no_best_matches",
                        listings_count=len(listings)
                    )
                else:
                    # best matches exist - take best match items
                    best_match_count = divider_index if divider_index > 0 else item_count
                    logger.info(
                        "best_matches_branch",
                        best_match_count=best_match_count,
                        will_take=min(best_match_count, self.config.MAX_BESTMATCH_ITEMS)
                    )
                    print(f"--- Best matches found. Taking up to {self.config.MAX_BESTMATCH_ITEMS} items ---")
                    
                    elements = self._get_search_result_elements(sb)
                    listings = self._parse_elements(
                        elements[:self.config.MAX_BESTMATCH_ITEMS],
                        is_best_match=True
                    )
                    
                    logger.info(
                        "search_completed",
                        branch="best_matches",
                        listings_count=len(listings)
                    )
                
                return listings
                
            except Exception as e:
                logger.error(
                    "ebay_search_failed",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise ScrapingError("eBay search failed", str(e))
    
    def _build_search_url(self, query: str) -> str:
        """
        Build eBay search URL from query with all filters applied.
        
        Args:
            query: Search query string
            
        Returns:
            Complete eBay search URL with filters
        """
        from urllib.parse import urlencode
        
        params = {
            "_nkw": query,
            "_from": "R40",
            "_sacat": "0",
            "LH_PrefLoc": "6",  # Germany
            "LH_BIN": "1",      # Buy It Now only
            "_sop": "15",       # Sort by price + shipping: lowest first
            "_udlo": str(self.config.EBAY_MIN_PRICE)  # always apply min price filter
        }
        
        return f"https://www.ebay.de/sch/i.html?{urlencode(params)}"
    
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
            soup = sb.get_beautiful_soup()
            
            # get all list items from search results
            container_selector = self.selector_manager.get_all_patterns('results_container')[0]
            list_items = soup.select(container_selector)
            
            # filter to only get items with product class (s-card or s-item)
            product_elements = []
            for item in list_items:
                if self.selector_manager.try_class_match(item, 'item_class'):
                    product_elements.append(item)
            
            return product_elements
            
        except Exception as e:
            logger.error("failed_to_get_search_elements", error=str(e))
            raise ScrapingError("Failed to get eBay search elements", str(e))
    
    def _analyze_search_results(self, sb) -> tuple[bool, int, int]:
        """
        Analyze search results to determine match types and counts.
        
        Args:
            sb: SeleniumBase driver instance
            
        Returns:
            Tuple of (has_no_best_matches, divider_index, item_count)
        """
        logger.debug("starting_result_analysis")
        
        # get page soup for analysis
        soup = sb.get_beautiful_soup()
        
        # check if no best matches found using selector manager
        no_match_element = self.selector_manager.try_selectors(
            soup, 'no_results', required=False
        )
        has_no_best_matches = bool(no_match_element)
        
        if has_no_best_matches:
            logger.info(
                "no_best_matches_detected",
                element_text=no_match_element.get_text(strip=True) if no_match_element else None
            )
        
        # get all list items and find divider
        container_selector = self.selector_manager.get_all_patterns('results_container')[0]
        list_items = soup.select(container_selector)
        logger.debug("total_list_items_found", count=len(list_items))
        
        divider_index = -1
        item_count = 0
        
        # get divider patterns
        divider_classes = self.selector_manager.get_all_patterns('divider_class')
        divider_texts = self.selector_manager.get_all_patterns('divider_text')
        
        for idx, item in enumerate(list_items):
            class_list = item.get('class')
            # check for divider element
            if class_list:
                for divider_class in divider_classes:
                    if divider_class in class_list:
                        item_text = item.get_text()
                        # check if it contains the expected text
                        for divider_text in divider_texts:
                            if divider_text in item_text:
                                divider_index = item_count
                                logger.info(
                                    "divider_found",
                                    at_position=idx,
                                    after_items=item_count,
                                    divider_text=item_text[:100]
                                )
                                break
                        if divider_index != -1:
                            break
            
            # count actual product items using selector manager
            if self.selector_manager.try_class_match(item, 'item_class'):
                item_count += 1
                if item_count <= 3:  # log first few items for debugging
                    logger.debug(
                        "product_item_found",
                        index=idx,
                        item_number=item_count,
                        item_id=item.get('id')
                    )
        
        logger.info(
            "search_results_analyzed",
            has_no_best=has_no_best_matches,
            divider_index=divider_index,
            item_count=item_count,
            best_match_count=divider_index if divider_index != -1 else item_count,
            least_match_count=item_count - divider_index if divider_index != -1 else 0
        )
        
        return has_no_best_matches, divider_index, item_count
    
    def _parse_elements(
        self, elements: list, is_best_match: bool
    ) -> List[EbayListing]:
        """
        Parse a list of elements into eBay listings.
        
        Args:
            elements: List of selenium elements to parse
            is_best_match: Whether these are best match items
            
        Returns:
            List of parsed eBay listings
        """
        listings = []
        total = len(elements)
        
        print(f"Parsing {total} eBay listings...")
        
        for i, element in enumerate(elements):
            if i % 5 == 0 or i == total - 1:
                print(f"Parsing listings: {i+1}/{total}...")
            
            try:
                listing = self.parser.parse_search_result_item(element, is_best_match)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning("listing_parse_failed", index=i, error=str(e))
        
        return listings
    
    def close(self):
        """Clean up and close the scraper."""
        # SB context manager handles cleanup automatically
        logger.info("ebay_scraper_closed")