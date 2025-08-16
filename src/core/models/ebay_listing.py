"""
Pydantic model for eBay listing data validation and serialization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class EbayListing(BaseModel):
    """
    Model representing an eBay listing for comparison.
    
    Attributes:
        title: Product title on eBay
        subtitle: Additional product description
        price: Listed price in EUR
        source_url: URL to the eBay listing
        image_url: URL to the product image
        is_best_match: Whether listing is in eBay's best match section
        scraped_at: Timestamp when listing was scraped
    """
    
    title: str = Field(..., min_length=1, max_length=500)
    subtitle: Optional[str] = Field(None, max_length=500)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    source_url: HttpUrl
    image_url: Optional[HttpUrl] = None
    is_best_match: bool = Field(default=False)
    scraped_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """
        Validates that price is reasonable.
        
        Args:
            v: Price value to validate
            
        Returns:
            Validated price
            
        Raises:
            ValueError: If price exceeds maximum allowed value
        """
        if v > Decimal("1000000"):
            raise ValueError("Price cannot exceed 1,000,000")
        return v
    
    def get_total_price(self) -> Decimal:
        """
        Get the listing price (no shipping data extracted currently).
        
        Returns:
            Listing price
        """
        return self.price
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }