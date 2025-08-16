"""
Generic repository pattern with CRUD operations for any entity.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

import psycopg2

from src.core.exceptions.database_errors import DatabaseConnectionError, DatabaseOperationError
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class BaseRepository(ABC):
    """Generic repository pattern with CRUD operations."""
    
    def __init__(self, connection):
        """
        Initialize repository with database connection.
        
        Args:
            connection: psycopg2 connection object
        """
        self.conn = connection
    
    def _execute_query(self, query: str, params: tuple = ()) -> Optional[List[tuple]]:
        """
        Execute a query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Query results or None for non-SELECT queries
            
        Raises:
            DatabaseOperationError: If query execution fails
        """
        if not self.conn:
            raise DatabaseConnectionError("localhost", 5432, "unknown", "No connection available")
        
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            
            # return results for SELECT queries
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            
            return None
            
        except Exception as e:
            logger.error("query_execution_failed", query=query[:100], error=str(e))
            raise DatabaseOperationError("EXECUTE", None, str(e))
        finally:
            cursor.close()
    
    def _execute_with_return(self, query: str, params: tuple = ()) -> Any:
        """
        Execute a query and return single value (for RETURNING clauses).
        
        Args:
            query: SQL query string with RETURNING clause
            params: Query parameters
            
        Returns:
            First column of first row
            
        Raises:
            DatabaseOperationError: If query execution fails
        """
        if not self.conn:
            raise DatabaseConnectionError("localhost", 5432, "unknown", "No connection available")
        
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else None
            
        except Exception as e:
            logger.error("query_with_return_failed", query=query[:100], error=str(e))
            raise DatabaseOperationError("EXECUTE_RETURNING", None, str(e))
        finally:
            cursor.close()
    
    def commit(self) -> None:
        """Commit current transaction."""
        if self.conn:
            self.conn.commit()
    
    def rollback(self) -> None:
        """Rollback current transaction."""
        if self.conn:
            self.conn.rollback()