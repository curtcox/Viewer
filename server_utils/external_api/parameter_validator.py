"""Validate operation-specific parameter requirements for external API servers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .error_response import validation_error


class ParameterValidator:
    """Validate operation-specific parameter requirements.
    
    This class helps standardize parameter validation across external server
    definitions, ensuring required parameters are provided for each operation.
    
    Example:
        >>> REQUIREMENTS = {
        ...     "list_buckets": ["project_id"],
        ...     "get_object": ["bucket", "key"],
        ... }
        >>> validator = ParameterValidator(REQUIREMENTS)
        >>> error = validator.validate_required(
        ...     "get_object",
        ...     {"bucket": "my-bucket", "key": "my-key"}
        ... )
        >>> error is None
        True
    """

    def __init__(self, operation_requirements: Dict[str, List[str]]):
        """Initialize validator with operation requirements.
        
        Args:
            operation_requirements: Dict mapping operations to required parameter names
            
        Example:
            validator = ParameterValidator({
                "list_issues": ["owner", "repo"],
                "create_issue": ["owner", "repo", "title"],
            })
        """
        self.operation_requirements = operation_requirements

    def validate_required(
        self,
        operation: str,
        provided_params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Validate that all required parameters for an operation are provided.
        
        Args:
            operation: Operation being performed
            provided_params: Dict of provided parameters
            
        Returns:
            Error dict if validation fails, None if valid
            
        Example:
            error = validator.validate_required(
                operation="get_object",
                provided_params={"bucket": "my-bucket", "key": "my-key"}
            )
            if error:
                return error
        """
        required = self.operation_requirements.get(operation, [])
        for param in required:
            value = provided_params.get(param)
            if value is None or (isinstance(value, str) and not value):
                return validation_error(
                    f"Missing required {param} for {operation}",
                    field=param,
                    details={
                        "operation": operation,
                        "required_parameters": required,
                    },
                )
        return None

    def get_required_params(self, operation: str) -> List[str]:
        """Get list of required parameters for an operation.
        
        Args:
            operation: Operation name
            
        Returns:
            List of required parameter names
        """
        return self.operation_requirements.get(operation, [])

    @staticmethod
    def validate_required_for_operation(
        operation: str,
        operation_requirements: Dict[str, List[str]],
        provided_params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Static method to validate parameters without creating an instance.
        
        Args:
            operation: Operation being performed
            operation_requirements: Dict mapping operations to required parameter names
            provided_params: Dict of provided parameters
            
        Returns:
            Error dict if validation fails, None if valid
            
        Example:
            REQUIREMENTS = {
                "list_buckets": ["project_id"],
                "get_object": ["bucket", "key"],
            }
            
            error = ParameterValidator.validate_required_for_operation(
                operation="get_object",
                operation_requirements=REQUIREMENTS,
                provided_params={"bucket": "my-bucket", "key": "my-key"}
            )
            if error:
                return error
        """
        required = operation_requirements.get(operation, [])
        for param in required:
            value = provided_params.get(param)
            if value is None or (isinstance(value, str) and not value):
                return validation_error(
                    f"Missing required {param} for {operation}",
                    field=param,
                    details={
                        "operation": operation,
                        "required_parameters": required,
                    },
                )
        return None
