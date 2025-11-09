"""Backward compatibility shim for routes.openapi module.

This module provides backward compatibility by re-exporting the openapi
functionality from the routes.openapi package.
"""
from __future__ import annotations

from .openapi import openapi_docs, openapi_route_rules, openapi_spec

__all__ = ["openapi_spec", "openapi_docs", "openapi_route_rules"]
