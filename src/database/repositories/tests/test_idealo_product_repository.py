"""
Unit tests for IdealoProductRepository.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

from src.core.models.idealo_product import IdealoProduct
from src.database.repositories.idealo_product_repository import IdealoProductRepository


class TestIdealoProductRepository:
    """Test IdealoProductRepository database operations."""
    
    @pytest.fixture
    def repository(self):
        """Provide repository instance for testing."""
        return IdealoProductRepository()
    
    @pytest.fixture
    def sample_product(self):
        """Provide sample product for testing."""
        return IdealoProduct(
            name="Test Product",
            price=Decimal("99.99"),
            discount=15,
            source_url="https://idealo.de/test-product"
        )
    
    @patch('src.database.repositories.idealo_product_repository.get_db_connection')
    def test_save_product_success(self, mock_get_conn, repository, sample_product):
        """Test successful product save."""
        # mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # mock cursor.fetchone to return a product_id
        mock_cursor.fetchone.return_value = {'product_id': str(uuid4())}
        
        product_id = repository.save(sample_product)
        
        # verify database operations
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
        assert product_id is not None
    
    @patch('src.database.repositories.idealo_product_repository.get_db_connection')
    def test_find_by_url_exists(self, mock_get_conn, repository):
        """Test finding product by URL when it exists."""
        # mock database response
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # mock product data from database
        mock_cursor.fetchone.return_value = {
            'product_id': str(uuid4()),
            'name': 'Found Product',
            'price': Decimal('149.99'),
            'discount_percentage': 20,
            'source_url': 'https://idealo.de/found-product',
            'image_url': None,
            'category': 'Electronics'
        }
        
        product = repository.find_by_url("https://idealo.de/found-product")
        
        assert product is not None
        assert product.name == "Found Product"
        assert product.price == Decimal("149.99")
        mock_cursor.execute.assert_called()
    
    @patch('src.database.repositories.idealo_product_repository.get_db_connection')
    def test_find_by_url_not_exists(self, mock_get_conn, repository):
        """Test finding product by URL when it doesn't exist."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # mock no result found
        mock_cursor.fetchone.return_value = None
        
        product = repository.find_by_url("https://idealo.de/nonexistent")
        
        assert product is None
    
    @patch('src.database.repositories.idealo_product_repository.get_db_connection')
    def test_get_recent_products(self, mock_get_conn, repository):
        """Test getting recent products."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # mock multiple products
        mock_cursor.fetchall.return_value = [
            {
                'product_id': str(uuid4()),
                'name': 'Product 1',
                'price': Decimal('99.99'),
                'discount_percentage': 10,
                'source_url': 'https://idealo.de/product1',
                'image_url': None,
                'category': None
            },
            {
                'product_id': str(uuid4()),
                'name': 'Product 2',
                'price': Decimal('149.99'),
                'discount_percentage': 15,
                'source_url': 'https://idealo.de/product2',
                'image_url': None,
                'category': None
            }
        ]
        
        products = repository.get_recent_products(limit=10)
        
        assert len(products) == 2
        assert all(isinstance(p, IdealoProduct) for p in products)
        mock_cursor.execute.assert_called()
    
    def test_to_dict(self, repository, sample_product):
        """Test product to dict conversion."""
        product_dict = repository._to_dict(sample_product)
        
        assert product_dict['name'] == "Test Product"
        assert product_dict['price'] == Decimal("99.99")
        assert product_dict['discount_percentage'] == 15
        assert product_dict['source_url'] == "https://idealo.de/test-product"