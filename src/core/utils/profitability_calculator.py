"""
Calculate profit margins, fees, and determine if deals are worth pursuing.
"""

from decimal import Decimal
from typing import List

from src.core.models.ebay_listing import EbayListing
from src.core.models.idealo_product import IdealoProduct
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class ProfitabilityCalculator:
    """Handles profitability calculations for product comparisons."""
    
    @staticmethod
    def calculate_simple_profit(source_price: Decimal, selling_price: Decimal) -> Decimal:
        """
        Calculate simple profit difference (original eBay scraper logic).
        
        Args:
            source_price: Price from Idealo
            selling_price: Price from eBay
            
        Returns:
            Profit amount
        """
        return selling_price - source_price
    
    @staticmethod
    def calculate_profit_percentage(source_price: Decimal, selling_price: Decimal) -> float:
        """
        Calculate profit as percentage of source price.
        
        Args:
            source_price: Price from Idealo
            selling_price: Price from eBay
            
        Returns:
            Profit percentage
        """
        if source_price <= 0:
            return 0.0
        
        profit = selling_price - source_price
        return float((profit / source_price) * 100)
    
    @staticmethod
    def is_profitable(
        source_price: Decimal,
        selling_price: Decimal,
        min_profit_margin: Decimal = Decimal("20.0"),
        min_profit_percentage: float = 15.0
    ) -> bool:
        """
        Determine if a product comparison is profitable.
        
        Args:
            source_price: Price from Idealo
            selling_price: Price from eBay (lowest competitive price)
            min_profit_margin: Minimum profit in EUR
            min_profit_percentage: Minimum profit percentage
            
        Returns:
            True if profitable based on both criteria
        """
        profit_amount = ProfitabilityCalculator.calculate_simple_profit(source_price, selling_price)
        profit_percent = ProfitabilityCalculator.calculate_profit_percentage(source_price, selling_price)
        
        is_profitable = (
            profit_amount >= min_profit_margin and
            profit_percent >= min_profit_percentage
        )
        
        logger.debug(
            "profitability_check",
            source_price=str(source_price),
            selling_price=str(selling_price),
            profit_amount=str(profit_amount),
            profit_percent=f"{profit_percent:.1f}%",
            is_profitable=is_profitable
        )
        
        return is_profitable
    
    @staticmethod
    def find_best_competitive_price(listings: List[EbayListing]) -> Decimal:
        """
        Find the lowest price from eBay listings (our competition benchmark).
        
        Args:
            listings: List of eBay listings
            
        Returns:
            Lowest price found
        """
        if not listings:
            return Decimal("0")
        
        prices = [listing.get_total_price() for listing in listings]
        return min(prices)
    
    @staticmethod
    def format_profit_for_display(
        source_price: Decimal,
        competitive_price: Decimal,
        is_best_match: bool = True
    ) -> dict:
        """
        Format profit information for display (original eBay format logic).
        
        Args:
            source_price: Price from Idealo
            competitive_price: Price from eBay
            is_best_match: Whether this is a best match result
            
        Returns:
            Dictionary with formatted profit info
        """
        potential_profit = ProfitabilityCalculator.calculate_simple_profit(source_price, competitive_price)
        
        return {
            "is_best_match": is_best_match,
            "potential_profit": potential_profit,
            "profit_display": f"€{potential_profit:.2f}"
        }