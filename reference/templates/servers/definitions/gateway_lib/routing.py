"""Gateway routing module.

Provides simple pattern-based routing for gateway requests.
Uses first-match-wins strategy with support for:
- Exact string matches: "foo"
- Single segment variables: "{var}"
- Greedy path variables: "{var:path}"

Reserved routes (checked first):
- "" (empty) -> instruction page
- "request" -> request form
- "response" -> response form
- "meta/<server>" -> meta page
- "meta/test/<test_path>/as/<server>" -> meta test page
- "test/<test_path>/as/<server>/<rest>" -> test mode

Gateway server routes (checked last):
- "<server>/<rest>" -> gateway request with path
- "<server>" -> gateway request without path

Important: Servers named "meta", "request", "response", or "test" will be
shadowed by reserved routes and need aliases to be accessible via gateway.
"""

from typing import Optional, Callable, Any


class Route:
    """A single route with pattern and handler."""
    
    def __init__(self, pattern: str, handler: Callable):
        """Initialize a route.
        
        Args:
            pattern: Route pattern (e.g., "", "foo", "{var}", "{var:path}")
            handler: Callable that handles matched requests
        """
        self.pattern = pattern
        self.handler = handler
        self._parse_pattern()
    
    def _parse_pattern(self):
        """Parse pattern into parts for matching."""
        if self.pattern == "":
            self.parts = []
            self.greedy_indices = []
            return
        
        self.parts = self.pattern.split("/")
        # Find all greedy path variables
        self.greedy_indices = [
            i for i, part in enumerate(self.parts)
            if part.startswith("{") and ":path}" in part
        ]
    
    def match(self, path: str) -> Optional[dict]:
        """Try to match path against this route's pattern.
        
        Args:
            path: Request path to match (without leading/trailing slashes)
        
        Returns:
            Dict of captured variables if match, None otherwise
        """
        if self.pattern == "":
            return {} if path == "" else None
        
        path_parts = path.split("/") if path else []
        
        # Handle patterns with greedy path variables
        if self.greedy_indices:
            return self._match_with_greedy(path_parts)
        
        # Exact segment count match (no greedy variables)
        if len(self.parts) != len(path_parts):
            return None
        
        params = {}
        for p_part, path_part in zip(self.parts, path_parts):
            if p_part.startswith("{") and p_part.endswith("}"):
                var_name = p_part[1:-1].split(":")[0]
                params[var_name] = path_part
            elif p_part != path_part:
                return None
        
        return params
    
    def _match_with_greedy(self, path_parts: list) -> Optional[dict]:
        """Match pattern with greedy path variables.
        
        Algorithm:
        1. Find literal segments that must match
        2. Match literal segments in path
        3. Allocate remaining segments to greedy variables
        """
        # For patterns like "test/{path:path}/as/{server}"
        # We need to find "as" as an anchor and work backwards
        
        if not self.greedy_indices:
            return None
        
        # Simple case: single greedy at the end
        if len(self.greedy_indices) == 1 and self.greedy_indices[0] == len(self.parts) - 1:
            # Need at least as many parts as non-greedy pattern parts
            min_parts = len(self.parts) - 1
            if len(path_parts) < min_parts:
                return None
            
            params = {}
            # Match non-greedy parts
            for i in range(min_parts):
                p_part = self.parts[i]
                if p_part.startswith("{") and p_part.endswith("}"):
                    var_name = p_part[1:-1].split(":")[0]
                    params[var_name] = path_parts[i]
                elif p_part != path_parts[i]:
                    return None
            
            # Capture remaining path in greedy variable
            greedy_var = self.parts[-1][1:-1].split(":")[0]
            params[greedy_var] = "/".join(path_parts[min_parts:])
            return params
        
        # Complex case: greedy variables with trailing segments
        # Pattern: "test/{path:path}/as/{server}" or "test/{path:path}/as/{server}/{rest:path}"
        # Find literal anchors after greedy variables
        params = {}
        path_idx = 0
        
        for pattern_idx, p_part in enumerate(self.parts):
            if pattern_idx in self.greedy_indices:
                # This is a greedy variable - need to find the next anchor
                var_name = p_part[1:-1].split(":")[0]
                
                # Find next non-variable pattern part (anchor)
                anchor_pattern_idx = None
                for j in range(pattern_idx + 1, len(self.parts)):
                    if not (self.parts[j].startswith("{") and self.parts[j].endswith("}")):
                        anchor_pattern_idx = j
                        break
                
                if anchor_pattern_idx is None:
                    # No anchor after this greedy - capture rest of path
                    params[var_name] = "/".join(path_parts[path_idx:])
                    return params
                
                # Find anchor in path
                anchor_literal = self.parts[anchor_pattern_idx]
                try:
                    anchor_path_idx = path_parts.index(anchor_literal, path_idx)
                except ValueError:
                    return None  # Anchor not found in path
                
                # Capture segments between current position and anchor
                params[var_name] = "/".join(path_parts[path_idx:anchor_path_idx])
                path_idx = anchor_path_idx
            
            elif p_part.startswith("{") and p_part.endswith("}"):
                # Regular variable - capture single segment
                if path_idx >= len(path_parts):
                    return None
                var_name = p_part[1:-1].split(":")[0]
                params[var_name] = path_parts[path_idx]
                path_idx += 1
            
            else:
                # Literal segment - must match
                if path_idx >= len(path_parts) or path_parts[path_idx] != p_part:
                    return None
                path_idx += 1
        
        # Check if we consumed all path segments
        if path_idx != len(path_parts):
            return None
        
        return params


class GatewayRouter:
    """Routes gateway requests using first-match-wins strategy.
    
    Routing is scoped to /gateway/ only - does not affect Flask routing elsewhere.
    
    Reserved route patterns (checked first):
    - "" (empty) -> instruction page
    - "request" -> request form
    - "response" -> response form
    - "meta/test/{test_path:path}/as/{server}" -> meta test page
    - "meta/{server}" -> meta page
    - "test/{test_path:path}/as/{server}/{rest:path}" -> test mode with path
    - "test/{test_path:path}/as/{server}" -> test mode without path
    
    Gateway server routes (checked last):
    - "{server}/{rest:path}" -> gateway request with path
    - "{server}" -> gateway request without path
    
    Important: Servers named "meta", "request", "response", or "test" will be
    shadowed by reserved routes and need aliases to be accessible via gateway.
    """
    
    def __init__(self):
        """Initialize router with empty routes."""
        self.routes = []
    
    def add_route(self, pattern: str, handler: Callable):
        """Add a route to the router.
        
        Routes are matched in the order they are added (first-match-wins).
        
        Args:
            pattern: Route pattern
            handler: Handler callable
        """
        self.routes.append(Route(pattern, handler))
    
    def route(self, path: str, **kwargs) -> Any:
        """Match path to handler and execute.
        
        Args:
            path: Request path after /gateway/ prefix (without leading/trailing slashes)
            **kwargs: Additional arguments passed to all handlers
        
        Returns:
            Handler result
        """
        # Strip leading/trailing slashes
        path = path.strip("/")
        
        # Try each route in order (first-match-wins)
        for route in self.routes:
            params = route.match(path)
            if params is not None:
                # Merge captured params with kwargs
                handler_kwargs = {**kwargs, **params}
                return route.handler(**handler_kwargs)
        
        # No match found - this shouldn't happen with proper route setup
        raise ValueError(f"No route matched path: {path}")


def create_gateway_router(handlers: dict) -> GatewayRouter:
    """Create a configured gateway router with all standard routes.
    
    Args:
        handlers: Dict of handler callables with keys:
            - instruction: Instruction page handler
            - request_form: Request form handler
            - response_form: Response form handler
            - meta: Meta page handler
            - meta_test: Meta test page handler
            - test: Test mode handler
            - gateway_request: Gateway request handler
    
    Returns:
        Configured GatewayRouter instance
    """
    router = GatewayRouter()
    
    # Reserved routes (checked first - more specific before general)
    router.add_route("", handlers["instruction"])
    router.add_route("request", handlers["request_form"])
    router.add_route("response", handlers["response_form"])
    
    # Meta routes (test pattern before general meta)
    router.add_route("meta/test/{test_path:path}/as/{server}", handlers["meta_test"])
    router.add_route("meta/{server}", handlers["meta"])
    
    # Test routes (with and without rest path)
    router.add_route("test/{test_path:path}/as/{server}/{rest:path}", handlers["test"])
    router.add_route("test/{test_path:path}/as/{server}", handlers["test"])
    
    # Gateway server routes (checked last)
    router.add_route("{server}/{rest:path}", handlers["gateway_request"])
    router.add_route("{server}", handlers["gateway_request"])
    
    return router
