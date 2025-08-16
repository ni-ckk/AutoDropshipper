"""
Parser for extracting product data from Idealo HTML/DOM elements.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional
import json

from bs4 import BeautifulSoup, Tag

from src.core.exceptions.scraping_errors import ElementNotFoundError, PriceParsingError
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class IdealoParser:
    """Handles parsing of Idealo product data from HTML."""
    
    @staticmethod
    def parse_price(price_text: str) -> Decimal:
        """
        Parse price from text string.
        
        Args:
            price_text: Raw price text
            
        Returns:
            Parsed price as Decimal
            
        Raises:
            PriceParsingError: If price cannot be parsed
        """
        try:
            price_match = re.search(r'[\d,.]+', price_text)
            if not price_match:
                raise PriceParsingError(price_text)
            
            price_cleaned = price_match.group(0).replace('.', '').replace(',', '.')
            return Decimal(price_cleaned)
            
        except (InvalidOperation, ValueError) as e:
            logger.error("price_parsing_failed", price_text=price_text, error=str(e))
            raise PriceParsingError(price_text)
    
    @staticmethod
    def parse_discount(discount_text: str) -> Optional[Decimal]:
        """
        Parse discount percentage from text.
        
        Args:
            discount_text: Raw discount text (e.g., "-25%")
            
        Returns:
            Discount as Decimal (e.g., 0.25 for 25%) or None if not found
        """
        try:
            discount_match = re.search(r'\d+', discount_text)
            if discount_match:
                # convert percentage to decimal (25% -> 0.25)
                discount_percent = int(discount_match.group(0))
                return Decimal(str(discount_percent / 100))
        except (ValueError, AttributeError):
            pass
        # default to None if discount can't be parsed
        logger.debug("discount_parse_failed", text=discount_text)
        return None
    
    @staticmethod
    def extract_product_data(card: Tag) -> Optional[Dict[str, Any]]:
        """
        Extract product data from a BeautifulSoup element.
        
        Args:
            card: BeautifulSoup Tag containing product card
            
        Returns:
            Dictionary with product data or None if parsing fails
        """
        try:
            product_data = {}
            
            # extract title using actual selector
            title_tag = card.select_one('div[class*="sr-productSummary__title"]')
            if not title_tag:
                return None
            product_data['name'] = title_tag.get_text(strip=True)
            
            # extract URL using actual method from original code
            source_url = "N/A"
            
            # method 1: direct link
            link_tag = card.select_one('a[class*="sr-resultItemTile__link"]')
            if link_tag and link_tag.get("href"):
                raw_url = str(link_tag.get("href"))
                if raw_url and not raw_url.startswith("https://"):
                    source_url = f"https://www.idealo.de{raw_url}"
                else:
                    source_url = raw_url
            
            # method 2: wishlist data (from original code)
            if "ipc/prg" in source_url or source_url == "N/A":
                wishlist_tag = card.select_one("[data-wishlist-heart]")
                if wishlist_tag:
                    wishlist_attr = wishlist_tag.get("data-wishlist-heart")
                    if wishlist_attr:
                        wishlist_data = json.loads(str(wishlist_attr))
                        product_id = wishlist_data.get("id")
                        if product_id:
                            source_url = (
                                f"https://www.idealo.de/preisvergleich/"
                                f"OffersOfProduct/{product_id}.html"
                            )
            
            # extract price using actual selector
            price_tag = card.select_one('div[class*="sr-detailedPriceInfo__price"]')
            if not price_tag:
                return None
            product_data['price'] = IdealoParser.parse_price(price_tag.get_text(strip=True))
            
            # extract image URL using actual selector
            image_tag = card.select_one('img[class*="sr-resultItemTile__image"]')
            if image_tag:
                product_data['image_url'] = image_tag.get("data-src") or image_tag.get("src")
            else:
                product_data['image_url'] = None
            
            # extract discount using actual selector
            discount_tag = card.select_one('span[class*="sr-bargainBadge__savingBadge"]')
            if discount_tag:
                product_data['discount'] = IdealoParser.parse_discount(
                    discount_tag.get_text(strip=True)
                )
            else:
                product_data['discount'] = None  # default if no discount found
            
            # skip if essential data is missing (from original logic)
            if (product_data['name'] == "N/A" or 
                source_url == "N/A" or 
                "ipc/prg" in source_url or 
                not product_data['price']):
                logger.debug(
                    "product_skipped", 
                    name=product_data['name'][:50],
                    reason="missing_essential_data"
                )
                return None
            
            product_data['source_url'] = source_url
            product_data['category'] = "Electronics"  # default category since Idealo doesn't have clear category in product cards
            product_data['is_active'] = True  # products from scraping are active by default
            
            logger.debug("product_parsed", name=product_data['name'][:50], discount=product_data['discount'])
            return product_data
            
        except Exception as e:
            logger.warning("product_parsing_failed", error=str(e))
            return None
    
    @staticmethod
    def find_products_on_page(soup: BeautifulSoup) -> list:
        """
        Find all product elements on the page using actual selector.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of product elements
        """
        # use actual selector from original code
        products = soup.select('div[class*="sr-resultList__item"]')
        
        logger.info("products_found_on_page", count=len(products))
        return products
    
    @staticmethod
    def wait_for_results_container() -> str:
        """
        Get the actual results container selector.
        
        Returns:
            Selector string for results container
        """
        return 'div[class*="sr-resultList"]'