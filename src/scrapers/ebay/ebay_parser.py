"""
Parser for extracting eBay listing data from HTML/DOM elements.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

from src.core.exceptions.scraping_errors import ElementNotFoundError, PriceParsingError
from src.core.models.ebay_listing import EbayListing
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class EbayParser:
    """Parser for eBay search results and product listings."""
    
    def __init__(self):
        """Initialize the parser with selector manager."""
        from .ebay_selectors import selector_manager
        self.selector_manager = selector_manager
    
    @staticmethod
    def parse_price(price_text: str) -> float:
        """
        Parse price text to float value.
        
        Args:
            price_text: Price string from eBay (e.g., "EUR 29,99", "$19.99")
            
        Returns:
            Float price value
        """
        try:
            # remove currency symbols and extra text
            cleaned = price_text.replace('EUR', '').replace('$', '').replace('£', '')
            cleaned = cleaned.replace('€', '').strip()
            
            # handle range prices (take first value)
            if ' to ' in cleaned or ' bis ' in cleaned:
                cleaned = cleaned.split()[0]
            
            # handle german decimal format (comma as decimal separator)
            if ',' in cleaned and '.' in cleaned:
                # both present - assume german format (1.234,56)
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned and cleaned.count(',') == 1:
                # only comma - could be german decimal
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # likely german decimal format
                    cleaned = cleaned.replace(',', '.')
                else:
                    # likely thousands separator
                    cleaned = cleaned.replace(',', '')
            else:
                # just remove any commas (thousands separator)
                cleaned = cleaned.replace(',', '')
            
            return float(cleaned)
        except (ValueError, AttributeError) as e:
            logger.warning("price_parse_failed", price_text=price_text, error=str(e))
            return 0.0
    
    def extract_listing_data(self, item_soup: Tag) -> Optional[Dict[str, Any]]:
        """
        Extract listing data from eBay search result item.
        
        Args:
            item_soup: BeautifulSoup Tag containing eBay listing
            
        Returns:
            Dictionary with listing data or None if parsing fails
        """
        try:
            listing_data = {}
            
            # extract title using selector manager
            title_tag = self.selector_manager.try_selectors(
                item_soup, 'title', required=True
            )
            if not title_tag:
                return None
            listing_data['title'] = title_tag.get_text(strip=True)
            
            # extract subtitle (optional) using selector manager
            subtitle_tag = self.selector_manager.try_selectors(
                item_soup, 'subtitle', required=False
            )
            listing_data['subtitle'] = (
                subtitle_tag.get_text(strip=True, separator=' ') 
                if subtitle_tag else None
            )
            
            # extract price using selector manager
            price_tag = self.selector_manager.try_selectors(
                item_soup, 'price', required=True
            )
            if not price_tag:
                return None
            
            price_text = price_tag.get_text(strip=True)
            listing_data['price'] = self.parse_price(price_text)
            
            # extract URL using selector manager
            url_tag = self.selector_manager.try_selectors(
                item_soup, 'url', required=True
            )
            if not url_tag or not url_tag.get('href'):
                return None
            listing_data['source_url'] = url_tag['href']
            
            # extract image URL using selector manager
            image_tag = self.selector_manager.try_selectors(
                item_soup, 'image', required=False
            )
            if image_tag:
                listing_data['image_url'] = (
                    image_tag.get('src') or image_tag.get('data-src')
                )
            else:
                listing_data['image_url'] = None
            
            logger.debug("ebay_listing_parsed", title=listing_data['title'][:50])
            return listing_data
            
        except Exception as e:
            logger.warning("ebay_listing_parse_failed", error=str(e))
            return None
    
    def find_listings_on_page(self, soup: BeautifulSoup) -> list:
        """
        Find all listing elements on eBay search results page.
        
        Args:
            soup: BeautifulSoup object of the eBay page
            
        Returns:
            List of valid listing elements
        """
        # get all list items from search results
        container_selector = self.selector_manager.get_all_patterns('results_container')[0]
        list_items = soup.select(container_selector)
        valid_listings = []
        
        for item in list_items:
            # use selector manager to check item classes
            if self.selector_manager.try_class_match(item, 'item_class'):
                valid_listings.append(item)
        
        logger.info("ebay_listings_found_on_page", count=len(valid_listings))
        return valid_listings
    
    @staticmethod
    def check_no_results(soup: BeautifulSoup) -> bool:
        """
        Check if eBay search returned no results.
        
        Args:
            soup: BeautifulSoup object of the eBay page
            
        Returns:
            True if no results found, False otherwise
        """
        from .ebay_selectors import selector_manager
        
        # check for "no results" element
        no_results_elem = selector_manager.try_selectors(
            soup, 'no_results', required=False
        )
        has_no_best_matches = bool(no_results_elem)
        
        if has_no_best_matches:
            logger.info("no_ebay_results_detected")
        
        return has_no_best_matches
    
    def find_divider_index(self, soup: BeautifulSoup) -> int:
        """
        Find the index of the divider between best and less relevant matches.
        
        Args:
            soup: BeautifulSoup object of the eBay page
            
        Returns:
            Index of divider element or -1 if not found
        """
        container_selector = self.selector_manager.get_all_patterns('results_container')[0]
        list_items = soup.select(container_selector)
        
        divider_patterns = self.selector_manager.get_all_patterns('divider_class')
        text_patterns = self.selector_manager.get_all_patterns('divider_text')
        
        item_count = 0
        for idx, item in enumerate(list_items):
            # check if this is a divider
            class_list = item.get('class')
            if class_list:
                for divider_class in divider_patterns:
                    if divider_class in class_list:
                        item_text = item.get_text()
                        # check if it contains the expected text
                        for text_pattern in text_patterns:
                            if text_pattern in item_text:
                                logger.info(
                                    "divider_found",
                                    at_index=item_count,
                                    text_preview=item_text[:100]
                                )
                                return item_count
            
            # count actual product items
            if self.selector_manager.try_class_match(item, 'item_class'):
                item_count += 1
        
        return -1
    
    def parse_search_result_item(
        self, item_soup: Tag, is_best_match: bool = True
    ) -> Optional[EbayListing]:
        """
        Parse a single search result item into EbayListing.
        
        Args:
            item_soup: BeautifulSoup Tag containing the item
            is_best_match: Whether this is a best match result
            
        Returns:
            EbayListing object or None if parsing fails
        """
        listing_data = self.extract_listing_data(item_soup)
        if not listing_data:
            return None
        
        try:
            # create EbayListing object
            listing = EbayListing(
                title=listing_data['title'],
                subtitle=listing_data.get('subtitle'),
                price=listing_data['price'],
                source_url=listing_data['source_url'],
                image_url=listing_data.get('image_url'),
                is_best_match=is_best_match
            )
            
            return listing
            
        except Exception as e:
            logger.warning(
                "ebay_listing_creation_failed",
                error=str(e),
                title=listing_data.get('title', 'Unknown')[:50]
            )
            return None