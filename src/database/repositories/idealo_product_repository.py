"""
Idealo product-specific queries, upserts, and price history.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from src.shared.logging.log_setup import get_logger

from .base_repository import BaseRepository

logger = get_logger(__name__)


class IdealoProductRepository(BaseRepository):
    """Repository for Idealo product data operations."""
    
    def deactivate_all_products(self) -> None:
        """Mark all products as inactive before processing new data."""
        query = "UPDATE deal_board_product SET is_active = FALSE;"
        self._execute_query(query)
        logger.info("all_products_deactivated")
    
    def find_by_source_url(self, source_url: str) -> Optional[tuple]:
        """
        Find product by source URL.
        
        Args:
            source_url: Product URL from Idealo
            
        Returns:
            Tuple of (id, latest_price, last_ebay_check) or None if not found
        """
        query = "SELECT id, price, last_ebay_check FROM deal_board_product WHERE source_url = %s;"
        results = self._execute_query(query, (source_url,))
        return results[0] if results else None
    
    def update_product(self, product_id: int, price: Any, discount: Optional[int] = None) -> None:
        """
        Update existing product with new price and discount.
        
        Args:
            product_id: Product ID to update
            price: New price value
            discount: New discount percentage (optional, defaults to 0)
        """
        # use 0 as default if discount is None
        discount_value = discount if discount is not None else 0
        query = """
            UPDATE deal_board_product
            SET price = %s, discount = %s, is_active = TRUE, updated_at = NOW()
            WHERE id = %s;
        """
        self._execute_query(query, (price, discount_value, product_id))
        logger.debug("product_updated", product_id=product_id)
    
    def insert_product(self, product_data: Dict[str, Any]) -> Optional[int]:
        """
        Insert new product into database (matching Django model fields).
        
        Args:
            product_data: Dictionary with product information
            
        Returns:
            New product ID or None if insertion failed
        """
        # match exact Django model fields with updated field names
        # include new profit fields with default values (NULL for calculations, FALSE for is_profitable)
        # use 0.0 as default for discount if not provided
        query = """
            INSERT INTO deal_board_product 
            (name, source_url, image_url, price, discount, is_active, category, 
             potential_profit, profit_percentage, is_profitable, min_ebay_price,
             created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, TRUE, %s, NULL, NULL, FALSE, NULL, NOW(), NOW()) RETURNING id;
        """
        params = (
            product_data["name"],
            product_data["source_url"],
            product_data["image_url"],
            product_data["price"],
            product_data.get("discount", 0.0),  # default to 0.0 if discount not provided
            product_data.get("category", "Unknown")  # use default if not provided
        )
        
        product_id = self._execute_with_return(query, params)
        if product_id:
            logger.debug("product_inserted", product_id=product_id, name=product_data["name"][:30])
        return product_id
    
    def add_price_log(self, product_id: int, price: Any) -> None:
        """
        Add price history entry for product.
        
        Args:
            product_id: Product ID
            price: Price value to log
        """
        query = """
            INSERT INTO deal_board_pricelog (product_id, price, scraped_at)
            VALUES (%s, %s, NOW());
        """
        self._execute_query(query, (product_id, price))
        logger.debug("price_log_added", product_id=product_id)
    
    def update_last_ebay_check(self, product_id: int) -> None:
        """
        Update the last_ebay_check timestamp for a product.
        
        Args:
            product_id: Product ID to update
        """
        query = """
            UPDATE deal_board_product
            SET last_ebay_check = NOW()
            WHERE id = %s;
        """
        self._execute_query(query, (product_id,))
        logger.debug("last_ebay_check_updated", product_id=product_id)
    
    def update_product_profit(
        self, 
        product_id: int, 
        potential_profit: Any,
        profit_percentage: Optional[float],
        is_profitable: bool,
        min_ebay_price: Any
    ) -> None:
        """
        Update product with calculated profit information.
        
        Args:
            product_id: Product ID to update
            potential_profit: Calculated potential profit (Decimal or None)
            profit_percentage: Profit margin as percentage (float or None)
            is_profitable: Whether the product is considered profitable
            min_ebay_price: Minimum price found on eBay (Decimal or None)
        """
        query = """
            UPDATE deal_board_product
            SET potential_profit = %s,
                profit_percentage = %s,
                is_profitable = %s,
                min_ebay_price = %s,
                updated_at = NOW()
            WHERE id = %s;
        """
        self._execute_query(
            query, 
            (potential_profit, profit_percentage, is_profitable, min_ebay_price, product_id)
        )
        logger.info(
            "product_profit_updated", 
            product_id=product_id,
            is_profitable=is_profitable,
            potential_profit=potential_profit
        )
    
    def process_scraped_products(self, products_to_process: List[Dict[str, Any]], ebay_check_threshold_days: int = 14) -> List[Dict[str, Any]]:
        """
        Process and store list of scraped products, tracking which need eBay checks.
        
        Args:
            products_to_process: List of product dictionaries
            ebay_check_threshold_days: Days after which eBay data is considered stale
            
        Returns:
            List of products needing eBay check with product_id, name, and type
        """
        if not products_to_process:
            logger.warning("no_products_to_process")
            return []
        
        needs_ebay_check = []
        
        try:
            # deactivate all products first (original logic)
            self.deactivate_all_products()
            
            # process each product
            for product in products_to_process:
                existing_product = self.find_by_source_url(product["source_url"])
                
                product_id = None
                if existing_product:
                    # update existing product
                    product_id, old_price, last_ebay_check = existing_product
                    # pass discount with get() to handle missing values
                    self.update_product(product_id, product["price"], product.get("discount"))
                    
                    # check if eBay data is stale
                    if last_ebay_check is None:
                        needs_ebay_check.append({
                            "product_id": product_id,
                            "name": product["name"],
                            "type": "returning_never_checked"
                        })
                        logger.debug("ebay_check_needed", product_id=product_id, reason="never_checked")
                    else:
                        # use timezone-aware datetime for comparison
                        berlin_tz = ZoneInfo("Europe/Berlin")
                        now_berlin = datetime.now(berlin_tz)
                        
                        # convert last_ebay_check to timezone-aware if needed
                        if last_ebay_check.tzinfo is None:
                            # assume database times are in Berlin timezone
                            last_ebay_check_aware = last_ebay_check.replace(tzinfo=berlin_tz)
                        else:
                            # already timezone-aware, convert to Berlin if different
                            last_ebay_check_aware = last_ebay_check.astimezone(berlin_tz)
                        
                        days_since_check = (now_berlin - last_ebay_check_aware).days
                        if days_since_check > ebay_check_threshold_days:
                            needs_ebay_check.append({
                                "product_id": product_id,
                                "name": product["name"],
                                "type": "returning_stale"
                            })
                            logger.debug("ebay_check_needed", product_id=product_id, days_since=days_since_check)
                else:
                    # insert new product
                    product_id = self.insert_product(product)
                    # new products always need eBay check
                    if product_id:
                        needs_ebay_check.append({
                            "product_id": product_id,
                            "name": product["name"],
                            "type": "new"
                        })
                        logger.debug("ebay_check_needed", product_id=product_id, reason="new_product")
                
                # add price history entry (original logic)
                if product_id:
                    self.add_price_log(product_id, product["price"])
            
            # commit all changes
            self.commit()
            logger.info(
                "database_update_complete", 
                products_processed=len(products_to_process),
                needs_ebay_check=len(needs_ebay_check)
            )
            
            return needs_ebay_check
            
        except Exception as e:
            logger.error("database_processing_error", error=str(e), exc_info=True)
            self.rollback()
            raise