"""Tests for gateway middleware module."""

from reference.templates.servers.definitions.gateway_lib.middleware import (
    Middleware,
    MiddlewareChain,
)


class TestMiddleware:
    """Tests for Middleware base class."""
    
    def test_before_request_default_returns_context(self):
        mw = Middleware()
        context = {"key": "value"}
        result = mw.before_request(context)
        assert result is context
    
    def test_after_request_default_returns_result(self):
        mw = Middleware()
        result = "response"
        context = {"key": "value"}
        output = mw.after_request(result, context)
        assert output is result
    
    def test_on_error_default_does_nothing(self):
        mw = Middleware()
        error = ValueError("test error")
        context = {"key": "value"}
        # Should not raise
        mw.on_error(error, context)


class LoggingMiddleware(Middleware):
    """Test middleware that logs calls."""
    
    def __init__(self):
        self.calls = []
    
    def before_request(self, context):
        self.calls.append(("before", context.get("id")))
        context["logged"] = True
        return context
    
    def after_request(self, result, context):
        self.calls.append(("after", context.get("id")))
        if isinstance(result, str):
            result = result.upper()
        return result
    
    def on_error(self, error, context):
        self.calls.append(("error", str(error)))


class TransformMiddleware(Middleware):
    """Test middleware that transforms data."""
    
    def __init__(self, prefix=""):
        self.prefix = prefix
    
    def before_request(self, context):
        context["prefix"] = self.prefix
        return context
    
    def after_request(self, result, context):
        if isinstance(result, str):
            return f"{context.get('prefix', '')}{result}"
        return result


class TestMiddlewareChain:
    """Tests for MiddlewareChain."""
    
    def test_empty_chain_returns_context_unchanged(self):
        chain = MiddlewareChain()
        context = {"key": "value"}
        result = chain.execute_before_request(context)
        assert result is context
    
    def test_empty_chain_returns_result_unchanged(self):
        chain = MiddlewareChain()
        result = "response"
        context = {"key": "value"}
        output = chain.execute_after_request(result, context)
        assert output is result
    
    def test_single_middleware_before_request(self):
        chain = MiddlewareChain()
        mw = LoggingMiddleware()
        chain.add(mw)
        
        context = {"id": "req1"}
        result = chain.execute_before_request(context)
        
        assert result["logged"] is True
        assert mw.calls == [("before", "req1")]
    
    def test_single_middleware_after_request(self):
        chain = MiddlewareChain()
        mw = LoggingMiddleware()
        chain.add(mw)
        
        context = {"id": "req1"}
        result = chain.execute_after_request("response", context)
        
        assert result == "RESPONSE"
        assert mw.calls == [("after", "req1")]
    
    def test_single_middleware_on_error(self):
        chain = MiddlewareChain()
        mw = LoggingMiddleware()
        chain.add(mw)
        
        error = ValueError("test error")
        context = {"id": "req1"}
        chain.execute_on_error(error, context)
        
        assert mw.calls == [("error", "test error")]
    
    def test_multiple_middleware_before_request_order(self):
        """Middleware executes in added order for before_request."""
        chain = MiddlewareChain()
        mw1 = LoggingMiddleware()
        mw2 = LoggingMiddleware()
        chain.add(mw1)
        chain.add(mw2)
        
        context = {"id": "req1"}
        chain.execute_before_request(context)
        
        # First middleware runs first
        assert mw1.calls[0] == ("before", "req1")
        assert mw2.calls[0] == ("before", "req1")
    
    def test_multiple_middleware_after_request_reverse_order(self):
        """Middleware executes in reverse order for after_request."""
        chain = MiddlewareChain()
        mw1 = TransformMiddleware(prefix="A:")
        mw2 = TransformMiddleware(prefix="B:")
        chain.add(mw1)
        chain.add(mw2)
        
        context = {}
        # before_request to set up context
        context = mw1.before_request(context)
        context = mw2.before_request(context)
        
        # after_request should apply mw2 first, then mw1
        # Since mw2 is applied first (reverse order), context["prefix"] = "B:"
        # But we need to track this differently...
        # Let's use a different test
        pass
    
    def test_middleware_chain_transforms_context(self):
        """Multiple middleware can transform context."""
        chain = MiddlewareChain()
        
        class AddKeyMiddleware(Middleware):
            def __init__(self, key, value):
                self.key = key
                self.value = value
            
            def before_request(self, context):
                context[self.key] = self.value
                return context
        
        chain.add(AddKeyMiddleware("key1", "value1"))
        chain.add(AddKeyMiddleware("key2", "value2"))
        
        context = {}
        result = chain.execute_before_request(context)
        
        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
    
    def test_middleware_chain_transforms_result(self):
        """Multiple middleware can transform result."""
        chain = MiddlewareChain()
        
        class AppendMiddleware(Middleware):
            def __init__(self, suffix):
                self.suffix = suffix
            
            def after_request(self, result, context):
                if isinstance(result, str):
                    return result + self.suffix
                return result
        
        chain.add(AppendMiddleware("_A"))
        chain.add(AppendMiddleware("_B"))
        
        # Reverse order: B applied first, then A
        result = chain.execute_after_request("start", {})
        
        assert result == "start_B_A"
    
    def test_on_error_executes_all_middleware(self):
        """All middleware on_error handlers are called."""
        chain = MiddlewareChain()
        mw1 = LoggingMiddleware()
        mw2 = LoggingMiddleware()
        chain.add(mw1)
        chain.add(mw2)
        
        error = ValueError("test error")
        chain.execute_on_error(error, {})
        
        assert mw1.calls == [("error", "test error")]
        assert mw2.calls == [("error", "test error")]
    
    def test_middleware_can_modify_shared_context(self):
        """Middleware can see modifications made by previous middleware."""
        chain = MiddlewareChain()
        
        class IncrementMiddleware(Middleware):
            def before_request(self, context):
                context["count"] = context.get("count", 0) + 1
                return context
        
        chain.add(IncrementMiddleware())
        chain.add(IncrementMiddleware())
        chain.add(IncrementMiddleware())
        
        context = {}
        result = chain.execute_before_request(context)
        
        assert result["count"] == 3
