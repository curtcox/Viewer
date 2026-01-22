"""Transform validation.

This module validates transform source code for syntax and required functions.

Design decisions:
- Validation at load time (not runtime)
- Checks syntax and function signatures
- Returns detailed error messages for debugging
"""

import ast
import logging
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger('gateway')


class TransformValidator:
    """Validates transform source code."""
    
    def __init__(self, cid_resolver):
        """Initialize transform validator.
        
        Args:
            cid_resolver: CIDResolver instance for resolving CIDs
        """
        self.cid_resolver = cid_resolver
    
    def load_and_validate_transform(
        self, 
        cid: str, 
        expected_fn_name: str, 
        context: dict
    ) -> Tuple[Optional[str], Optional[str], List[str]]:
        """Load transform source and validate it.
        
        Args:
            cid: CID identifier or file path
            expected_fn_name: Expected function name (transform_request or transform_response)
            context: Server execution context (not currently used but reserved)
            
        Returns:
            Tuple of (source, error, warnings) where:
            - source: Transform source code or None if not found
            - error: Error message or None if valid
            - warnings: List of warning messages
        """
        source = None
        warnings = []
        
        try:
            # Try file path first (for development)
            if isinstance(cid, str) and Path(cid).exists():
                with open(cid, "r", encoding="utf-8") as f:
                    source = f.read()
            
            # Try to load from CID store via resolver
            if not source:
                source = self.cid_resolver.resolve(cid, as_bytes=False)
            
            if not source:
                return None, f"Transform not found at CID: {cid}", []
            
            # Syntax validation
            try:
                tree = ast.parse(source)
            except SyntaxError as e:
                return source, f"Syntax error at line {e.lineno}: {e.msg}", []
            
            # Check for expected function
            function_found = False
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == expected_fn_name:
                    function_found = True
                    # Check signature
                    args = node.args
                    if len(args.args) < 2:
                        warnings.append(
                            f"Function {expected_fn_name} should have at least 2 parameters "
                            f"(request_details, context)"
                        )
                    break
            
            if not function_found:
                return source, f"Missing required function: {expected_fn_name}", []
            
            return source, None, warnings
            
        except Exception as e:
            return source, f"Validation error: {str(e)}", []
    
    def validate_direct_response(self, direct_response: dict) -> Tuple[bool, Optional[str]]:
        """Validate a direct response dict from request transform.
        
        Args:
            direct_response: Direct response dict to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(direct_response, dict):
            return False, "Direct response must be a dict"
        
        # 'output' is required (can be str or bytes, but must be present)
        if "output" not in direct_response:
            return False, "Direct response must contain 'output' key"
        
        output = direct_response.get("output")
        if output is not None and not isinstance(output, (str, bytes)):
            return False, f"Direct response 'output' must be str or bytes, got {type(output).__name__}"
        
        # 'content_type' is optional but must be string if present
        content_type = direct_response.get("content_type")
        if content_type is not None and not isinstance(content_type, str):
            return False, f"Direct response 'content_type' must be str, got {type(content_type).__name__}"
        
        # 'status_code' is optional but must be int if present
        status_code = direct_response.get("status_code")
        if status_code is not None and not isinstance(status_code, int):
            return False, f"Direct response 'status_code' must be int, got {type(status_code).__name__}"
        
        return True, None
