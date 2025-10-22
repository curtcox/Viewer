"""Routes for managing user-defined aliases."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from identity import current_user

from db_access import get_alias_by_name, get_user_aliases, record_entity_interaction, save_entity
from entity_references import extract_references_from_target
from forms import AliasForm
from models import Alias
import logfire
from cid_presenter import extract_cid_from_path

from . import main_bp
from .core import derive_name_from_path, get_existing_routes
from interaction_log import load_interaction_history
from alias_matching import evaluate_test_strings, matches_path
from alias_definition import (
    AliasDefinitionError,
    DefinitionLineSummary,
    ensure_primary_line,
    format_primary_alias_line,
    get_primary_alias_route,
    parse_alias_definition,
    replace_primary_definition_line,
    summarize_definition_lines,
)


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


def _primary_definition_line_for_alias(alias: Alias) -> Optional[str]:
    route = get_primary_alias_route(alias)
    if not route:
        return None
    return format_primary_alias_line(
        route.match_type,
        route.match_pattern,
        route.target_path,
        ignore_case=route.ignore_case,
        alias_name=getattr(alias, "name", None),
    )


def _prefill_definition_from_hints(
    form: AliasForm,
    target_hint: Optional[str],
    path_hint: Optional[str],
) -> None:
    if form.definition.data:
        return

    candidate_name = (form.name.data or "").strip()
    target = (target_hint or "").strip() or (path_hint or "").strip()

    if candidate_name and target:
        form.definition.data = format_primary_alias_line(
            "literal",
            f"/{candidate_name}",
            target,
            alias_name=candidate_name,
        )

@logfire.instrument("aliases._persist_alias({alias=})", extract_args=True, record_return=True)
def _persist_alias(alias: Alias) -> Alias:
    """Persist alias changes while capturing observability metadata."""

    save_entity(alias)
    return alias


def _candidate_cid_from_target(path: str) -> Optional[str]:
    """Return the CID portion from a potential CID target path."""

    candidate = extract_cid_from_path(path)
    if candidate:
        return candidate

    segments = [segment for segment in path.split("/") if segment]
    if len(segments) >= 2 and segments[0].lower() == "cid":
        return extract_cid_from_path(segments[1])

    return None


def _describe_target_path(target_path: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return metadata for rendering a target path within a definition."""

    if not target_path:
        return None

    normalized = target_path.strip()
    if not normalized:
        return None

    parsed = urlsplit(normalized)
    path = parsed.path or ""
    query = parsed.query or ""
    fragment = parsed.fragment or ""

    suffix = ""
    if query:
        suffix += f"?{query}"
    if fragment:
        suffix += f"#{fragment}"

    canonical_path = path
    if canonical_path and not canonical_path.startswith("/"):
        canonical_path = f"/{canonical_path}"

    candidate_cid = _candidate_cid_from_target(canonical_path or normalized)
    if candidate_cid:
        return {
            "kind": "cid",
            "cid": candidate_cid,
            "suffix": suffix,
        }

    segments = [segment for segment in canonical_path.split("/") if segment]
    if len(segments) >= 2:
        head = segments[0].lower()
        name = segments[1]
        display_path = f"{canonical_path}{suffix}" if canonical_path else normalized

        if head == "servers":
            return {
                "kind": "server",
                "name": name,
                "url": url_for("main.view_server", server_name=name),
                "display": display_path,
            }

        if head == "aliases":
            return {
                "kind": "alias",
                "name": name,
                "url": url_for("main.view_alias", alias_name=name),
                "display": display_path,
            }

    return {
        "kind": "path",
        "display": f"{canonical_path}{suffix}" if canonical_path else normalized,
    }


def _serialize_definition_line(entry: DefinitionLineSummary) -> Dict[str, Any]:
    """Convert a definition line summary into template-friendly metadata."""

    options: list[str] = []
    if entry.match_type and entry.match_type != "literal":
        options.append(entry.match_type)
    if entry.ignore_case:
        options.append("ignore-case")

    pattern_text = ""
    if entry.text and "->" in entry.text:
        pattern_text = entry.text.split("->", 1)[0].strip()

    target_details = None
    if entry.is_mapping and not entry.parse_error:
        target_details = _describe_target_path(entry.target_path)

    return {
        "number": entry.number,
        "text": entry.text,
        "is_mapping": entry.is_mapping,
        "parse_error": entry.parse_error,
        "match_type": entry.match_type,
        "match_pattern": entry.match_pattern,
        "ignore_case": entry.ignore_case,
        "target_path": entry.target_path,
        "target_details": target_details,
        "options": options,
        "alias_path": entry.alias_path,
        "depth": entry.depth,
        "pattern_text": (pattern_text or entry.match_pattern or ""),
    }


@main_bp.route('/aliases')
def aliases():
    """Display the authenticated user's aliases."""
    alias_list = get_user_aliases(current_user.id)
    return render_template('aliases.html', aliases=alias_list)


@main_bp.route('/aliases/new', methods=['GET', 'POST'])
def new_alias():
    """Create a new alias for the authenticated user."""
    form = AliasForm()
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

        _prefill_definition_from_hints(form, target_hint, path_hint)

    if form.validate_on_submit():
        parsed = form.parsed_definition
        name = form.name.data

        if _alias_name_conflicts_with_routes(name):
            flash(f'Alias name "{name}" conflicts with an existing route.', 'danger')
        elif _alias_with_name_exists(current_user.id, name):
            flash(f'An alias named "{name}" already exists.', 'danger')
        else:
            definition_text = form.definition.data or ""
            if parsed:
                primary_line = format_primary_alias_line(
                    parsed.match_type,
                    parsed.match_pattern,
                    parsed.target_path,
                    ignore_case=parsed.ignore_case,
                    alias_name=name,
                )
                definition_value = replace_primary_definition_line(
                    definition_text,
                    primary_line,
                )
            else:
                definition_value = definition_text or None

            alias = Alias(
                name=name,
                user_id=current_user.id,
                definition=definition_value,
            )
            _persist_alias(alias)
            record_entity_interaction(
                current_user.id,
                'alias',
                alias.name,
                'save',
                change_message,
                form.definition.data or '',
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

    primary_route = get_primary_alias_route(alias)
    target_references = extract_references_from_target(
        primary_route.target_path if primary_route else None,
        current_user.id,
    )

    definition_summary = summarize_definition_lines(
        getattr(alias, "definition", None), alias_name=getattr(alias, "name", None)
    )
    definition_lines = [_serialize_definition_line(entry) for entry in definition_summary]

    return render_template(
        'alias_view.html',
        alias=alias,
        target_references=target_references,
        alias_definition_lines=definition_lines,
    )


@main_bp.route('/aliases/<alias_name>/edit', methods=['GET', 'POST'])
def edit_alias(alias_name: str):
    """Edit an existing alias."""
    alias = get_alias_by_name(current_user.id, alias_name)
    if not alias:
        abort(404)

    form = AliasForm(obj=alias)
    change_message = (request.form.get('change_message') or '').strip()
    interaction_history = load_interaction_history(current_user.id, 'alias', alias.name)

    if request.method == 'GET':
        primary_line = _primary_definition_line_for_alias(alias)
        if primary_line:
            form.definition.data = ensure_primary_line(alias.definition, primary_line)

    if form.validate_on_submit():
        parsed = form.parsed_definition
        new_name = form.name.data

        if new_name != alias.name:
            if _alias_name_conflicts_with_routes(new_name):
                flash(f'Alias name "{new_name}" conflicts with an existing route.', 'danger')
                return render_template(
                    'alias_form.html',
                    form=form,
                    title=f'Edit Alias "{alias.name}"',
                    alias=alias,
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
                    interaction_history=interaction_history,
                    ai_entity_name=alias.name,
                    ai_entity_name_field=form.name.id,
                )

        alias.name = new_name
        definition_text = form.definition.data or ""
        if parsed:
            primary_line = format_primary_alias_line(
                parsed.match_type,
                parsed.match_pattern,
                parsed.target_path,
                ignore_case=parsed.ignore_case,
                alias_name=new_name,
            )
            definition_value = replace_primary_definition_line(
                definition_text,
                primary_line,
            )
        else:
            definition_value = definition_text

        alias.definition = definition_value or None
        alias.updated_at = datetime.now(timezone.utc)
        _persist_alias(alias)
        record_entity_interaction(
            current_user.id,
            'alias',
            alias.name,
            'save',
            change_message,
            form.definition.data or '',
        )

        flash(f'Alias "{alias.name}" updated successfully!', 'success')
        return redirect(url_for('main.view_alias', alias_name=alias.name))

    return render_template(
        'alias_form.html',
        form=form,
        title=f'Edit Alias "{alias.name}"',
        alias=alias,
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
    alias_name = payload.get('name')
    definition_text = payload.get('definition')
    raw_paths = payload.get('paths', [])

    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]
    if not isinstance(raw_paths, list):
        return jsonify({'ok': False, 'error': 'Provide a list of paths to evaluate.'}), 400

    if definition_text is None:
        return jsonify({'ok': False, 'error': 'Provide an alias definition to evaluate.'}), 400

    candidate_paths: list[str] = []
    for raw_value in raw_paths:
        if not isinstance(raw_value, str):
            continue
        trimmed = raw_value.strip()
        if not trimmed:
            continue
        candidate_paths.append(trimmed if trimmed.startswith('/') else f'/{trimmed}')

    try:
        parsed = parse_alias_definition(definition_text, alias_name=alias_name)
    except AliasDefinitionError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400

    definition_summary = summarize_definition_lines(definition_text, alias_name=alias_name)
    has_active_paths = bool(candidate_paths)

    line_status = []
    for entry in definition_summary:
        matches_any = False
        if (
            entry.is_mapping
            and not entry.parse_error
            and entry.match_type
            and entry.match_pattern
            and has_active_paths
        ):
            matches_any = any(
                matches_path(entry.match_type, entry.match_pattern, path, entry.ignore_case)
                for path in candidate_paths
            )

        line_status.append(
            {
                'number': entry.number,
                'text': entry.text,
                'is_mapping': entry.is_mapping,
                'matches_any': matches_any,
                'has_error': bool(entry.parse_error),
                'parse_error': entry.parse_error,
            }
        )

    results = evaluate_test_strings(
        parsed.match_type,
        parsed.match_pattern,
        raw_paths,
        ignore_case=parsed.ignore_case,
    )

    return jsonify(
        {
            'ok': True,
            'pattern': parsed.match_pattern,
            'results': [
                {
                    'value': value,
                    'matches': matches,
                }
                for value, matches in results
            ],
            'definition': {
                'has_active_paths': has_active_paths,
                'lines': line_status,
            },
        }
    )


__all__ = ['aliases', 'new_alias', 'view_alias', 'edit_alias', 'alias_match_preview']
