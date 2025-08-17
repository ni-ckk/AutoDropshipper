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
        
        Implements the working flow diagram logic:
        - First attempt without min price filter
        - If too many/no best matches, retry with min price filter
        - Select items based on MAX_BESTMATCH_ITEMS and MAX_LEASTMATCH_ITEMS
        
        Args:
            search_query: Product search query
            max_results: Maximum number of results (ignored, uses config values)
            
        Returns:
            List of EbayListing objects
        """
        logger.info("starting_ebay_search", query=search_query, max_results=max_results)
        print(f"--- Starting eBay scrape for '{search_query}' ---")
        
        with SB(uc=True, headless=self.config.IS_HEADLESS_EBAY) as sb:
            is_filtered_by_min_price = False
            
            for attempt in range(2):  # max 2 attempts
                try:
                    # build and navigate to search URL
                    search_url = self._build_search_url(
                        search_query, 
                        with_min_price=is_filtered_by_min_price
                    )
                    print(f"\n--- Opening URL (Attempt #{attempt+1}): {search_url} ---")
                    logger.debug(
                        "navigating_to_search", 
                        url=search_url, 
                        attempt=attempt+1,
                        filtered=is_filtered_by_min_price
                    )
                    
                    sb.open(search_url)
                    time.sleep(2)
                    
                    # handle cookie consent on first attempt
                    if attempt == 0:
                        self.utils.handle_cookie_consent(sb)
                    
                    time.sleep(1)
                    
                    # analyze search results
                    has_no_best_matches, divider_index, item_count = self._analyze_search_results(sb)
                    best_match_count = divider_index if divider_index != -1 else item_count
                    
                    # branch 1: no best matches found
                    if has_no_best_matches:
                        should_retry, listings = self._process_no_best_matches(
                            sb, is_filtered_by_min_price
                        )
                        if should_retry:
                            is_filtered_by_min_price = True
                            continue
                        return listings
                    
                    # branch 2: too many best matches
                    elif best_match_count >= self.config.MAX_BESTMATCH_ITEMS:
                        should_retry, listings = self._process_many_best_matches(
                            sb, best_match_count, is_filtered_by_min_price
                        )
                        if should_retry:
                            is_filtered_by_min_price = True
                            continue
                        return listings
                    
                    # branch 3: mixed matches (fewer best matches than limit)
                    else:
                        listings = self._process_mixed_matches(sb, divider_index)
                        return listings
                    
                except Exception as e:
                    if attempt == 1:  # last attempt
                        logger.error("ebay_search_failed", error=str(e))
                        raise ScrapingError("eBay search failed", str(e))
                    else:
                        logger.warning("ebay_search_attempt_failed", attempt=attempt+1, error=str(e))
                        continue
            
            # should not reach here
            return []
    
    def _build_search_url(self, query: str, with_min_price: bool = False) -> str:
        """
        Build eBay search URL from query.
        
        Args:
            query: Search query string
            with_min_price: Whether to include minimum price filter
            
        Returns:
            Complete eBay search URL
        """
        from urllib.parse import urlencode
        
        params = {
            "_nkw": query,
            "_from": "R40",
            "_sacat": "0",
            "LH_PrefLoc": "6",  # Germany
            "LH_BIN": "1",      # Buy It Now only
            "_sop": "15"        # Sort by price + shipping: lowest first
        }
        
        if with_min_price:
            params["_udlo"] = str(self.config.EBAY_MIN_PRICE)
        
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
    
    def _analyze_search_results(self, sb) -> tuple[bool, int, int]:
        """
        Analyze search results to determine match types and counts.
        
        Args:
            sb: SeleniumBase driver instance
            
        Returns:
            Tuple of (has_no_best_matches, divider_index, item_count)
        """
        # get page soup for analysis
        soup = sb.get_beautiful_soup()
        
        # check if no best matches found
        has_no_best_matches = bool(soup.select_one("div.srp-save-null-search__title"))
        
        # get all list items and find divider
        list_items = soup.select('ul.srp-results > li')
        divider_index = -1
        item_count = 0
        
        for item in list_items:
            class_list = item.get('class')
            # check for divider element
            if class_list and 'srp-river-answer--REWRITE_START' in class_list:
                if "Ergebnisse für weniger Suchbegriffe" in item.get_text():
                    divider_index = item_count
                    break
            # count actual product items
            if isinstance(class_list, list) and 's-item' in class_list:
                item_count += 1
        
        logger.debug(
            "search_results_analyzed",
            has_no_best=has_no_best_matches,
            divider_index=divider_index,
            item_count=item_count
        )
        
        return has_no_best_matches, divider_index, item_count
    
    def _process_no_best_matches(
        self, sb, is_filtered_by_min_price: bool
    ) -> tuple[bool, List[EbayListing]]:
        """
        Process case when no best matches are found.
        
        Args:
            sb: SeleniumBase driver instance
            is_filtered_by_min_price: Whether min price filter is active
            
        Returns:
            Tuple of (should_retry, listings)
        """
        print("--- Branch: No best matches found. ---")
        logger.info("no_best_matches_branch")
        
        if not is_filtered_by_min_price:
            print("--- Decision: Re-searching with min price filter. ---")
            logger.info("retrying_with_min_price_filter")
            return True, []  # retry with filter
        else:
            print("--- Decision: Already filtered. Scraping available items. ---")
            logger.info("already_filtered_scraping_least_matches")
            
            # parse up to MAX_LEASTMATCH_ITEMS
            elements = self._get_search_result_elements(sb)
            listings = self._parse_elements(
                elements[:self.config.MAX_LEASTMATCH_ITEMS],
                is_best_match=False
            )
            
            logger.info("ebay_search_completed", listings_found=len(listings))
            return False, listings
    
    def _process_many_best_matches(
        self, sb, best_match_count: int, is_filtered_by_min_price: bool
    ) -> tuple[bool, List[EbayListing]]:
        """
        Process case when there are too many best matches.
        
        Args:
            sb: SeleniumBase driver instance
            best_match_count: Number of best matches found
            is_filtered_by_min_price: Whether min price filter is active
            
        Returns:
            Tuple of (should_retry, listings)
        """
        print(f"--- Branch: Found {best_match_count} best matches (>= limit of {self.config.MAX_BESTMATCH_ITEMS}). ---")
        logger.info(
            "sufficient_best_matches_branch",
            count=best_match_count,
            limit=self.config.MAX_BESTMATCH_ITEMS
        )
        
        if not is_filtered_by_min_price:
            print("--- Decision: Re-searching with min price filter. ---")
            logger.info("retrying_with_min_price_filter")
            return True, []  # retry with filter
        else:
            print("--- Decision: Already filtered. Scraping best matches only. ---")
            logger.info("already_filtered_taking_best_matches_only")
            
            # parse only MAX_BESTMATCH_ITEMS
            elements = self._get_search_result_elements(sb)
            listings = self._parse_elements(
                elements[:self.config.MAX_BESTMATCH_ITEMS],
                is_best_match=True
            )
            
            logger.info("ebay_search_completed", listings_found=len(listings))
            return False, listings
    
    def _process_mixed_matches(
        self, sb, divider_index: int
    ) -> List[EbayListing]:
        """
        Process case with mixed best and less relevant matches.
        
        Args:
            sb: SeleniumBase driver instance
            divider_index: Index separating best from less relevant matches
            
        Returns:
            List of parsed eBay listings
        """
        best_match_count = divider_index if divider_index != -1 else 0
        print(f"--- Branch: Found {best_match_count} best matches (< limit). Scraping all. ---")
        logger.info(
            "mixed_matches_branch",
            best_count=best_match_count,
            taking_best=best_match_count,
            taking_least=self.config.MAX_LEASTMATCH_ITEMS
        )
        
        elements = self._get_search_result_elements(sb)
        all_listings = []
        
        # parse all elements and determine match type for each
        for i, element in enumerate(elements):
            # determine if this is a best match
            is_best_match = (divider_index == -1) or (i < divider_index)
            
            try:
                listing = self.parser.parse_search_result_item(element, is_best_match)
                if listing:
                    all_listings.append(listing)
            except Exception as e:
                logger.warning("listing_parse_failed", index=i, error=str(e))
        
        # split into best and less relevant
        if divider_index != -1:
            best_listings = all_listings[:divider_index]
            other_listings = all_listings[divider_index:divider_index + self.config.MAX_LEASTMATCH_ITEMS]
            final_listings = best_listings + other_listings
        else:
            final_listings = all_listings
        
        logger.info("ebay_search_completed", listings_found=len(final_listings))
        return final_listings
    
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