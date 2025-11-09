"""Routes that expose the application's OpenAPI schema and Swagger UI."""
from __future__ import annotations

from typing import Set

from flask import Flask, Response, jsonify, render_template, url_for

from .. import main_bp
from .helpers import convert_path_to_rule
from .spec_builder import build_openapi_spec


def openapi_route_rules(app: Flask) -> Set[str]:
    """Return the Flask routing rules documented in the OpenAPI schema."""

    with app.test_request_context("/"):
        spec = build_openapi_spec()
    return {convert_path_to_rule(path) for path in spec["paths"]}


@main_bp.route("/openapi.json")
def openapi_spec() -> Response:
    """Return the OpenAPI specification describing the HTTP API."""

    return jsonify(build_openapi_spec())


@main_bp.route("/openapi")
def openapi_docs() -> str:
    """Render an interactive Swagger UI configured for the app's schema."""

    spec_url = url_for("main.openapi_spec", _external=False)
    return render_template("swagger.html", title="API Explorer", spec_url=spec_url)


__all__ = ["openapi_spec", "openapi_docs", "openapi_route_rules", "build_openapi_spec"]
