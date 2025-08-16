"""
PostgreSQL connection pooling and lifecycle management.
"""

import psycopg2
from psycopg2.extensions import connection as Connection
from typing import Optional

from src.core.exceptions.database_errors import DatabaseConnectionError
from src.shared.config.app_settings import get_app_config
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class ConnectionHandler:
    """Handles PostgreSQL connection lifecycle."""
    
    def __init__(self):
        """Initialize connection handler with configuration."""
        self.config = get_app_config()
        self.conn: Optional[Connection] = None
    
    def connect(self) -> Connection:
        """
        Establish database connection.
        
        Returns:
            PostgreSQL connection object
            
        Raises:
            DatabaseConnectionError: If connection fails
        """
        try:
            db_config = self.config.database
            self.conn = psycopg2.connect(
                dbname=db_config.POSTGRES_DB,
                user=db_config.POSTGRES_USER,
                password=db_config.POSTGRES_PASSWORD,
                host=db_config.POSTGRES_HOST,
                port=db_config.DB_PORT
            )
            logger.info("database_connected")
            return self.conn
            
        except psycopg2.OperationalError as e:
            logger.error("database_connection_failed", error=str(e))
            raise DatabaseConnectionError(
                host=self.config.database.POSTGRES_HOST,
                port=self.config.database.DB_PORT,
                database=self.config.database.POSTGRES_DB,
                message=str(e)
            )
    
    def disconnect(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("database_disconnected")
    
    def get_connection(self) -> Connection:
        """
        Get current connection or create new one.
        
        Returns:
            Active PostgreSQL connection
        """
        if not self.conn or self.conn.closed:
            return self.connect()
        return self.conn
    
    def __enter__(self):
        """Context manager entry."""
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()