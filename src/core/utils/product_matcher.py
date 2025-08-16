"""
Match Idealo products with eBay listings using title/price similarity.
"""

import re
from typing import Dict, List, Tuple

from src.core.models.ebay_listing import EbayListing
from src.core.models.idealo_product import IdealoProduct
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class ProductMatcher:
    """Handles matching products between platforms."""
    
    @staticmethod
    def clean_product_name(name: str) -> str:
        """
        Clean product name for better matching.
        
        Args:
            name: Raw product name
            
        Returns:
            Cleaned product name
        """
        # remove common prefixes/suffixes and normalize
        cleaned = re.sub(r'[^\w\s]', ' ', name.lower())
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    @staticmethod
    def categorize_listings(
        listings: List[EbayListing],
        idealo_product: IdealoProduct,
        divider_index: int = -1
    ) -> Tuple[List[EbayListing], List[EbayListing]]:
        """
        Categorize eBay listings into best matches and less relevant matches.
        
        Args:
            listings: All eBay listings
            idealo_product: Source Idealo product
            divider_index: Index where less relevant results start
            
        Returns:
            Tuple of (best_matches, less_relevant_matches)
        """
        if divider_index == -1:
            # no divider found, all are best matches
            return listings, []
        
        best_matches = listings[:divider_index]
        less_relevant = listings[divider_index:]
        
        logger.debug(
            "listings_categorized",
            total=len(listings),
            best_matches=len(best_matches),
            less_relevant=len(less_relevant)
        )
        
        return best_matches, less_relevant