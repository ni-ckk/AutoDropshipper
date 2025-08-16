"""
Pydantic model for Idealo product data validation and serialization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class IdealoProduct(BaseModel):
    """
    Model representing a product scraped from Idealo.
    
    Attributes:
        name: Product name/title
        price: Current price in EUR
        discount: Discount as decimal (e.g., 0.25 for 25%) if available
        source_url: URL to the product page on Idealo
        image_url: URL to the product image
        category: Product category on Idealo  
        is_active: Whether the product is currently active
        scraped_at: Timestamp when product was scraped
    """
    
    name: str = Field(..., min_length=1, max_length=500)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    discount: Optional[Decimal] = Field(None, ge=0, le=1, decimal_places=2)
    source_url: HttpUrl
    image_url: Optional[HttpUrl] = None
    category: str = Field("Electronics", max_length=100)
    is_active: bool = Field(True)
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
    
    @field_validator("discount")
    @classmethod
    def validate_discount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """
        Validates discount is in proper decimal format.
        
        Args:
            v: Discount value to validate (0.0 to 1.0 for 0% to 100%)
            
        Returns:
            Validated discount
            
        Raises:
            ValueError: If discount is out of valid range
        """
        if v is not None:
            if v < 0 or v > 1:
                raise ValueError("Discount must be between 0 and 1 (0% to 100%)")
        return v
    
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }