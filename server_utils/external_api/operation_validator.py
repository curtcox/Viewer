"""Validate operation names against allowed set for external API servers."""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

from .error_response import validation_error


class OperationValidator:
    """Validate operation names against allowed set.
    
    This class helps standardize operation validation across external server
    definitions, reducing duplication and ensuring consistent error messages.
    
    Example:
        >>> validator = OperationValidator({"list_issues", "get_issue", "create_issue"})
        >>> error = validator.validate("list_issues")
        >>> error is None
        True
        >>> error = validator.validate("delete_issue")
        >>> error["output"]["error"]["message"]
        'Unsupported operation'
    """

    def __init__(self, valid_operations: Set[str]):
        """Initialize validator with valid operations.
        
        Args:
            valid_operations: Set of allowed operation names (case-insensitive)
        """
        self.valid_operations = {op.lower() for op in valid_operations}

    def validate(self, operation: str) -> Optional[Dict[str, Any]]:
        """Validate an operation name.
        
        Args:
            operation: Operation name to validate
            
        Returns:
            Error dict if invalid, None if valid
        """
        if operation.lower() not in self.valid_operations:
            return validation_error(
                "Unsupported operation",
                field="operation",
                details={
                    "provided": operation,
                    "valid_operations": sorted(self.valid_operations),
                },
            )
        return None

    def normalize(self, operation: str) -> str:
        """Return normalized (lowercase) operation name.
        
        Args:
            operation: Operation name to normalize
            
        Returns:
            Lowercase version of the operation name
        """
        return operation.lower()

    def is_valid(self, operation: str) -> bool:
        """Check if an operation is valid without returning an error.
        
        Args:
            operation: Operation name to check
            
        Returns:
            True if operation is valid, False otherwise
        """
        return operation.lower() in self.valid_operations
