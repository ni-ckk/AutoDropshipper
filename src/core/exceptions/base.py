"""
Base exception classes for all domain-specific errors.
"""


class AutoDropshipperError(Exception):
    """Base exception for all application-specific errors."""
    
    pass


class ValidationError(AutoDropshipperError):
    """Base exception for all validation-related errors."""
    
    def __init__(self, field: str, value: any, message: str):
        """
        Initialize validation error.
        
        Args:
            field: Field that failed validation
            value: Invalid value
            message: Error message
        """
        self.field = field
        self.value = value
        super().__init__(f"Validation failed for {field}={value}: {message}")