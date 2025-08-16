"""
Unit tests for EbayParser.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock

from src.core.models.ebay_listing import EbayListing
from src.scrapers.ebay.ebay_parser import EbayParser


class TestEbayParser:
    """Test EbayParser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Provide EbayParser instance for testing."""
        return EbayParser()
    
    def test_parse_search_result_item_valid(self, parser):
        """Test parsing a valid eBay search result item."""
        # mock selenium element
        mock_element = Mock()
        
        # mock sub-elements
        title_span = Mock()
        title_span.text = "Test eBay Item Title"
        
        subtitle_span = Mock()
        subtitle_span.text = "Great condition"
        
        price_element = Mock()
        price_element.text = "EUR 149,99"
        
        link_element = Mock()
        link_element.get_attribute.return_value = "https://ebay.com/test-item"
        
        image_element = Mock()
        image_element.get_attribute.return_value = "https://ebay.com/image.jpg"
        
        # setup element finding
        def mock_find_element(by, selector):
            selector_map = {
                'div.s-item__title > span': title_span,
                'div.s-item__subtitle > span': subtitle_span,
                'span.s-item__price': price_element,
                'a.s-item__link': link_element,
                'img': image_element,
            }
            return selector_map.get(selector)
        
        mock_element.find_element.side_effect = mock_find_element
        
        listing = parser.parse_search_result_item(mock_element)
        
        assert isinstance(listing, EbayListing)
        assert listing.title == "Test eBay Item Title"
        assert listing.subtitle == "Great condition"
        assert listing.price == Decimal("149.99")
        assert str(listing.source_url) == "https://ebay.com/test-item"
        assert str(listing.image_url) == "https://ebay.com/image.jpg"
    
    def test_parse_price_text(self, parser):
        """Test eBay price parsing."""
        assert parser.parse_price_text("EUR 99,99") == Decimal("99.99")
        assert parser.parse_price_text("€ 1.234,56") == Decimal("1234.56")
        assert parser.parse_price_text("99,00 EUR") == Decimal("99.00")
        assert parser.parse_price_text("invalid") is None
    
    def test_find_divider_index(self, parser):
        """Test finding divider index in search results."""
        # mock elements list with divider
        mock_elements = []
        for i in range(5):
            elem = Mock()
            elem.get_attribute.return_value = f"item-{i}"
            mock_elements.append(elem)
        
        # add divider element
        divider = Mock()
        divider.get_attribute.return_value = "srp-river-answer-REWRITE_START"
        mock_elements.insert(3, divider)
        
        divider_index = parser.find_divider_index(mock_elements)
        assert divider_index == 3