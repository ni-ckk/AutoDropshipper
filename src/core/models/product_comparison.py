"""
Model for comparing Idealo products with eBay listings.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from src.shared.config.app_settings import get_app_config
from .ebay_listing import EbayListing
from .idealo_product import IdealoProduct


class ProductComparison(BaseModel):
    """
    Model for comparing an Idealo product with eBay listings.
    
    Attributes:
        idealo_product: The source product from Idealo
        ebay_listings: List of comparable eBay listings
        potential_profit: Calculated potential profit margin (based on lowest eBay price)
        profit_percentage: Profit margin as percentage
        is_profitable: Whether the product is considered profitable
        min_ebay_price: Minimum price found on eBay (our competition benchmark)
        comparison_date: When the comparison was made
    """
    
    idealo_product: IdealoProduct
    ebay_listings: List[EbayListing] = Field(default_factory=list)
    potential_profit: Optional[Decimal] = None
    profit_percentage: Optional[float] = None
    is_profitable: bool = False
    min_ebay_price: Optional[Decimal] = None
    comparison_date: datetime = Field(default_factory=datetime.now)
    
    def calculate_profitability(
        self, 
        min_profit_margin: Decimal = Decimal("50.0")
    ) -> None:
        """
        Calculates profitability based on price differences.
        Profit is calculated using the LOWEST eBay price to ensure we can compete.
        
        Args:
            min_profit_margin: Minimum profit margin in EUR to consider profitable
        """
        if not self.ebay_listings:
            self.is_profitable = False
            return
        
        # find minimum eBay price - this is what we need to beat
        ebay_prices = [listing.get_total_price() for listing in self.ebay_listings]
        self.min_ebay_price = min(ebay_prices)
        
        # calculate potential profit based on MINIMUM eBay price
        # we need to be able to sell below the lowest eBay price and still make profit
        idealo_price = self.idealo_product.price
        self.potential_profit = self.min_ebay_price - idealo_price
        
        # calculate profit percentage for informational purposes only
        if idealo_price > 0:
            self.profit_percentage = float(
                ((self.min_ebay_price - idealo_price) / idealo_price) * 100
            )
        
        # determine if profitable based only on margin
        self.is_profitable = self.potential_profit >= min_profit_margin
    
    def get_cheapest_listing(self) -> Optional[EbayListing]:
        """
        Get the eBay listing with the lowest price.
        This is our competition benchmark - we need to sell below this price.
        
        Returns:
            The cheapest eBay listing or None
        """
        if not self.ebay_listings:
            return None
        return min(self.ebay_listings, key=lambda x: x.get_total_price())
    
    def get_summary(self) -> str:
        """
        Generate a summary of the comparison.
        
        Returns:
            Human-readable summary string
        """
        if not self.ebay_listings:
            return f"No eBay listings found for {self.idealo_product.name}"
        
        config = get_app_config()
        baseline = config.PROFIT_PERCENTAGE_BASELINE
        
        # determine emoji and text based on profit percentage vs baseline
        if self.profit_percentage is not None:
            if self.profit_percentage >= baseline:
                percentage_text = f"🚀 High margin: ({self.profit_percentage:.1f}% ≥ {baseline}% baseline)"
            else:
                percentage_text = f"⚠️ Normal margin: ({self.profit_percentage:.1f}% < {baseline}% baseline)"
        else:
            percentage_text = "N/A"
        
        return (
            f"Product: {self.idealo_product.name}\n"
            f"Idealo Price: €{self.idealo_product.price}\n"
            f"Lowest eBay Price: €{self.min_ebay_price}\n"
            f"Potential Profit: €{self.potential_profit}\n"
            f"Profit Margin: {percentage_text}\n"
            f"Profitable: {'Yes' if self.is_profitable else 'No'}"
        )
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }