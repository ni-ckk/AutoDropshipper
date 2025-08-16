"""
eBay listing storage, updates, and comparison queries.
"""

from typing import Any, Dict, List

from src.shared.logging.log_setup import get_logger

from .base_repository import BaseRepository

logger = get_logger(__name__)


class EbayListingRepository(BaseRepository):
    """Repository for eBay listing data operations."""
    
    def delete_old_listings(self, product_id: int) -> None:
        """
        Remove old eBay listings for a product.
        
        Args:
            product_id: Product ID to clear listings for
        """
        query = "DELETE FROM deal_board_ebaylisting WHERE product_id = %s;"
        self._execute_query(query, (product_id,))
        logger.info("old_ebay_listings_deleted", product_id=product_id)
    
    def insert_listing(self, product_id: int, listing_data: Dict[str, Any]) -> None:
        """
        Insert new eBay listing for a product.
        
        Args:
            product_id: Product ID to associate listing with
            listing_data: Dictionary with eBay listing data
        """
        query = """
            INSERT INTO deal_board_ebaylisting
            (product_id, title, subtitle, price, source_url, image_url, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW());
        """
        params = (
            product_id,
            listing_data["title"],
            listing_data.get("subtitle"),
            listing_data["price"],
            listing_data["source_url"],
            listing_data.get("image_url"),
        )
        
        self._execute_query(query, params)
        logger.debug("ebay_listing_inserted", title=listing_data["title"][:40])
    
    def save(self, listing) -> None:
        """
        Save an eBay listing to database.
        
        Args:
            listing: EbayListing object to save
        """
        query = """
            INSERT INTO deal_board_ebaylisting
            (title, subtitle, price, source_url, image_url, condition, shipping_cost, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (source_url) DO UPDATE SET
                price = EXCLUDED.price,
                shipping_cost = EXCLUDED.shipping_cost,
                scraped_at = NOW();
        """
        params = (
            listing.title,
            listing.subtitle,
            listing.price,
            str(listing.source_url),
            str(listing.image_url) if listing.image_url else None,
            listing.condition,
            listing.shipping_cost if hasattr(listing, 'shipping_cost') else 0
        )
        
        self._execute_query(query, params)
        logger.debug("ebay_listing_saved", title=listing.title[:40])
    
    def update_listings_for_product(self, product_id: int, ebay_listings: List[Dict[str, Any]]) -> None:
        """
        Replace all eBay listings for a product (original logic preserved).
        
        Args:
            product_id: Product ID to update
            ebay_listings: List of eBay listing dictionaries
        """
        try:
            # remove old listings first (original logic)
            self.delete_old_listings(product_id)
            
            # insert new listings
            for listing in ebay_listings:
                self.insert_listing(product_id, listing)
            
            logger.info(
                "ebay_listings_updated",
                product_id=product_id,
                listings_count=len(ebay_listings)
            )
            
        except Exception as e:
            logger.error("ebay_listing_update_error", error=str(e), exc_info=True)
            raise