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
    """Handles parsing of eBay listing data from HTML."""
    
    @staticmethod
    def parse_price(price_text: str) -> Decimal:
        """
        Parse price from eBay price text.
        
        Args:
            price_text: Raw price text from eBay
            
        Returns:
            Parsed price as Decimal
            
        Raises:
            PriceParsingError: If price cannot be parsed
        """
        try:
            # extract numeric part from price text
            price_match = re.search(r'[\d,.]+', price_text)
            if not price_match:
                raise PriceParsingError(price_text)
            
            price_cleaned = price_match.group(0).replace('.', '').replace(',', '.')
            return Decimal(price_cleaned)
            
        except (InvalidOperation, ValueError) as e:
            logger.error("ebay_price_parsing_failed", price_text=price_text, error=str(e))
            raise PriceParsingError(price_text)
    
    @staticmethod
    def extract_listing_data(item_soup: Tag) -> Optional[Dict[str, Any]]:
        """
        Extract listing data from eBay search result item.
        
        Args:
            item_soup: BeautifulSoup Tag containing eBay listing
            
        Returns:
            Dictionary with listing data or None if parsing fails
        """
        try:
            listing_data = {}
            
            # extract title
            title_selector = 'div.s-item__title > span'
            title_tag = item_soup.select_one(title_selector)
            if not title_tag:
                return None
            listing_data['title'] = title_tag.get_text(strip=True)
            
            # extract subtitle (optional)
            subtitle_selector = 'div.s-item__subtitle'
            subtitle_tag = item_soup.select_one(subtitle_selector)
            listing_data['subtitle'] = (
                subtitle_tag.get_text(strip=True, separator=' ') 
                if subtitle_tag else None
            )
            
            # extract price
            price_selector = 'span.s-item__price'
            price_tag = item_soup.select_one(price_selector)
            if not price_tag:
                return None
            
            price_text = price_tag.get_text(strip=True)
            listing_data['price'] = EbayParser.parse_price(price_text)
            
            # extract URL
            url_selector = 'a.s-item__link'
            url_tag = item_soup.select_one(url_selector)
            if not url_tag or not url_tag.get('href'):
                return None
            listing_data['source_url'] = url_tag['href']
            
            # extract image URL (using exact original selector)
            image_selector = 'div.s-item__image img'
            image_tag = item_soup.select_one(image_selector)
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
    
    @staticmethod
    def find_listings_on_page(soup: BeautifulSoup) -> list:
        """
        Find all listing elements on eBay search results page using original logic.
        
        Args:
            soup: BeautifulSoup object of the eBay page
            
        Returns:
            List of valid listing elements
        """
        # use original selector from the working code
        list_items = soup.select('ul.srp-results > li')
        valid_listings = []
        
        for item in list_items:
            class_list = item.get('class')
            # use original logic: check if 's-item' is in class list
            if isinstance(class_list, list) and 's-item' in class_list:
                valid_listings.append(item)
        
        logger.info("ebay_listings_found_on_page", count=len(valid_listings))
        return valid_listings
    
    @staticmethod
    def check_no_results(soup: BeautifulSoup) -> bool:
        """
        Check if eBay search returned no results using original logic.
        
        Args:
            soup: BeautifulSoup object of the eBay page
            
        Returns:
            True if no results found
        """
        # use original selector from working code
        has_no_best_matches = bool(soup.select_one("div.srp-save-null-search__title"))
        
        if has_no_best_matches:
            logger.info("ebay_no_results_detected")
            return True
        
        return False
    
    @staticmethod
    def find_divider_index(search_elements: List[Tag]) -> int:
        """
        Find the index that divides best matches from less relevant results.
        
        Based on original logic from find_product_ebay.py that looks for 
        'srp-river-answer--REWRITE_START' class with text about less relevant results.
        
        Args:
            search_elements: List of search result elements
            
        Returns:
            Index of divider element, or -1 if not found
        """
        for index, element in enumerate(search_elements):
            class_list = element.get('class')
            # check for divider element using original logic
            if class_list and 'srp-river-answer--REWRITE_START' in class_list:
                # check if it contains text about less relevant results
                if "Ergebnisse für weniger Suchbegriffe" in element.get_text():
                    logger.debug("ebay_divider_found", index=index)
                    return index
        
        logger.debug("ebay_divider_not_found")
        return -1
    
    @staticmethod
    def parse_search_result_item(item_soup: Tag, is_best_match: bool = False) -> Optional[EbayListing]:
        """
        Parse a search result item into an EbayListing object.
        
        This is a wrapper around extract_listing_data that returns 
        an EbayListing model instead of a dictionary.
        
        Args:
            item_soup: BeautifulSoup Tag containing eBay listing
            is_best_match: Whether this listing is in the best match section
            
        Returns:
            EbayListing object or None if parsing fails
        """
        listing_data = EbayParser.extract_listing_data(item_soup)
        
        if not listing_data:
            return None
        
        try:
            # create EbayListing from extracted data
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
            logger.warning("ebay_listing_model_creation_failed", error=str(e))
            return None