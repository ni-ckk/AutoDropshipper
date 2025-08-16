"""
Unit tests for ProductComparison model.
"""

import pytest
from decimal import Decimal

from src.core.models.ebay_listing import EbayListing
from src.core.models.idealo_product import IdealoProduct
from src.core.models.product_comparison import ProductComparison


class TestProductComparison:
    """Test ProductComparison model and profitability calculations."""
    
    @pytest.fixture
    def sample_idealo_product(self):
        """Provide sample Idealo product for testing."""
        return IdealoProduct(
            name="Test Product",
            price=Decimal("100.00"),
            discount=20,
            source_url="https://idealo.de/test-product"
        )
    
    @pytest.fixture
    def sample_ebay_listings(self):
        """Provide sample eBay listings for testing."""
        return [
            EbayListing(
                title="Test Product - Good Deal",
                price=Decimal("150.00"),
                source_url="https://ebay.com/item1"
            ),
            EbayListing(
                title="Test Product - Better Price",
                price=Decimal("130.00"),
                source_url="https://ebay.com/item2"
            ),
            EbayListing(
                title="Test Product - Expensive",
                price=Decimal("200.00"),
                source_url="https://ebay.com/item3"
            )
        ]
    
    def test_comparison_creation(self, sample_idealo_product, sample_ebay_listings):
        """Test creating a product comparison."""
        comparison = ProductComparison(
            idealo_product=sample_idealo_product,
            ebay_listings=sample_ebay_listings
        )
        
        assert comparison.idealo_product == sample_idealo_product
        assert len(comparison.ebay_listings) == 3
        assert comparison.min_ebay_price is None  # not calculated yet
    
    def test_profitability_calculation(self, sample_idealo_product, sample_ebay_listings):
        """Test profitability calculation logic."""
        comparison = ProductComparison(
            idealo_product=sample_idealo_product,
            ebay_listings=sample_ebay_listings
        )
        
        comparison.calculate_profitability(min_profit_margin=Decimal("20.0"))
        
        # min eBay price should be 130.00
        assert comparison.min_ebay_price == Decimal("130.00")
        # potential profit = 130.00 - 100.00 = 30.00
        assert comparison.potential_profit == Decimal("30.00")
        # profit margin = (30.00 / 130.00) * 100 = 23.08%
        assert comparison.profit_margin == Decimal("23.08")
        # should be profitable (23.08% > 20%)
        assert comparison.is_profitable is True
    
    def test_not_profitable_scenario(self, sample_idealo_product):
        """Test scenario where product is not profitable."""
        expensive_listings = [
            EbayListing(
                title="Expensive Item",
                price=Decimal("110.00"),  # only 10 euro profit
                source_url="https://ebay.com/expensive"
            )
        ]
        
        comparison = ProductComparison(
            idealo_product=sample_idealo_product,
            ebay_listings=expensive_listings
        )
        
        comparison.calculate_profitability(min_profit_margin=Decimal("20.0"))
        
        # profit margin = (10.00 / 110.00) * 100 = 9.09%
        assert comparison.profit_margin == Decimal("9.09")
        # should not be profitable (9.09% < 20%)
        assert comparison.is_profitable is False
    
    def test_empty_listings_handling(self, sample_idealo_product):
        """Test handling of empty eBay listings."""
        comparison = ProductComparison(
            idealo_product=sample_idealo_product,
            ebay_listings=[]
        )
        
        comparison.calculate_profitability()
        
        assert comparison.min_ebay_price is None
        assert comparison.potential_profit is None
        assert comparison.profit_margin is None
        assert comparison.is_profitable is False