"""Routes for managing user-defined aliases."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Dict, Optional, TypeAlias
from urllib.parse import urlsplit

import logfire
from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

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
from alias_matching import evaluate_test_strings, matches_path
from cid_presenter import extract_cid_from_path
from db_access import (
    EntityInteractionRequest,
    get_alias_by_name,
    get_aliases,
    get_template_aliases,
    get_variables,
    record_entity_interaction,
    save_entity,
)
from entity_references import extract_references_from_target
from forms import AliasForm
from interaction_log import load_interaction_history
from models import Alias
from serialization import model_to_dict
from template_status import get_template_link_info


from . import main_bp
from .core import derive_name_from_path, get_existing_routes
from .crud_factory import EntityRouteConfig, register_standard_crud_routes


# Constants
SUBMIT_ACTION_SAVE_AS = 'save-as'

# Type aliases
ValidationResult: TypeAlias = tuple[bool, Optional[str]]
DefinitionMetadata: TypeAlias = Dict[str, Any]


# Dataclasses for structured metadata
@dataclass
class TargetPathMetadata:
    """Metadata for rendering a target path in alias definitions."""
    kind: str  # 'cid', 'server', 'alias', 'path'
    display: str
    url: Optional[str] = None
    name: Optional[str] = None
    cid: Optional[str] = None
    suffix: str = ""


class AliasValidator:
    """Validates alias names against routes and existing aliases."""

    def validate_name(
        self, name: str, exclude_id: Optional[int] = None
    ) -> ValidationResult:
        """Validate an alias name.

        Returns:
            (is_valid, error_message): Tuple with validation and optional error.
        """
        if _alias_name_conflicts_with_routes(name):
            return False, f'Alias name "{name}" conflicts with an existing route.'
        if _alias_with_name_exists(name, exclude_id):
            return False, f'An alias named "{name}" already exists.'
        return True, None


def _alias_name_conflicts_with_routes(name: str) -> bool:
    if not name:
        return False
    return f"/{name}" in get_existing_routes()


def _alias_with_name_exists(
    name: str, exclude_id: Optional[int] = None
) -> bool:
    existing = get_alias_by_name(name)
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


def _build_definition_value(
    definition_text: str, parsed, new_name: str
) -> Optional[str]:
    """Build final definition value from parsed data.

    Consolidates the pattern of building a definition value that appears
    multiple times in new_alias() and edit_alias().

    Args:
        definition_text: The raw definition text from the form
        parsed: Parsed alias definition (or None if parsing failed)
        new_name: The alias name to use in the primary line

    Returns:
        The final definition value with updated primary line, or None if empty
    """
    if parsed:
        primary_line = format_primary_alias_line(
            parsed.match_type,
            parsed.match_pattern,
            parsed.target_path,
            ignore_case=parsed.ignore_case,
            alias_name=new_name,
        )
        return replace_primary_definition_line(definition_text, primary_line)
    return definition_text or None


@logfire.instrument(
    "aliases._persist_alias({alias=})", extract_args=True, record_return=True
)
def _persist_alias(alias: Alias) -> Alias:
    """Persist alias changes while capturing observability metadata."""

    save_entity(alias)
    return alias


def _candidate_cid_from_target(path: str) -> Optional[str]:
    """Return the CID portion from a potential CID target path.

    Examples:
        >>> _candidate_cid_from_target('/QmABC123...')
        'QmABC123...'

        >>> _candidate_cid_from_target('/cid/QmXYZ456...')
        'QmXYZ456...'

        >>> _candidate_cid_from_target('/servers/api')
        None
    """

    candidate = extract_cid_from_path(path)
    if candidate:
        return candidate

    segments = [segment for segment in path.split("/") if segment]
    if len(segments) >= 2 and segments[0].lower() == "cid":
        return extract_cid_from_path(segments[1])

    return None


def _describe_target_path(target_path: Optional[str]) -> Optional[TargetPathMetadata]:
    """Return metadata for rendering a target path within a definition.

    Examples:
        >>> _describe_target_path('/servers/api')
        TargetPathMetadata(kind='server', display='/servers/api',
                           name='api', url='/servers/api')

        >>> _describe_target_path('/ABC123...')
        TargetPathMetadata(kind='cid', display='...', cid='ABC123...', suffix='')
    """

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
        return TargetPathMetadata(
            kind="cid",
            display=f"{candidate_cid}{suffix}",
            cid=candidate_cid,
            suffix=suffix,
        )

    segments = [segment for segment in canonical_path.split("/") if segment]
    if len(segments) >= 2:
        head = segments[0].lower()
        name = segments[1]
        display_path = f"{canonical_path}{suffix}" if canonical_path else normalized

        if head == "servers":
            return TargetPathMetadata(
                kind="server",
                display=display_path,
                name=name,
                url=url_for("main.view_server", server_name=name),
            )

        if head == "aliases":
            return TargetPathMetadata(
                kind="alias",
                display=display_path,
                name=name,
                url=url_for("main.view_alias", alias_name=name),
            )

    return TargetPathMetadata(
        kind="path",
        display=f"{canonical_path}{suffix}" if canonical_path else normalized,
    )


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
        metadata = _describe_target_path(entry.target_path)
        if metadata:
            # Convert dataclass to dict for template compatibility
            target_details = {
                "kind": metadata.kind,
                "display": metadata.display,
                "url": metadata.url,
                "name": metadata.name,
                "cid": metadata.cid,
                "suffix": metadata.suffix,
            }

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


def _build_alias_view_context(alias: Alias) -> Dict[str, Any]:
    """Build extra context for alias view page."""
    primary_route = get_primary_alias_route(alias)
    target_references = extract_references_from_target(
        primary_route.target_path if primary_route else None,
    )

    definition_summary = summarize_definition_lines(
        getattr(alias, "definition", None),
        alias_name=getattr(alias, "name", None),
    )
    definition_lines = [
        _serialize_definition_line(entry) for entry in definition_summary
    ]

    return {
        'target_references': target_references,
        'alias_definition_lines': definition_lines,
    }


def _alias_to_json(alias: Alias) -> Dict[str, Any]:
    return model_to_dict(
        alias,
        {
            "match_type": alias.get_primary_match_type(),
            "match_pattern": alias.get_primary_match_pattern(),
            "target_path": alias.get_primary_target_path(),
            "ignore_case": alias.get_primary_ignore_case(),
        },
    )


# Configure and register standard CRUD routes using the factory
_alias_config = EntityRouteConfig(
    entity_class=Alias,
    entity_type='alias',
    plural_name='aliases',
    get_by_name_func=get_alias_by_name,
    get_entities_func=get_aliases,
    form_class=AliasForm,
    to_json_func=_alias_to_json,
    build_view_context=_build_alias_view_context,
)

register_standard_crud_routes(main_bp, _alias_config)


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

    alias_templates = [
        {
            'id': getattr(alias, 'template_key', None) or alias.id,
            'name': alias.name,
            'definition': alias.definition or '',
            'suggested_name': f"{alias.name}-copy" if alias.name else '',
        }
        for alias in get_template_aliases()
    ]

    if form.validate_on_submit():
        parsed = form.parsed_definition
        name = form.name.data
        validator = AliasValidator()

        is_valid, error_message = validator.validate_name(name)
        if not is_valid:
            flash(error_message, 'danger')
        else:
            definition_text = form.definition.data or ""
            definition_value = _build_definition_value(definition_text, parsed, name)

            alias = Alias(
                name=name,
                definition=definition_value,
                enabled=bool(form.enabled.data),
            )
            _persist_alias(alias)
            record_entity_interaction(
                EntityInteractionRequest(
                    entity_type='alias',
                    entity_name=alias.name,
                    action='save',
                    message=change_message,
                    content=form.definition.data or '',
                )
            )
            flash(f'Alias "{name}" created successfully!', 'success')
            return redirect(url_for('main.aliases'))

    entity_name_hint = (form.name.data or '').strip()
    interaction_history = load_interaction_history(
        'alias', entity_name_hint
    )

    template_link_info = get_template_link_info('aliases')

    return render_template(
        'alias_form.html',
        form=form,
        title='Create New Alias',
        alias=None,
        interaction_history=interaction_history,
        ai_entity_name=entity_name_hint,
        ai_entity_name_field=form.name.id,
        alias_templates=alias_templates,
        template_link_info=template_link_info,
    )


def _handle_save_as(
    form: AliasForm,
    alias: Alias,
    new_name: str,
    definition_value: Optional[str],
    change_message: str,
    validator: AliasValidator,
) -> Optional[str]:
    """Handle 'save-as' submission logic.

    Returns:
        Redirect URL if successful, None if validation failed
    """
    if not new_name or new_name == alias.name:
        flash('Choose a new name to save this alias as a copy.', 'danger')
        return None

    is_valid, error_message = validator.validate_name(new_name)
    if not is_valid:
        flash(error_message, 'danger')
        return None

    alias_copy = Alias(
        name=new_name,
        definition=definition_value or None,
        enabled=bool(form.enabled.data),
    )
    _persist_alias(alias_copy)
    record_entity_interaction(
        EntityInteractionRequest(
            entity_type='alias',
            entity_name=alias_copy.name,
            action='save',
            message=change_message,
            content=form.definition.data or '',
        )
    )
    flash(f'Alias "{alias_copy.name}" created successfully!', 'success')
    return url_for('main.view_alias', alias_name=alias_copy.name)


def _handle_rename(
    form: AliasForm,
    alias: Alias,
    new_name: str,
    definition_value: Optional[str],
    change_message: str,
    validator: AliasValidator,
) -> Optional[str]:
    """Handle standard save with potential rename.

    Returns:
        Redirect URL if successful, None if validation failed
    """
    if new_name != alias.name:
        is_valid, error_message = validator.validate_name(new_name, exclude_id=alias.id)
        if not is_valid:
            flash(error_message, 'danger')
            return None

    alias.name = new_name
    alias.definition = definition_value or None
    alias.updated_at = datetime.now(timezone.utc)
    alias.enabled = bool(form.enabled.data)
    _persist_alias(alias)
    record_entity_interaction(
        EntityInteractionRequest(
            entity_type='alias',
            entity_name=alias.name,
            action='save',
            message=change_message,
            content=form.definition.data or '',
        )
    )
    flash(f'Alias "{alias.name}" updated successfully!', 'success')
    return url_for('main.view_alias', alias_name=alias.name)


@main_bp.route('/aliases/<alias_name>/edit', methods=['GET', 'POST'])
def edit_alias(alias_name: str):
    """Edit an existing alias."""
    alias = get_alias_by_name(alias_name)
    if not alias:
        abort(404)

    form = AliasForm(obj=alias)
    change_message = (request.form.get('change_message') or '').strip()
    interaction_history = load_interaction_history('alias', alias.name)

    def render_edit_form() -> str:
        return render_template(
            'alias_form.html',
            form=form,
            title=f'Edit Alias "{alias.name}"',
            alias=alias,
            interaction_history=interaction_history,
            ai_entity_name=alias.name,
            ai_entity_name_field=form.name.id,
        )

    if request.method == 'GET':
        primary_line = _primary_definition_line_for_alias(alias)
        if primary_line:
            form.definition.data = ensure_primary_line(alias.definition, primary_line)

    if form.validate_on_submit():
        parsed = form.parsed_definition
        new_name = form.name.data or ''
        save_action = (request.form.get('submit_action') or '').strip().lower()
        definition_text = form.definition.data or ""

        definition_value = _build_definition_value(definition_text, parsed, new_name)
        validator = AliasValidator()

        if save_action == SUBMIT_ACTION_SAVE_AS:
            redirect_url = _handle_save_as(
                form, alias, new_name, definition_value, change_message, validator
            )
            if redirect_url:
                return redirect(redirect_url)
            return render_edit_form()

        redirect_url = _handle_rename(
            form, alias, new_name, definition_value, change_message, validator
        )
        if redirect_url:
            return redirect(redirect_url)
        return render_edit_form()

    return render_edit_form()


@main_bp.route('/aliases/match-preview', methods=['POST'])
def alias_match_preview():
    """Return live matching results for the provided alias configuration."""

    payload = request.get_json(silent=True) or {}
    alias_name = payload.get('name')
    definition_text = payload.get('definition')
    raw_paths = payload.get('paths', [])

    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]
    if not isinstance(raw_paths, list):
        return (
            jsonify({'ok': False, 'error': 'Provide a list of paths.'}),
            400,
        )

    if definition_text is None:
        return (
            jsonify({'ok': False, 'error': 'Provide an alias definition.'}),
            400,
        )

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

    definition_summary = summarize_definition_lines(
        definition_text, alias_name=alias_name
    )
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
                matches_path(
                    entry.match_type, entry.match_pattern, path, entry.ignore_case
                )
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


@main_bp.route('/aliases/definition-status', methods=['POST'])
def alias_definition_status():
    """Return the validation status for an alias definition."""

    payload = request.get_json(silent=True) or {}
    raw_definition = payload.get('definition')
    alias_name = payload.get('name')

    if raw_definition is None:
        definition_text = ''
    elif isinstance(raw_definition, str):
        definition_text = raw_definition
    else:
        definition_text = str(raw_definition)

    if alias_name is not None and not isinstance(alias_name, str):
        alias_name = str(alias_name)

    try:
        variables = get_variables()
    except (SQLAlchemyError, AttributeError):  # pragma: no cover - defensive fallback when database fails
        variables = []

    variable_map: dict[str, str] = {}
    for entry in variables:
        name = getattr(entry, 'name', None)
        if not name:
            continue
        value = getattr(entry, 'definition', '')
        variable_map[str(name)] = '' if value is None else str(value)

    variable_pattern = re.compile(r"\{([A-Za-z0-9._-]+)\}")

    def _replace(match: re.Match[str]) -> str:
        placeholder = match.group(0)
        name = match.group(1)
        if not name:
            return placeholder
        return variable_map.get(name, placeholder)

    substituted_definition = variable_pattern.sub(_replace, definition_text)

    try:
        parse_alias_definition(substituted_definition, alias_name=alias_name or None)
    except AliasDefinitionError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400

    return jsonify({'ok': True, 'message': 'Alias definition parses correctly.'})


__all__ = [
    'new_alias',
    'edit_alias',
    'alias_match_preview',
    'alias_definition_status',
]
