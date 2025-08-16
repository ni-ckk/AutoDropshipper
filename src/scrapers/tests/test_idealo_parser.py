"""
Unit tests for IdealoParser.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock

from src.core.models.idealo_product import IdealoProduct
from src.scrapers.idealo.idealo_parser import IdealoParser


class TestIdealoParser:
    """Test IdealoParser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Provide IdealoParser instance for testing."""
        return IdealoParser()
    
    def test_parse_product_grid_item_valid(self, parser):
        """Test parsing a valid product grid item."""
        # mock selenium element with required attributes
        mock_element = Mock()
        
        # mock the sub-elements
        title_element = Mock()
        title_element.text = "Test Product Name"
        
        price_element = Mock()
        price_element.text = "€99,99"
        
        link_element = Mock()
        link_element.get_attribute.return_value = "https://idealo.de/test-product"
        
        discount_element = Mock()
        discount_element.text = "-15%"
        
        image_element = Mock()
        image_element.get_attribute.return_value = "https://idealo.de/image.jpg"
        
        # set up element finding
        mock_element.find_element.side_effect = lambda by, value: {
            ('css selector', 'div[class*="sr-productSummary__title"]'): title_element,
            ('css selector', 'div[class*="price-info__price"] > span'): price_element,
            ('css selector', 'a[class*="sr-productSummary__title-link"]'): link_element,
            ('css selector', 'div[class*="price-info__discount"]'): discount_element,
            ('css selector', 'img'): image_element,
        }[by, value]
        
        product = parser.parse_product_grid_item(mock_element)
        
        assert isinstance(product, IdealoProduct)
        assert product.name == "Test Product Name"
        assert product.price == Decimal("99.99")
        assert product.discount == 15
        assert str(product.source_url) == "https://idealo.de/test-product"
        assert str(product.image_url) == "https://idealo.de/image.jpg"
    
    def test_parse_price_string(self, parser):
        """Test price string parsing."""
        assert parser.parse_price_string("€99,99") == Decimal("99.99")
        assert parser.parse_price_string("€1.234,56") == Decimal("1234.56")
        assert parser.parse_price_string("99,00 €") == Decimal("99.00")
        assert parser.parse_price_string("invalid") is None
    
    def test_parse_discount_string(self, parser):
        """Test discount string parsing."""
        assert parser.parse_discount_string("-15%") == 15
        assert parser.parse_discount_string("15%") == 15
        assert parser.parse_discount_string("invalid") is None
        assert parser.parse_discount_string("") is None