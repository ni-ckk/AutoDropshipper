"""
Unit tests for IdealoScraper.
"""

import pytest
from unittest.mock import Mock, patch

from src.scrapers.idealo.idealo_scraper import IdealoScraper


class TestIdealoScraper:
    """Test IdealoScraper functionality."""
    
    @pytest.fixture
    def scraper(self):
        """Provide IdealoScraper instance for testing."""
        with patch('src.scrapers.idealo.idealo_scraper.SB'):
            scraper = IdealoScraper()
            scraper.driver = Mock()  # inject mock driver
            return scraper
    
    def test_search_url_construction(self, scraper):
        """Test search URL is constructed correctly."""
        base_url = scraper._build_search_url("laptop gaming")
        assert "laptop+gaming" in base_url
        assert "idealo.de" in base_url
    
    def test_search_products_calls_correct_methods(self, scraper):
        """Test that search_products calls driver methods correctly."""
        # mock driver responses
        mock_elements = [Mock(), Mock()]
        scraper.driver.find_elements.return_value = mock_elements
        scraper.driver.current_url = "https://idealo.de/search"
        
        # mock parser
        with patch.object(scraper.parser, 'parse_product_grid_item') as mock_parse:
            mock_parse.return_value = Mock()  # mock product
            
            products = scraper.search_products("test query", max_results=10)
            
            # verify driver was called correctly
            scraper.driver.get.assert_called()
            scraper.driver.find_elements.assert_called()
            
            # verify parser was called for each element
            assert mock_parse.call_count == len(mock_elements)
            assert len(products) == len(mock_elements)
    
    def test_handle_cookie_banner(self, scraper):
        """Test cookie banner handling."""
        # mock cookie banner element
        cookie_button = Mock()
        scraper.driver.find_element.return_value = cookie_button
        
        scraper._handle_cookie_banner()
        
        cookie_button.click.assert_called_once()
    
    def test_close_driver(self, scraper):
        """Test driver cleanup."""
        scraper.close()
        scraper.driver.quit.assert_called_once()