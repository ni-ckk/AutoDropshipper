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
        logger.info(
            "starting_ebay_search", 
            query=search_query, 
            max_results=max_results,
            max_bestmatch=self.config.MAX_BESTMATCH_ITEMS,
            max_leastmatch=self.config.MAX_LEASTMATCH_ITEMS,
            min_price=self.config.EBAY_MIN_PRICE
        )
        print(f"--- Starting eBay scrape for '{search_query}' ---")
        
        with SB(uc=True, headless=self.config.IS_HEADLESS_EBAY) as sb:
            is_filtered_by_min_price = False
            
            for attempt in range(2):  # max 2 attempts
                try:
                    logger.info(
                        "search_attempt_started",
                        attempt=attempt+1,
                        is_filtered=is_filtered_by_min_price
                    )
                    
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
                    logger.debug("page_loaded", current_url=sb.get_current_url())
                    time.sleep(2)
                    
                    # handle cookie consent on first attempt
                    if attempt == 0:
                        logger.debug("handling_cookie_consent")
                        self.utils.handle_cookie_consent(sb)
                        logger.debug("cookie_consent_handled")
                    
                    time.sleep(1)
                    
                    # analyze search results
                    logger.info("analyzing_search_results")
                    has_no_best_matches, divider_index, item_count = self._analyze_search_results(sb)
                    best_match_count = divider_index if divider_index != -1 else item_count
                    
                    logger.info(
                        "search_results_summary",
                        has_no_best_matches=has_no_best_matches,
                        divider_index=divider_index,
                        total_items=item_count,
                        best_match_count=best_match_count,
                        least_match_count=item_count - best_match_count if divider_index != -1 else 0
                    )
                    
                    # branch 1: no best matches found
                    if has_no_best_matches:
                        logger.info("branch_no_best_matches_selected")
                        should_retry, listings = self._process_no_best_matches(
                            sb, is_filtered_by_min_price
                        )
                        if should_retry:
                            logger.info("retrying_with_filter", reason="no_best_matches")
                            is_filtered_by_min_price = True
                            continue
                        logger.info(
                            "search_completed", 
                            branch="no_best_matches",
                            listings_count=len(listings)
                        )
                        return listings
                    
                    # branch 2: too many best matches
                    elif best_match_count >= self.config.MAX_BESTMATCH_ITEMS:
                        logger.info(
                            "branch_many_best_matches_selected",
                            best_match_count=best_match_count,
                            threshold=self.config.MAX_BESTMATCH_ITEMS
                        )
                        should_retry, listings = self._process_many_best_matches(
                            sb, best_match_count, is_filtered_by_min_price
                        )
                        if should_retry:
                            logger.info("retrying_with_filter", reason="too_many_best_matches")
                            is_filtered_by_min_price = True
                            continue
                        logger.info(
                            "search_completed",
                            branch="many_best_matches", 
                            listings_count=len(listings)
                        )
                        return listings
                    
                    # branch 3: mixed matches (fewer best matches than limit)
                    else:
                        logger.info(
                            "branch_mixed_matches_selected",
                            best_match_count=best_match_count,
                            threshold=self.config.MAX_BESTMATCH_ITEMS
                        )
                        listings = self._process_mixed_matches(sb, divider_index)
                        logger.info(
                            "search_completed",
                            branch="mixed_matches",
                            listings_count=len(listings)
                        )
                        return listings
                    
                except Exception as e:
                    logger.error(
                        "search_attempt_failed",
                        attempt=attempt+1,
                        error=str(e),
                        error_type=type(e).__name__,
                        is_last_attempt=(attempt == 1)
                    )
                    if attempt == 1:  # last attempt
                        logger.error("ebay_search_failed", error=str(e))
                        raise ScrapingError("eBay search failed", str(e))
                    else:
                        logger.warning("ebay_search_attempt_failed", attempt=attempt+1, error=str(e))
                        continue
            
            # should not reach here
            logger.error("unexpected_search_flow_end")
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
            soup = sb.get_beautiful_soup()
            
            # get all list items from search results
            list_items = soup.select('ul.srp-results > li')
            
            # filter to only get items with s-card class (actual product listings)
            product_elements = []
            for item in list_items:
                class_list = item.get('class')
                if isinstance(class_list, list) and 's-card' in class_list:
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
        
        # check if no best matches found
        no_match_element = soup.select_one("div.srp-save-null-search__title")
        has_no_best_matches = bool(no_match_element)
        
        if has_no_best_matches:
            logger.info(
                "no_best_matches_detected",
                element_text=no_match_element.get_text(strip=True) if no_match_element else None
            )
        
        # get all list items and find divider
        list_items = soup.select('ul.srp-results > li')
        logger.debug("total_list_items_found", count=len(list_items))
        
        divider_index = -1
        item_count = 0
        
        for idx, item in enumerate(list_items):
            class_list = item.get('class')
            # check for divider element
            if class_list and 'srp-river-answer--REWRITE_START' in class_list:
                item_text = item.get_text()
                if "Ergebnisse für weniger Suchbegriffe" in item_text:
                    divider_index = item_count
                    logger.info(
                        "divider_found",
                        at_position=idx,
                        after_items=item_count,
                        divider_text=item_text[:100]  # first 100 chars
                    )
                    break
            # count actual product items - updated to check for s-card
            if isinstance(class_list, list) and 's-card' in class_list:
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
        logger.info(
            "no_best_matches_branch",
            is_filtered=is_filtered_by_min_price
        )
        
        if not is_filtered_by_min_price:
            print("--- Decision: Re-searching with min price filter. ---")
            logger.info(
                "retrying_with_min_price_filter",
                min_price=self.config.EBAY_MIN_PRICE,
                reason="no_best_matches_without_filter"
            )
            return True, []  # retry with filter
        else:
            print("--- Decision: Already filtered. Scraping available items. ---")
            logger.info(
                "already_filtered_scraping_least_matches",
                max_items_to_scrape=self.config.MAX_LEASTMATCH_ITEMS
            )
            
            # parse up to MAX_LEASTMATCH_ITEMS
            elements = self._get_search_result_elements(sb)
            logger.debug(
                "search_elements_retrieved",
                total_elements=len(elements),
                will_parse=min(len(elements), self.config.MAX_LEASTMATCH_ITEMS)
            )
            
            listings = self._parse_elements(
                elements[:self.config.MAX_LEASTMATCH_ITEMS],
                is_best_match=False
            )
            
            logger.info(
                "no_best_matches_completed",
                elements_found=len(elements),
                listings_parsed=len(listings),
                max_allowed=self.config.MAX_LEASTMATCH_ITEMS
            )
            
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
            limit=self.config.MAX_BESTMATCH_ITEMS,
            is_filtered=is_filtered_by_min_price
        )
        
        if not is_filtered_by_min_price:
            print("--- Decision: Re-searching with min price filter. ---")
            logger.info(
                "retrying_with_min_price_filter",
                min_price=self.config.EBAY_MIN_PRICE,
                reason="too_many_best_matches_without_filter",
                current_count=best_match_count
            )
            return True, []  # retry with filter
        else:
            print("--- Decision: Already filtered. Scraping best matches only. ---")
            logger.info(
                "already_filtered_taking_best_matches_only",
                will_take=self.config.MAX_BESTMATCH_ITEMS,
                available=best_match_count
            )
            
            # parse only MAX_BESTMATCH_ITEMS
            elements = self._get_search_result_elements(sb)
            logger.debug(
                "search_elements_retrieved",
                total_elements=len(elements),
                will_parse=min(len(elements), self.config.MAX_BESTMATCH_ITEMS)
            )
            
            listings = self._parse_elements(
                elements[:self.config.MAX_BESTMATCH_ITEMS],
                is_best_match=True
            )
            
            logger.info(
                "many_best_matches_completed",
                elements_found=len(elements),
                listings_parsed=len(listings),
                max_allowed=self.config.MAX_BESTMATCH_ITEMS,
                all_best_matches=True
            )
            
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
            taking_least=self.config.MAX_LEASTMATCH_ITEMS,
            divider_index=divider_index
        )
        
        elements = self._get_search_result_elements(sb)
        logger.debug(
            "search_elements_for_mixed",
            total_elements=len(elements),
            divider_at=divider_index
        )
        
        all_listings = []
        best_match_parsed = 0
        least_match_parsed = 0
        
        # parse all elements and determine match type for each
        for i, element in enumerate(elements):
            # determine if this is a best match
            is_best_match = (divider_index == -1) or (i < divider_index)
            
            try:
                listing = self.parser.parse_search_result_item(element, is_best_match)
                if listing:
                    all_listings.append(listing)
                    if is_best_match:
                        best_match_parsed += 1
                    else:
                        least_match_parsed += 1
                    
                    # log first few items for debugging
                    if len(all_listings) <= 3:
                        logger.debug(
                            "listing_parsed",
                            index=i,
                            is_best_match=is_best_match,
                            title=listing.title[:50] if listing.title else None
                        )
            except Exception as e:
                logger.warning(
                    "listing_parse_failed",
                    index=i,
                    error=str(e),
                    is_best_match=is_best_match
                )
        
        # split into best and less relevant
        if divider_index != -1:
            best_listings = all_listings[:divider_index]
            other_listings = all_listings[divider_index:divider_index + self.config.MAX_LEASTMATCH_ITEMS]
            final_listings = best_listings + other_listings
            
            logger.info(
                "mixed_matches_split",
                best_listings_count=len(best_listings),
                other_listings_count=len(other_listings),
                final_count=len(final_listings)
            )
        else:
            final_listings = all_listings
            logger.info(
                "no_divider_all_best_matches",
                total_listings=len(final_listings)
            )
        
        logger.info(
            "mixed_matches_completed",
            listings_found=len(final_listings),
            best_match_parsed=best_match_parsed,
            least_match_parsed=least_match_parsed,
            divider_was_present=divider_index != -1
        )
        
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