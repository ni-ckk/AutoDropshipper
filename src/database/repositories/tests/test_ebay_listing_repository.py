"""
Unit tests for EbayListingRepository.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

from src.core.models.ebay_listing import EbayListing
from src.database.repositories.ebay_listing_repository import EbayListingRepository


class TestEbayListingRepository:
    """Test EbayListingRepository database operations."""
    
    @pytest.fixture
    def repository(self):
        """Provide repository instance for testing."""
        return EbayListingRepository()
    
    @pytest.fixture
    def sample_listing(self):
        """Provide sample eBay listing for testing."""
        return EbayListing(
            title="Test eBay Item",
            subtitle="Great condition",
            price=Decimal("149.99"),
            source_url="https://ebay.com/test-item",
            image_url="https://ebay.com/image.jpg"
        )
    
    @patch('src.database.repositories.ebay_listing_repository.get_db_connection')
    def test_save_listing_success(self, mock_get_conn, repository, sample_listing):
        """Test successful listing save."""
        # mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # mock cursor.fetchone to return a listing_id
        mock_cursor.fetchone.return_value = {'listing_id': str(uuid4())}
        
        listing_id = repository.save(sample_listing)
        
        # verify database operations
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
        assert listing_id is not None
    
    @patch('src.database.repositories.ebay_listing_repository.get_db_connection')
    def test_find_by_url_exists(self, mock_get_conn, repository):
        """Test finding listing by URL when it exists."""
        # mock database response
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # mock listing data from database
        mock_cursor.fetchone.return_value = {
            'listing_id': str(uuid4()),
            'title': 'Found eBay Item',
            'subtitle': 'Excellent condition',
            'price': Decimal('199.99'),
            'source_url': 'https://ebay.com/found-item',
            'image_url': 'https://ebay.com/found-image.jpg'
        }
        
        listing = repository.find_by_url("https://ebay.com/found-item")
        
        assert listing is not None
        assert listing.title == "Found eBay Item"
        assert listing.price == Decimal("199.99")
        mock_cursor.execute.assert_called()
    
    @patch('src.database.repositories.ebay_listing_repository.get_db_connection')
    def test_find_by_url_not_exists(self, mock_get_conn, repository):
        """Test finding listing by URL when it doesn't exist."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # mock no result found
        mock_cursor.fetchone.return_value = None
        
        listing = repository.find_by_url("https://ebay.com/nonexistent")
        
        assert listing is None
    
    @patch('src.database.repositories.ebay_listing_repository.get_db_connection')
    def test_get_recent_listings(self, mock_get_conn, repository):
        """Test getting recent listings."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # mock multiple listings
        mock_cursor.fetchall.return_value = [
            {
                'listing_id': str(uuid4()),
                'title': 'eBay Item 1',
                'subtitle': None,
                'price': Decimal('99.99'),
                'source_url': 'https://ebay.com/item1',
                'image_url': None
            },
            {
                'listing_id': str(uuid4()),
                'title': 'eBay Item 2',
                'subtitle': 'Like new',
                'price': Decimal('149.99'),
                'source_url': 'https://ebay.com/item2',
                'image_url': 'https://ebay.com/item2.jpg'
            }
        ]
        
        listings = repository.get_recent_listings(limit=10)
        
        assert len(listings) == 2
        assert all(isinstance(l, EbayListing) for l in listings)
        mock_cursor.execute.assert_called()
    
    def test_to_dict(self, repository, sample_listing):
        """Test listing to dict conversion."""
        listing_dict = repository._to_dict(sample_listing)
        
        assert listing_dict['title'] == "Test eBay Item"
        assert listing_dict['subtitle'] == "Great condition"
        assert listing_dict['price'] == Decimal("149.99")
        assert listing_dict['source_url'] == "https://ebay.com/test-item"
        assert listing_dict['image_url'] == "https://ebay.com/image.jpg"