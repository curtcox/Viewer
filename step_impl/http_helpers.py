"""HTTP request helpers for step implementations."""
from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from step_impl.shared_app import get_shared_app, get_shared_client
from step_impl.shared_state import get_scenario_state, store
from step_impl.artifacts import attach_response_snapshot


def _require_app() -> Flask:
    return get_shared_app()


def _require_client() -> FlaskClient:
    return get_shared_client()


def _is_redirect_response(response) -> bool:
    """Return True when the response is an HTTP redirect."""
    status = getattr(response, "status_code", 0) or 0
    has_location = bool(getattr(response, "headers", {}).get("Location"))
    return 300 <= status < 400 and has_location


def _perform_get_request(path: str) -> None:
    """Issue a GET request for the provided path and store the response."""
    client = _require_client()
    # Capture the initial response without following redirects so redirect
    # assertions can inspect the Location header.
    initial_response = client.get(path, follow_redirects=False)
    store.last_response = initial_response

    # Follow redirects separately so most specs continue to validate the
    # rendered destination content.
    final_response = (
        client.get(path, follow_redirects=True)
        if _is_redirect_response(initial_response)
        else initial_response
    )

    scenario_state = get_scenario_state()
    scenario_state["response"] = final_response
    attach_response_snapshot(final_response)


def _perform_post_request(path: str, *, data: dict[str, str]) -> None:
    """Issue a POST request and store the resulting response."""
    client = _require_client()
    initial_response = client.post(path, data=data, follow_redirects=False)
    store.last_response = initial_response

    final_response = (
        client.post(path, data=data, follow_redirects=True)
        if _is_redirect_response(initial_response)
        else initial_response
    )

    scenario_state = get_scenario_state()
    scenario_state["response"] = final_response
    attach_response_snapshot(final_response)


def _normalize_path(path: str) -> str:
    normalized = path.strip().strip('"\'')
    state = get_scenario_state()

    for key, value in state.items():
        if not isinstance(value, str):
            continue
        placeholder = f"{{{key}}}"
        normalized = normalized.replace(placeholder, value)

    return normalized
