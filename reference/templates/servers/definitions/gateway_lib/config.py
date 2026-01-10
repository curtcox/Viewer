"""Gateway configuration loading and validation.

This module handles loading gateway configurations from various sources
and validating them at load time.

Design decisions:
- Hot-reloadable (no caching)
- Validation at load time
- Multiple source formats (dict, JSON string, CID)
"""

import json
import logging
from typing import Dict

logger = logging.getLogger('gateway')


class ConfigLoader:
    """Loads gateway configurations (hot-reloadable, no caching)."""
    
    def __init__(self, cid_resolver):
        """Initialize config loader.
        
        Args:
            cid_resolver: CIDResolver instance for resolving CIDs
        """
        self.cid_resolver = cid_resolver
    
    def load_gateways(self, context: dict) -> Dict:
        """Load gateway configurations from context variables.
        
        Args:
            context: Server execution context with variables, secrets, servers
            
        Returns:
            Dictionary of gateway configurations keyed by gateway name
            
        Note: No caching - always loads fresh to support hot-reloading
        """
        try:
            # Try to get gateways from context variables
            # Context is a dict with {"variables": {...}, "secrets": {...}, "servers": {...}}
            gateways_value = None
            if context and isinstance(context, dict):
                variables = context.get("variables", {})
                if isinstance(variables, dict):
                    gateways_value = variables.get("gateways")
            
            if gateways_value:
                if isinstance(gateways_value, dict):
                    return gateways_value
                if isinstance(gateways_value, str):
                    # Try to parse as JSON first
                    try:
                        return json.loads(gateways_value)
                    except json.JSONDecodeError:
                        # Value might be a CID - try to resolve it
                        if gateways_value.startswith("AAAAA"):
                            cid_content = self.cid_resolver.resolve(gateways_value, as_bytes=False)
                            if cid_content:
                                return json.loads(cid_content)
            
            # Try to resolve from named value resolver
            from server_execution.request_parsing import resolve_named_value
            
            # Build base_args with context for named value resolution
            base_args = {}
            if context and isinstance(context, dict):
                base_args["context"] = context
            
            value = resolve_named_value("gateways", base_args)
            if value:
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        # Value might be a CID - try to resolve it
                        if value.startswith("AAAAA"):
                            cid_content = self.cid_resolver.resolve(value, as_bytes=False)
                            if cid_content:
                                return json.loads(cid_content)
            
        except Exception as e:
            logger.warning("Failed to load gateways: %s", e)
        
        return {}
