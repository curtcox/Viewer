"""Routes for managing user-defined aliases."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from identity import current_user

from db_access import get_alias_by_name, get_user_aliases, record_entity_interaction, save_entity
from entity_references import extract_references_from_target
from forms import AliasForm
from models import Alias
import logfire

from . import main_bp
from .core import derive_name_from_path, get_existing_routes
from interaction_log import load_interaction_history
from alias_matching import PatternError, evaluate_test_strings, normalise_pattern


def _alias_name_conflicts_with_routes(name: str) -> bool:
    if not name:
        return False
    return f"/{name}" in get_existing_routes()


def _alias_with_name_exists(user_id: str, name: str, exclude_id: Optional[int] = None) -> bool:
    existing = get_alias_by_name(user_id, name)
    if not existing:
        return False
    if exclude_id is not None and getattr(existing, "id", None) == exclude_id:
        return False
    return True


@logfire.instrument("aliases._persist_alias({alias=})", extract_args=True, record_return=True)
def _persist_alias(alias: Alias) -> Alias:
    """Persist alias changes while capturing observability metadata."""

    save_entity(alias)
    return alias


@main_bp.route('/aliases')
def aliases():
    """Display the authenticated user's aliases."""
    alias_list = get_user_aliases(current_user.id)
    return render_template('aliases.html', aliases=alias_list)


@main_bp.route('/aliases/new', methods=['GET', 'POST'])
def new_alias():
    """Create a new alias for the authenticated user."""
    form = AliasForm()
    test_results = None
    change_message = (request.form.get('change_message') or '').strip()

    if request.method == 'GET':
        path_hint = (request.args.get('path') or '').strip()
        name_hint = (request.args.get('name') or '').strip()
        target_hint = (request.args.get('target_path') or '').strip()

        if name_hint and not form.name.data:
            form.name.data = name_hint
        elif path_hint:
            suggested_name = derive_name_from_path(path_hint)
            if suggested_name and not form.name.data:
                form.name.data = suggested_name

        if target_hint and not form.target_path.data:
            form.target_path.data = target_hint or None
        elif path_hint and not form.target_path.data:
            form.target_path.data = path_hint

    if form.validate_on_submit():
        if form.test_pattern.data:
            test_results = form.evaluated_tests()
        else:
            name = form.name.data
            target_path = form.target_path.data

            if _alias_name_conflicts_with_routes(name):
                flash(f'Alias name "{name}" conflicts with an existing route.', 'danger')
            elif _alias_with_name_exists(current_user.id, name):
                flash(f'An alias named "{name}" already exists.', 'danger')
            else:
                alias = Alias(
                    name=name,
                    target_path=target_path,
                    user_id=current_user.id,
                    match_type=form.match_type.data,
                    match_pattern=form.match_pattern.data,
                    ignore_case=bool(form.ignore_case.data),
                    definition=form.definition.data or None,
                )
                _persist_alias(alias)
                record_entity_interaction(
                    current_user.id,
                    'alias',
                    alias.name,
                    'save',
                    change_message,
                    form.test_strings.data or '',
                )
                flash(f'Alias "{name}" created successfully!', 'success')
                return redirect(url_for('main.aliases'))

    entity_name_hint = (form.name.data or '').strip()
    interaction_history = load_interaction_history(current_user.id, 'alias', entity_name_hint)

    return render_template(
        'alias_form.html',
        form=form,
        title='Create New Alias',
        alias=None,
        test_results=test_results,
        interaction_history=interaction_history,
        ai_entity_name=entity_name_hint,
        ai_entity_name_field=form.name.id,
    )


@main_bp.route('/aliases/<alias_name>')
def view_alias(alias_name: str):
    """View a single alias."""
    alias = get_alias_by_name(current_user.id, alias_name)
    if not alias:
        abort(404)

    target_references = extract_references_from_target(
        getattr(alias, "target_path", None),
        current_user.id,
    )

    return render_template(
        'alias_view.html',
        alias=alias,
        target_references=target_references,
    )


@main_bp.route('/aliases/<alias_name>/edit', methods=['GET', 'POST'])
def edit_alias(alias_name: str):
    """Edit an existing alias."""
    alias = get_alias_by_name(current_user.id, alias_name)
    if not alias:
        abort(404)

    form = AliasForm(obj=alias)
    test_results = None
    change_message = (request.form.get('change_message') or '').strip()
    interaction_history = load_interaction_history(current_user.id, 'alias', alias.name)

    if form.validate_on_submit():
        if form.test_pattern.data:
            test_results = form.evaluated_tests()
        else:
            new_name = form.name.data
            new_target = form.target_path.data

            if new_name != alias.name:
                if _alias_name_conflicts_with_routes(new_name):
                    flash(f'Alias name "{new_name}" conflicts with an existing route.', 'danger')
                    return render_template(
                        'alias_form.html',
                        form=form,
                        title=f'Edit Alias "{alias.name}"',
                        alias=alias,
                        test_results=test_results,
                        interaction_history=interaction_history,
                        ai_entity_name=alias.name,
                        ai_entity_name_field=form.name.id,
                    )

                if _alias_with_name_exists(current_user.id, new_name, exclude_id=alias.id):
                    flash(f'An alias named "{new_name}" already exists.', 'danger')
                    return render_template(
                        'alias_form.html',
                        form=form,
                        title=f'Edit Alias "{alias.name}"',
                        alias=alias,
                        test_results=test_results,
                        interaction_history=interaction_history,
                        ai_entity_name=alias.name,
                        ai_entity_name_field=form.name.id,
                    )

            alias.name = new_name
            alias.target_path = new_target
            alias.match_type = form.match_type.data
            alias.match_pattern = form.match_pattern.data
            alias.ignore_case = bool(form.ignore_case.data)
            alias.definition = form.definition.data or None
            alias.updated_at = datetime.now(timezone.utc)
            _persist_alias(alias)
            record_entity_interaction(
                current_user.id,
                'alias',
                alias.name,
                'save',
                change_message,
                form.test_strings.data or '',
            )

            flash(f'Alias "{alias.name}" updated successfully!', 'success')
            return redirect(url_for('main.view_alias', alias_name=alias.name))

    return render_template(
        'alias_form.html',
        form=form,
        title=f'Edit Alias "{alias.name}"',
        alias=alias,
        test_results=test_results,
        interaction_history=interaction_history,
        ai_entity_name=alias.name,
        ai_entity_name_field=form.name.id,
    )


@main_bp.route('/aliases/match-preview', methods=['POST'])
def alias_match_preview():
    """Return live matching results for the provided alias configuration."""

    if not getattr(current_user, 'id', None):
        abort(401)

    payload = request.get_json(silent=True) or {}
    match_type = (payload.get('match_type') or 'literal').lower()
    match_pattern = payload.get('match_pattern')
    alias_name = payload.get('name')
    ignore_case = bool(payload.get('ignore_case', False))
    raw_paths = payload.get('paths', [])

    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]
    if not isinstance(raw_paths, list):
        return jsonify({'ok': False, 'error': 'Provide a list of paths to evaluate.'}), 400

    try:
        normalised = normalise_pattern(match_type, match_pattern, alias_name)
    except PatternError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400

    results = evaluate_test_strings(
        match_type,
        normalised,
        raw_paths,
        ignore_case=ignore_case,
    )

    return jsonify(
        {
            'ok': True,
            'pattern': normalised,
            'results': [
                {
                    'value': value,
                    'matches': matches,
                }
                for value, matches in results
            ],
        }
    )


__all__ = ['aliases', 'new_alias', 'view_alias', 'edit_alias', 'alias_match_preview']
