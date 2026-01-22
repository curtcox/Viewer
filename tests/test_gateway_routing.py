"""Tests for gateway routing module."""

import pytest
from reference.templates.servers.definitions.gateway_lib.routing import (
    Route,
    GatewayRouter,
    create_gateway_router,
)


class TestRoute:
    """Tests for Route pattern matching."""
    
    def test_empty_pattern_matches_empty_path(self):
        route = Route("", lambda: "matched")
        assert route.match("") == {}
    
    def test_empty_pattern_does_not_match_non_empty_path(self):
        route = Route("", lambda: "matched")
        assert route.match("foo") is None
    
    def test_exact_string_match(self):
        route = Route("foo", lambda: "matched")
        assert route.match("foo") == {}
    
    def test_exact_string_no_match(self):
        route = Route("foo", lambda: "matched")
        assert route.match("bar") is None
    
    def test_exact_multi_segment_match(self):
        route = Route("foo/bar", lambda: "matched")
        assert route.match("foo/bar") == {}
    
    def test_exact_multi_segment_no_match(self):
        route = Route("foo/bar", lambda: "matched")
        assert route.match("foo/baz") is None
    
    def test_single_variable_capture(self):
        route = Route("{var}", lambda: "matched")
        result = route.match("value")
        assert result == {"var": "value"}
    
    def test_multiple_variable_capture(self):
        route = Route("{var1}/{var2}", lambda: "matched")
        result = route.match("value1/value2")
        assert result == {"var1": "value1", "var2": "value2"}
    
    def test_mixed_literal_and_variable(self):
        route = Route("foo/{var}/bar", lambda: "matched")
        result = route.match("foo/value/bar")
        assert result == {"var": "value"}
    
    def test_greedy_path_variable(self):
        route = Route("{var:path}", lambda: "matched")
        result = route.match("a/b/c")
        assert result == {"var": "a/b/c"}
    
    def test_greedy_path_variable_single_segment(self):
        route = Route("{var:path}", lambda: "matched")
        result = route.match("single")
        assert result == {"var": "single"}
    
    def test_greedy_path_variable_empty(self):
        route = Route("{var:path}", lambda: "matched")
        result = route.match("")
        assert result == {"var": ""}
    
    def test_mixed_literal_and_greedy_path(self):
        route = Route("test/{path:path}/as/{server}", lambda: "matched")
        result = route.match("test/foo/bar/baz/as/myserver")
        assert result == {"path": "foo/bar/baz", "server": "myserver"}
    
    def test_greedy_with_trailing_segments(self):
        route = Route("test/{path:path}/as/{server}/{rest:path}", lambda: "matched")
        result = route.match("test/foo/bar/as/myserver/extra/stuff")
        assert result == {"path": "foo/bar", "server": "myserver", "rest": "extra/stuff"}
    
    def test_segment_count_mismatch(self):
        route = Route("foo/bar", lambda: "matched")
        assert route.match("foo") is None
        assert route.match("foo/bar/baz") is None
    
    def test_variable_name_extraction_from_typed_var(self):
        """Test that {var:path} extracts 'var' as the parameter name."""
        route = Route("{myvar:path}", lambda: "matched")
        result = route.match("some/path")
        assert result == {"myvar": "some/path"}


class TestGatewayRouter:
    """Tests for GatewayRouter."""
    
    def test_first_match_wins(self):
        router = GatewayRouter()
        router.add_route("foo", lambda: "first")
        router.add_route("foo", lambda: "second")
        
        result = router.route("foo")
        assert result == "first"
    
    def test_route_with_captured_params(self):
        def handler(**kwargs):
            return kwargs
        
        router = GatewayRouter()
        router.add_route("{server}/{path:path}", handler)
        
        result = router.route("myserver/foo/bar", extra="value")
        assert result == {"server": "myserver", "path": "foo/bar", "extra": "value"}
    
    def test_route_strips_leading_trailing_slashes(self):
        router = GatewayRouter()
        router.add_route("foo", lambda: "matched")
        
        assert router.route("/foo/") == "matched"
        assert router.route("foo") == "matched"
    
    def test_route_no_match_raises_error(self):
        router = GatewayRouter()
        router.add_route("foo", lambda: "matched")
        
        with pytest.raises(ValueError, match="No route matched path"):
            router.route("bar")
    
    def test_multiple_routes_in_order(self):
        router = GatewayRouter()
        router.add_route("", lambda: "empty")
        router.add_route("foo", lambda: "foo")
        router.add_route("{var}", lambda var: f"var:{var}")
        
        assert router.route("") == "empty"
        assert router.route("foo") == "foo"
        assert router.route("bar") == "var:bar"


class TestCreateGatewayRouter:
    """Tests for create_gateway_router factory."""
    
    def test_creates_router_with_all_routes(self):
        handlers = {
            "instruction": lambda: "instruction",
            "request_form": lambda: "request_form",
            "response_form": lambda: "response_form",
            "meta": lambda server: f"meta:{server}",
            "meta_test": lambda test_path, server: f"meta_test:{test_path}:{server}",
            "test": lambda test_path, server, rest="": f"test:{test_path}:{server}:{rest}",
            "gateway_request": lambda server, rest="": f"gateway:{server}:{rest}",
        }
        
        router = create_gateway_router(handlers)
        
        # Test reserved routes
        assert router.route("") == "instruction"
        assert router.route("request") == "request_form"
        assert router.route("response") == "response_form"
    
    def test_reserved_routes_shadow_server_names(self):
        """Servers named 'meta', 'request', 'response', or 'test' are shadowed."""
        handlers = {
            "instruction": lambda: "instruction",
            "request_form": lambda: "REQUEST_FORM",
            "response_form": lambda: "response_form",
            "meta": lambda server: f"META:{server}",
            "meta_test": lambda test_path, server: f"meta_test:{test_path}:{server}",
            "test": lambda test_path, server, rest="": f"TEST:{test_path}:{server}:{rest}",
            "gateway_request": lambda server, rest="": f"gateway:{server}:{rest}",
        }
        
        router = create_gateway_router(handlers)
        
        # "request" matches request_form, not gateway_request with server="request"
        assert router.route("request") == "REQUEST_FORM"
        
        # "meta" without additional path matches meta handler (which expects server param)
        # This will fail because meta handler expects a server parameter
        # In actual usage, meta/{server} requires a server name
        # So "meta" alone would not match meta/{server} pattern
        
        # "meta/foo" matches meta handler
        assert router.route("meta/foo") == "META:foo"
    
    def test_meta_routes_order(self):
        """Meta test pattern checked before general meta."""
        handlers = {
            "instruction": lambda: "instruction",
            "request_form": lambda: "request_form",
            "response_form": lambda: "response_form",
            "meta": lambda server: f"meta:{server}",
            "meta_test": lambda test_path, server: f"meta_test:{test_path}:{server}",
            "test": lambda test_path, server, rest="": f"test:{test_path}:{server}:{rest}",
            "gateway_request": lambda server, rest="": f"gateway:{server}:{rest}",
        }
        
        router = create_gateway_router(handlers)
        
        # General meta
        assert router.route("meta/myserver") == "meta:myserver"
        
        # Test meta (more specific pattern)
        assert router.route("meta/test/foo/bar/as/myserver") == "meta_test:foo/bar:myserver"
    
    def test_test_routes_with_and_without_rest(self):
        """Test routes handle both with and without rest path."""
        handlers = {
            "instruction": lambda: "instruction",
            "request_form": lambda: "request_form",
            "response_form": lambda: "response_form",
            "meta": lambda server: f"meta:{server}",
            "meta_test": lambda test_path, server: f"meta_test:{test_path}:{server}",
            "test": lambda test_path, server, rest="": f"test:{test_path}:{server}:{rest}",
            "gateway_request": lambda server, rest="": f"gateway:{server}:{rest}",
        }
        
        router = create_gateway_router(handlers)
        
        # Without rest
        assert router.route("test/foo/bar/as/myserver") == "test:foo/bar:myserver:"
        
        # With rest
        assert router.route("test/foo/bar/as/myserver/extra/path") == "test:foo/bar:myserver:extra/path"
    
    def test_gateway_request_routes(self):
        """Gateway request routes handle server with and without path."""
        handlers = {
            "instruction": lambda: "instruction",
            "request_form": lambda: "request_form",
            "response_form": lambda: "response_form",
            "meta": lambda server: f"meta:{server}",
            "meta_test": lambda test_path, server: f"meta_test:{test_path}:{server}",
            "test": lambda test_path, server, rest="": f"test:{test_path}:{server}:{rest}",
            "gateway_request": lambda server, rest="": f"gateway:{server}:{rest}",
        }
        
        router = create_gateway_router(handlers)
        
        # Without rest
        assert router.route("myserver") == "gateway:myserver:"
        
        # With rest
        assert router.route("myserver/some/path") == "gateway:myserver:some/path"
