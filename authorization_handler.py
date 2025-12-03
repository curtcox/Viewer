"""Authorization handler for Flask requests."""

from flask import Response, jsonify, render_template, request
from werkzeug.exceptions import Forbidden, Unauthorized

from authorization import AuthorizationResult


def create_authorization_error_response(result: AuthorizationResult) -> Response:
    """Create an appropriate error response based on the authorization result.
    
    This function generates responses in the appropriate format (HTML, JSON, text)
    based on the request's Accept header.
    
    Args:
        result: The authorization result containing status code and message.
    
    Returns:
        Flask Response object with the appropriate content type and status code.
    """
    if not result.allowed:
        status_code = result.status_code
        message = result.message
        
        # Determine response format based on Accept header
        accept_header = request.headers.get('Accept', 'text/html')
        
        # Check for JSON request
        if 'application/json' in accept_header or request.path.startswith('/api/'):
            response = jsonify({
                'error': 'Authorization failed',
                'status': status_code,
                'message': message
            })
            response.status_code = status_code
            return response
        
        # Check for plain text request
        if 'text/plain' in accept_header and 'text/html' not in accept_header:
            return Response(
                f"Error {status_code}: {message}\n",
                status=status_code,
                mimetype='text/plain'
            )
        
        # Default to HTML response
        # Use Flask's built-in error templates or create custom ones
        if status_code == 401:
            error = Unauthorized(message)
            response_html = render_template('401.html', error=error)
            return Response(response_html, status=401, mimetype='text/html')
        elif status_code == 403:
            error = Forbidden(message)
            response_html = render_template('403.html', error=error)
            return Response(response_html, status=403, mimetype='text/html')
        else:
            # Fallback for other status codes
            return Response(
                f"<html><body><h1>Error {status_code}</h1><p>{message}</p></body></html>",
                status=status_code,
                mimetype='text/html'
            )
    
    # This shouldn't happen, but return an error if called with allowed=True
    raise ValueError(
        "create_authorization_error_response should only be called when "
        "authorization is denied (allowed=False)"
    )


__all__ = ['create_authorization_error_response']
