"""
Database connection, transaction, and constraint violation exceptions.
"""

from typing import Optional

from .base import AutoDropshipperError


class DatabaseError(AutoDropshipperError):
    """Base exception for database-related errors."""
    
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    
    def __init__(self, host: str, port: int, database: str, message: str):
        """
        Initialize database connection error.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            message: Error message
        """
        self.host = host
        self.port = port
        self.database = database
        super().__init__(
            f"Failed to connect to {database} at {host}:{port}: {message}"
        )


class DatabaseOperationError(DatabaseError):
    """Raised when a database operation fails."""
    
    def __init__(self, operation: str, table: Optional[str] = None, message: str = ""):
        """
        Initialize database operation error.
        
        Args:
            operation: Operation that failed (INSERT, UPDATE, etc.)
            table: Table name if applicable
            message: Error message
        """
        self.operation = operation
        self.table = table
        error_msg = f"Database operation '{operation}' failed"
        if table:
            error_msg += f" on table '{table}'"
        if message:
            error_msg += f": {message}"
        super().__init__(error_msg)


class TransactionError(DatabaseError):
    """Raised when a database transaction fails."""
    
    def __init__(self, action: str, message: str = ""):
        """
        Initialize transaction error.
        
        Args:
            action: Transaction action (commit, rollback, etc.)
            message: Error message
        """
        self.action = action
        error_msg = f"Transaction {action} failed"
        if message:
            error_msg += f": {message}"
        super().__init__(error_msg)


class ConstraintViolationError(DatabaseError):
    """Raised when a database constraint is violated."""
    
    def __init__(self, constraint: str, table: str, message: str = ""):
        """
        Initialize constraint violation error.
        
        Args:
            constraint: Constraint name or type
            table: Table name
            message: Error message
        """
        self.constraint = constraint
        self.table = table
        error_msg = f"Constraint '{constraint}' violated on table '{table}'"
        if message:
            error_msg += f": {message}"
        super().__init__(error_msg)