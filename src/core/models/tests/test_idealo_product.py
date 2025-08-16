"""
Unit tests for IdealoProduct model.
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from src.core.models.idealo_product import IdealoProduct


class TestIdealoProduct:
    """Test IdealoProduct model validation and behavior."""
    
    def test_valid_product_creation(self):
        """Test creating a valid Idealo product."""
        product = IdealoProduct(
            name="Test Product",
            price=Decimal("99.99"),
            discount=15,
            source_url="https://idealo.de/test-product",
            image_url="https://idealo.de/test-image.jpg"
        )
        
        assert product.name == "Test Product"
        assert product.price == Decimal("99.99")
        assert product.discount == 15
        assert str(product.source_url) == "https://idealo.de/test-product"
        assert str(product.image_url) == "https://idealo.de/test-image.jpg"
    
    def test_product_with_no_discount(self):
        """Test product creation with no discount."""
        product = IdealoProduct(
            name="Test Product",
            price=Decimal("50.00"),
            source_url="https://idealo.de/test"
        )
        
        assert product.discount is None
        assert product.image_url is None
    
    def test_empty_name_validation(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IdealoProduct(
                name="",
                price=Decimal("99.99"),
                source_url="https://idealo.de/test"
            )
        assert "at least 1 character" in str(exc_info.value)
    
    def test_zero_price_validation(self):
        """Test that zero price is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IdealoProduct(
                name="Test Product",
                price=Decimal("0.00"),
                source_url="https://idealo.de/test"
            )
        assert "greater than 0" in str(exc_info.value)
    
    def test_negative_discount_validation(self):
        """Test that negative discount is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IdealoProduct(
                name="Test Product",
                price=Decimal("99.99"),
                discount=-5,
                source_url="https://idealo.de/test"
            )
        assert "greater than or equal to 0" in str(exc_info.value)
    
    def test_discount_over_100_validation(self):
        """Test that discount over 100% is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IdealoProduct(
                name="Test Product",
                price=Decimal("99.99"),
                discount=150,
                source_url="https://idealo.de/test"
            )
        assert "less than or equal to 100" in str(exc_info.value)
    
    def test_invalid_url_validation(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IdealoProduct(
                name="Test Product",
                price=Decimal("99.99"),
                source_url="not-a-url"
            )
        assert "URL" in str(exc_info.value)