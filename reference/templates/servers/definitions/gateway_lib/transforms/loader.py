"""Transform loading and compilation.

This module handles loading transform functions from CIDs and compiling them
into callable Python functions.

Design decisions:
- No caching (always load fresh)
- No sandboxing (full Python access)
- No timeouts (unlimited execution)
- Loads from database or filesystem (for development)
"""

import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger('gateway')


class TransformLoader:
    """Loads and compiles transform functions (no caching).
    
    Resolution strategy:
    1. Try filesystem path (for development)
    2. Try database CID lookup (primary storage)
    
    No caching - always loads fresh to ensure latest content.
    No sandboxing - transforms run with full Python access.
    """
    
    def __init__(self, cid_resolver):
        """Initialize transform loader.
        
        Args:
            cid_resolver: CIDResolver instance for resolving CIDs
        """
        self.cid_resolver = cid_resolver
    
    def load_transform(self, cid: str, context: dict) -> Optional[Callable]:
        """Load and compile a transform function from a CID.
        
        Args:
            cid: CID identifier or file path
            context: Server execution context (not currently used but reserved)
            
        Returns:
            Compiled transform function or None if not found
            
        Note: No caching - always loads fresh content
        """
        try:
            # Try direct file path first (for development)
            if isinstance(cid, str) and Path(cid).exists():
                with open(cid, "r", encoding="utf-8") as f:
                    source = f.read()
                return self.compile_transform(source)
            
            # Try to load from CID store via resolver
            source = self.cid_resolver.resolve(cid, as_bytes=False)
            if source:
                return self.compile_transform(source)
                
        except Exception as e:
            logger.error("Failed to load transform from CID %s: %s", cid, e)
        
        return None
    
    def compile_transform(self, source: str) -> Optional[Callable]:
        """Compile transform source into a callable function.
        
        Args:
            source: Python source code containing transform function
            
        Returns:
            Callable transform function or None if not found
            
        Note: No sandboxing - full Python access with __builtins__
        """
        # Create a namespace for execution
        namespace = {"__builtins__": __builtins__}
        
        # Execute the source (no sandboxing)
        exec(source, namespace)
        
        # Look for transform functions (prefer transform_request, fallback to transform_response)
        for name in ("transform_request", "transform_response"):
            if name in namespace and callable(namespace[name]):
                return namespace[name]
        
        return None
