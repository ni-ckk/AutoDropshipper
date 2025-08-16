"""
Unit tests for EbayListing model.
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from src.core.models.ebay_listing import EbayListing


class TestEbayListing:
    """Test EbayListing model validation and behavior."""
    
    def test_valid_listing_creation(self):
        """Test creating a valid eBay listing."""
        listing = EbayListing(
            title="Test eBay Item",
            subtitle="Great condition",
            price=Decimal("149.99"),
            source_url="https://ebay.com/test-item",
            image_url="https://ebay.com/test-image.jpg"
        )
        
        assert listing.title == "Test eBay Item"
        assert listing.subtitle == "Great condition"
        assert listing.price == Decimal("149.99")
        assert str(listing.source_url) == "https://ebay.com/test-item"
        assert str(listing.image_url) == "https://ebay.com/test-image.jpg"
    
    def test_listing_without_optional_fields(self):
        """Test listing creation without optional fields."""
        listing = EbayListing(
            title="Basic eBay Item",
            price=Decimal("99.00"),
            source_url="https://ebay.com/basic-item"
        )
        
        assert listing.subtitle is None
        assert listing.image_url is None
    
    def test_empty_title_validation(self):
        """Test that empty title is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EbayListing(
                title="",
                price=Decimal("99.99"),
                source_url="https://ebay.com/test"
            )
        assert "at least 1 character" in str(exc_info.value)
    
    def test_zero_price_validation(self):
        """Test that zero price is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EbayListing(
                title="Test Item",
                price=Decimal("0.00"),
                source_url="https://ebay.com/test"
            )
        assert "greater than 0" in str(exc_info.value)
    
    def test_invalid_source_url_validation(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EbayListing(
                title="Test Item",
                price=Decimal("99.99"),
                source_url="invalid-url"
            )
        assert "URL" in str(exc_info.value)