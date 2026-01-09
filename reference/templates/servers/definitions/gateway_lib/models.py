"""Data classes for gateway server.

These classes provide type-safe data structures for gateway operations,
replacing dictionaries with explicit, well-documented types.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class GatewayConfig:
    """Configuration for a gateway server.
    
    Attributes:
        name: Name of the gateway server
        request_transform_cid: CID of the request transform function
        response_transform_cid: CID of the response transform function
        templates: Mapping of template names to their CIDs
        target_url: Optional target URL (defaults to /{name})
        custom_error_template_cid: Optional CID for custom error page
    """
    name: str
    request_transform_cid: Optional[str] = None
    response_transform_cid: Optional[str] = None
    templates: Dict[str, str] = field(default_factory=dict)
    target_url: Optional[str] = None
    custom_error_template_cid: Optional[str] = None


@dataclass
class RequestDetails:
    """Details of an incoming gateway request.
    
    Can be constructed from various sources:
    - Flask request context (HTTP)
    - Direct function parameters (programmatic)
    - CLI arguments
    - Batch processing data
    
    This decoupling allows gateway to work without Flask/HTTP layer.
    
    Attributes:
        path: Request path
        method: HTTP method (GET, POST, etc.)
        query_string: URL query string
        headers: Request headers (without cookies)
        json: Parsed JSON body if available
        data: Raw request body
        url: Full URL if available
    """
    path: str
    method: str = "GET"
    query_string: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    json: Optional[Any] = None
    data: Optional[str] = None
    url: Optional[str] = None

    @classmethod
    def from_flask_request(cls, flask_request, rest_path: str) -> 'RequestDetails':
        """Build RequestDetails from Flask request object.
        
        Args:
            flask_request: Flask request object
            rest_path: The rest of the path after gateway prefix
            
        Returns:
            RequestDetails instance
        """
        try:
            json_body = flask_request.get_json(silent=True)
        except Exception:
            json_body = None

        return cls(
            path=rest_path,
            method=flask_request.method,
            query_string=flask_request.query_string.decode("utf-8"),
            headers={k: v for k, v in flask_request.headers if k.lower() != "cookie"},
            json=json_body,
            data=flask_request.get_data(as_text=True),
            url=flask_request.url
        )

    @classmethod
    def from_params(cls, path: str, method: str = "GET", **kwargs) -> 'RequestDetails':
        """Build RequestDetails from direct parameters (non-HTTP invocation).
        
        Args:
            path: Request path
            method: HTTP method
            **kwargs: Additional optional parameters
            
        Returns:
            RequestDetails instance
        """
        return cls(path=path, method=method, **kwargs)


@dataclass
class ResponseDetails:
    """Details of a response from target server or direct response.
    
    Attributes:
        status_code: HTTP status code
        headers: Response headers
        content: Raw response content as bytes
        text: Response content as text
        json: Parsed JSON response if applicable
        request_path: Original request path
        source: Source of response ("server", "test_server", or "request_transform")
        is_direct_response: True if this was a direct response from request transform
    """
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    json: Optional[Any] = None
    request_path: str = ""
    source: str = "server"
    is_direct_response: bool = False


@dataclass
class TransformResult:
    """Result from a transform function.
    
    Attributes:
        output: Transform output (string or bytes)
        content_type: MIME type of the output
        status_code: HTTP status code
        headers: Optional additional headers
    """
    output: str | bytes
    content_type: str = "text/plain"
    status_code: int = 200
    headers: Optional[Dict[str, str]] = None


@dataclass
class Target:
    """Internal target for gateway execution.
    
    Attributes:
        mode: Target mode (currently only "internal" is supported)
        url: Target URL (must be internal path starting with /)
    """
    mode: str
    url: str

    def validate(self):
        """Validate target configuration.
        
        Raises:
            ValueError: If target configuration is invalid
        """
        if self.mode != "internal":
            raise ValueError(f"Unsupported target mode: {self.mode}")
        if not self.url.startswith("/"):
            raise ValueError("Gateway target must be an internal path")


@dataclass
class DirectResponse:
    """Direct response from request transform (bypasses target execution).
    
    Attributes:
        output: Response content (string or bytes)
        content_type: MIME type of the response
        status_code: HTTP status code
        headers: Optional additional headers
    """
    output: str | bytes
    content_type: str = "text/html"
    status_code: int = 200
    headers: Optional[Dict[str, str]] = None
