"""Template loading and resolution.

This module handles loading Jinja2 templates from CIDs and creating
template resolver functions for gateway configurations.

Design decisions:
- Lazy loading (templates loaded on-demand)
- No caching (always load fresh)
- Templates stored as CIDs in gateway config
"""

import logging
from typing import Optional, Tuple, List
from jinja2 import Template, Environment, meta

logger = logging.getLogger('gateway')


class TemplateLoader:
    """Loads and validates Jinja2 templates (lazy, no caching)."""
    
    def __init__(self, cid_resolver, resolve_fn=None):
        """Initialize template loader.
        
        Args:
            cid_resolver: CIDResolver instance for resolving CIDs
            resolve_fn: Optional custom resolve function (for testing)
        """
        self.cid_resolver = cid_resolver
        self._resolve_fn = resolve_fn or (lambda cid, as_bytes: cid_resolver.resolve(cid, as_bytes=as_bytes))
    
    def load_and_validate_template(
        self, 
        cid: str, 
        context: dict
    ) -> Tuple[Optional[str], Optional[str], List[str]]:
        """Load and validate a Jinja template.
        
        Args:
            cid: Template CID to load
            context: Server execution context (not currently used but reserved)
            
        Returns:
            Tuple of (source, error, variables) where:
            - source: Template source code (str) or None if not found
            - error: Error message (str) or None if valid
            - variables: List of detected template variables (list[str])
        """
        try:
            content = self._resolve_fn(cid, as_bytes=False)
            if not content:
                return None, f"Template not found at CID: {cid}", []
            
            # Try to parse as Jinja template
            env = Environment()
            try:
                ast_node = env.parse(content)
                # Extract referenced variables
                variables = sorted(list(meta.find_undeclared_variables(ast_node)))
            except Exception as e:
                return content, f"Jinja syntax error: {e}", []
            
            return content, None, variables
            
        except Exception as e:
            return None, f"Validation error: {e}", []
    
    def create_template_resolver(self, config: dict, context: dict):
        """Create a template resolution function for a gateway config.
        
        Args:
            config: Gateway configuration dict with optional 'templates' key
            context: Server execution context
            
        Returns:
            Function that takes template name and returns Jinja2 Template
        """
        templates_config = config.get("templates", {})
        
        def resolve_template(template_name: str) -> Template:
            """Resolve a template by name from the gateway's templates config.
            
            Args:
                template_name: Name of the template (e.g., "man_page.html")
                
            Returns:
                jinja2.Template object
                
            Raises:
                ValueError: If template not found in config
                LookupError: If template CID cannot be resolved
            """
            if template_name not in templates_config:
                raise ValueError(
                    f"Template '{template_name}' not found in gateway config. "
                    f"Available templates: {list(templates_config.keys())}"
                )
            
            template_cid = templates_config[template_name]
            content = self._resolve_fn(template_cid, as_bytes=False)
            if content is None:
                raise LookupError(f"Could not resolve template CID: {template_cid}")
            
            return Template(content)
        
        return resolve_template
