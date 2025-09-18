"""History-related routes."""
from flask import render_template, request
from flask_login import current_user

from auth_providers import require_login
from analytics import get_paginated_page_views, get_user_history_statistics

from . import main_bp


@main_bp.route('/history')
@require_login
def history():
    """Display user's page view history."""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    page_views = get_paginated_page_views(current_user.id, page, per_page)
    stats = get_user_history_statistics(current_user.id)

    return render_template('history.html', page_views=page_views, **stats)


__all__ = ['history']
