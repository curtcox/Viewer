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
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('gateway')


class ConfigValidationError(Exception):
    """Raised when gateway configuration is invalid."""
    pass


def validate_gateway_config(gateway_name: str, config: dict) -> Tuple[bool, List[str]]:
    """Validate a single gateway configuration.

    Args:
        gateway_name: Name of the gateway being validated
        config: Gateway configuration dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)

    Example:
        >>> is_valid, errors = validate_gateway_config("man", {
        ...     "request_transform_cid": "/CID1",
        ...     "response_transform_cid": "/CID2"
        ... })
    """
    errors = []

    if not isinstance(config, dict):
        errors.append(f"Gateway '{gateway_name}' config must be a dictionary, got {type(config).__name__}")
        return False, errors

    # Validate transform CIDs if present
    for transform_type in ["request_transform_cid", "response_transform_cid"]:
        if transform_type in config:
            value = config[transform_type]
            if value is not None and not isinstance(value, str):
                errors.append(
                    f"Gateway '{gateway_name}' {transform_type} must be a string or None, "
                    f"got {type(value).__name__}"
                )

    # Validate templates if present
    if "templates" in config:
        templates = config["templates"]
        if not isinstance(templates, dict):
            errors.append(
                f"Gateway '{gateway_name}' templates must be a dictionary, "
                f"got {type(templates).__name__}"
            )
        else:
            for template_name, template_cid in templates.items():
                if not isinstance(template_name, str):
                    errors.append(
                        f"Gateway '{gateway_name}' template name must be string, "
                        f"got {type(template_name).__name__}"
                    )
                if not isinstance(template_cid, str):
                    errors.append(
                        f"Gateway '{gateway_name}' template '{template_name}' CID must be string, "
                        f"got {type(template_cid).__name__}"
                    )

    # Validate target_url if present
    if "target_url" in config:
        target_url = config["target_url"]
        if target_url is not None and not isinstance(target_url, str):
            errors.append(
                f"Gateway '{gateway_name}' target_url must be a string or None, "
                f"got {type(target_url).__name__}"
            )

    # Validate custom_error_template_cid if present
    if "custom_error_template_cid" in config:
        value = config["custom_error_template_cid"]
        if value is not None and not isinstance(value, str):
            errors.append(
                f"Gateway '{gateway_name}' custom_error_template_cid must be a string or None, "
                f"got {type(value).__name__}"
            )

    return len(errors) == 0, errors


def validate_all_gateways(gateways: dict) -> Tuple[bool, Dict[str, List[str]]]:
    """Validate all gateway configurations.

    Args:
        gateways: Dictionary of gateway configs keyed by gateway name

    Returns:
        Tuple of (all_valid, dict_of_errors_by_gateway)

    Example:
        >>> all_valid, errors = validate_all_gateways({
        ...     "man": {"request_transform_cid": "/CID1"},
        ...     "bad": {"request_transform_cid": 123}  # Invalid!
        ... })
        >>> all_valid
        False
        >>> "bad" in errors
        True
    """
    if not isinstance(gateways, dict):
        return False, {"__root__": [f"Gateways must be a dictionary, got {type(gateways).__name__}"]}

    all_errors = {}
    for gateway_name, config in gateways.items():
        is_valid, errors = validate_gateway_config(gateway_name, config)
        if not is_valid:
            all_errors[gateway_name] = errors

    return len(all_errors) == 0, all_errors


class ConfigLoader:
    """Loads gateway configurations (hot-reloadable, no caching)."""
    
    def __init__(self, cid_resolver, validate: bool = True):
        """Initialize config loader.
        
        Args:
            cid_resolver: CIDResolver instance for resolving CIDs
            validate: Whether to validate configs at load time (default: True)
        """
        self.cid_resolver = cid_resolver
        self.validate = validate
    
    def load_gateways(self, context: dict) -> Dict:
        """Load gateway configurations from context variables.
        
        Args:
            context: Server execution context with variables, secrets, servers
            
        Returns:
            Dictionary of gateway configurations keyed by gateway name
            
        Raises:
            ConfigValidationError: If validation is enabled and config is invalid
            
        Note: No caching - always loads fresh to support hot-reloading
        """
        gateways = self._load_raw_gateways(context)

        # Validate if enabled
        if self.validate and gateways:
            is_valid, errors = validate_all_gateways(gateways)
            if not is_valid:
                error_msg = "Gateway configuration validation failed:\n"
                for gateway_name, gateway_errors in errors.items():
                    error_msg += f"\n{gateway_name}:\n"
                    for error in gateway_errors:
                        error_msg += f"  - {error}\n"
                logger.error(error_msg)
                raise ConfigValidationError(error_msg)

        return gateways

    def _load_raw_gateways(self, context: dict) -> Dict:
        """Load raw gateway configs without validation.

        Args:
            context: Server execution context

        Returns:
            Dictionary of gateway configurations
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
