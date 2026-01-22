"""Gateway middleware system.

Provides extensibility points for gateway requests without modifying core logic.
Middleware can hook into three points:
1. before_request - Called before request processing
2. after_request - Called after response generation
3. on_error - Called when an error occurs
"""

from typing import Any


class Middleware:
    """Base class for gateway middleware.
    
    Subclass this to create custom middleware that can:
    - Modify requests before they are processed
    - Modify responses before they are returned
    - Handle errors and add custom error handling
    """
    
    def before_request(self, context: dict) -> dict:
        """Called before request transform.
        
        Args:
            context: Request context dict
        
        Returns:
            Modified context dict (or original if no changes)
        """
        return context
    
    def after_request(self, result: Any, context: dict) -> Any:
        """Called after response generation.
        
        Args:
            result: Response result from handler
            context: Request context dict
        
        Returns:
            Modified result (or original if no changes)
        """
        return result
    
    def on_error(self, error: Exception, context: dict):
        """Called when an error occurs.
        
        Args:
            error: The exception that was raised
            context: Request context dict
        """
        pass


class MiddlewareChain:
    """Manages middleware execution in correct order.
    
    Middleware is executed in:
    - before_request: Added order (first to last)
    - after_request: Reverse order (last to first)
    - on_error: Added order (first to last)
    """
    
    def __init__(self):
        """Initialize empty middleware chain."""
        self.middleware = []
    
    def add(self, middleware: Middleware):
        """Add middleware to the chain.
        
        Args:
            middleware: Middleware instance to add
        """
        self.middleware.append(middleware)
    
    def execute_before_request(self, context: dict) -> dict:
        """Execute all before_request middleware.
        
        Args:
            context: Request context dict
        
        Returns:
            Modified context after all middleware
        """
        for mw in self.middleware:
            context = mw.before_request(context)
        return context
    
    def execute_after_request(self, result: Any, context: dict) -> Any:
        """Execute all after_request middleware in reverse order.
        
        Args:
            result: Response result from handler
            context: Request context dict
        
        Returns:
            Modified result after all middleware
        """
        for mw in reversed(self.middleware):
            result = mw.after_request(result, context)
        return result
    
    def execute_on_error(self, error: Exception, context: dict):
        """Execute all on_error middleware.
        
        Args:
            error: The exception that was raised
            context: Request context dict
        """
        for mw in self.middleware:
            mw.on_error(error, context)
