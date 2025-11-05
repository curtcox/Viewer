"""Core application routes and helpers."""
from __future__ import annotations

import re
from typing import Optional

from flask import abort, redirect, render_template, url_for

from db_access import (
    count_user_aliases,
    count_user_secrets,
    count_user_servers,
    count_user_variables,
    get_first_alias_name,
    get_first_secret_name,
    get_first_server_name,
    get_first_variable_name,
)
from identity import current_user
from routes.context_processors import (
    inject_meta_inspector_link,
    inject_observability_info,
    inject_viewer_navigation,
)
from routes.error_handlers import get_existing_routes, internal_error, not_found_error
from utils.cross_reference import build_cross_reference_data

# Import these for backward compatibility with tests that mock them at routes.core
# These are re-exported so utils/cross_reference.py and tests can access them via routes.core
from alias_definition import get_primary_alias_route  # noqa: F401
from entity_references import (  # noqa: F401
    extract_references_from_bytes,
    extract_references_from_target,
    extract_references_from_text,
)

from . import main_bp


_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


# Alias for backward compatibility
_build_cross_reference_data = build_cross_reference_data


def derive_name_from_path(path: str) -> Optional[str]:
    """
    Return the first path segment when it is safe for use as a name.

    Args:
        path: The URL path to extract a name from

    Returns:
        The extracted name or None if not valid
    """
    if not path:
        return None

    remainder = path.lstrip("/")
    if not remainder:
        return None

    segment = remainder.split("/", 1)[0]
    if not segment:
        return None

    if not _NAME_PATTERN.fullmatch(segment):
        return None

    return segment


# Register context processors
main_bp.app_context_processor(inject_observability_info)
main_bp.app_context_processor(inject_meta_inspector_link)
main_bp.app_context_processor(inject_viewer_navigation)


@main_bp.route('/')
def index():
    """Landing page with marketing and observability information."""
    cross_reference = build_cross_reference_data(current_user.id)

    return render_template('index.html', cross_reference=cross_reference)


@main_bp.route('/dashboard')
def dashboard():
    """User dashboard - directs members to their profile overview."""
    return redirect(url_for('main.profile'))


@main_bp.route('/profile')
def profile():
    """User profile placeholder for future external account management."""
    return render_template('profile.html')


@main_bp.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    abort(404)


@main_bp.route('/accept-terms', methods=['GET', 'POST'])
def accept_terms():
    abort(404)


@main_bp.route('/plans')
def plans():
    abort(404)


@main_bp.route('/terms')
def terms():
    abort(404)


@main_bp.route('/privacy')
def privacy():
    abort(404)


@main_bp.route('/invitations')
def invitations():
    abort(404)


@main_bp.route('/create-invitation', methods=['GET', 'POST'])
def create_invitation():
    abort(404)


@main_bp.route('/require-invitation', methods=['GET', 'POST'])
def require_invitation():
    abort(404)


@main_bp.route('/invite/<invitation_code>')
def accept_invitation(invitation_code):  # pylint: disable=unused-argument
    """Accept invitation route (placeholder - returns 404)."""
    abort(404)


@main_bp.route('/_screenshot/cid-demo')
def screenshot_cid_demo():
    abort(404)


@main_bp.route('/settings')
def settings():
    """Settings page with links to servers, variables, aliases, and secrets."""
    counts = get_user_settings_counts(current_user.id)
    return render_template('settings.html', **counts)


def get_user_settings_counts(user_id):
    """
    Get counts of a user's saved resources for settings display.

    Args:
        user_id: The user ID to get counts for

    Returns:
        Dictionary containing counts and example names
    """
    return {
        'alias_count': count_user_aliases(user_id),
        'server_count': count_user_servers(user_id),
        'variable_count': count_user_variables(user_id),
        'secret_count': count_user_secrets(user_id),
        'alias_example_name': get_first_alias_name(user_id),
        'server_example_name': get_first_server_name(user_id),
        'variable_example_name': get_first_variable_name(user_id),
        'secret_example_name': get_first_secret_name(user_id),
    }


__all__ = [
    'dashboard',
    'get_existing_routes',
    'get_user_settings_counts',
    'index',
    'inject_observability_info',
    'inject_meta_inspector_link',
    'inject_viewer_navigation',
    'not_found_error',
    'internal_error',
    'profile',
    'settings',
    # Backward compatibility exports
    '_build_cross_reference_data',
    # Re-exported functions for backward compatibility
    'get_primary_alias_route',
    'extract_references_from_bytes',
    'extract_references_from_target',
    'extract_references_from_text',
]
