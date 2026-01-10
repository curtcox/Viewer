"""Centralized logging configuration for gateway.

This module provides a single point of configuration for gateway logging,
making it easy to intercept, redirect, or customize logging behavior.
"""

import logging


def get_gateway_logger(name: str = "gateway") -> logging.Logger:
    """Get centralized gateway logger.

    This is the single point where logging can be intercepted and replaced.
    Configure this logger to redirect to custom handlers as needed.

    Args:
        name: Logger name, defaults to "gateway"

    Returns:
        Logger instance configured for gateway use

    Example:
        >>> logger = get_gateway_logger()
        >>> logger.info("Gateway request", extra={
        ...     "gateway": "man",
        ...     "path": "/ls",
        ...     "method": "GET"
        ... })

        >>> # Custom handler setup
        >>> logger = get_gateway_logger()
        >>> handler = logging.StreamHandler()
        >>> handler.setFormatter(logging.Formatter(
        ...     '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ... ))
        >>> logger.addHandler(handler)
        >>> logger.setLevel(logging.INFO)
    """
    return logging.getLogger(name)


def configure_gateway_logging(
    level: int = logging.INFO,
    format_string: str | None = None,
    handler: logging.Handler | None = None
) -> logging.Logger:
    """Configure gateway logging with custom settings.

    Args:
        level: Logging level (e.g., logging.INFO, logging.DEBUG)
        format_string: Optional custom format string
        handler: Optional custom handler (if None, uses StreamHandler)

    Returns:
        Configured logger instance

    Example:
        >>> logger = configure_gateway_logging(
        ...     level=logging.DEBUG,
        ...     format_string='[%(levelname)s] %(message)s'
        ... )
    """
    logger = get_gateway_logger()
    logger.setLevel(level)

    # Use provided handler or create default
    if handler is None:
        handler = logging.StreamHandler()

    # Set format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)

    # Clear existing handlers and add new one
    logger.handlers.clear()
    logger.addHandler(handler)

    return logger


def log_gateway_request(
    logger: logging.Logger,
    gateway: str,
    path: str,
    method: str = "GET",
    **extra_context
):
    """Log a gateway request with structured data.

    Args:
        logger: Logger instance
        gateway: Gateway name
        path: Request path
        method: HTTP method
        **extra_context: Additional context to log
    """
    logger.info(
        f"Gateway request: {gateway} {method} {path}",
        extra={
            "gateway": gateway,
            "path": path,
            "method": method,
            **extra_context
        }
    )


def log_gateway_error(
    logger: logging.Logger,
    gateway: str,
    error_type: str,
    error_message: str,
    exc_info: bool = True,
    **extra_context
):
    """Log a gateway error with structured data.

    Args:
        logger: Logger instance
        gateway: Gateway name
        error_type: Type of error (e.g., "transform_error", "target_error")
        error_message: Error message
        exc_info: Whether to include exception info
        **extra_context: Additional context to log
    """
    logger.error(
        f"Gateway error in {gateway}: {error_type} - {error_message}",
        extra={
            "gateway": gateway,
            "error_type": error_type,
            "error_message": error_message,
            **extra_context
        },
        exc_info=exc_info
    )


def log_transform_execution(
    logger: logging.Logger,
    gateway: str,
    transform_type: str,  # "request" or "response"
    transform_cid: str,
    **extra_context
):
    """Log transform execution.

    Args:
        logger: Logger instance
        gateway: Gateway name
        transform_type: Type of transform ("request" or "response")
        transform_cid: CID of transform being executed
        **extra_context: Additional context to log
    """
    logger.debug(
        f"Executing {transform_type} transform for {gateway}",
        extra={
            "gateway": gateway,
            "transform_type": transform_type,
            "transform_cid": transform_cid,
            **extra_context
        }
    )
