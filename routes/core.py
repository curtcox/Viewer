"""Core application routes and helpers."""
from __future__ import annotations

from pathlib import Path
import hashlib
import re
import traceback
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from identity import current_user
from database import db
from db_access import (
    count_user_aliases,
    count_user_secrets,
    count_user_servers,
    count_user_variables,
    create_payment_record,
    create_terms_acceptance_record,
    get_cid_by_path,
    get_first_alias_name,
    get_first_secret_name,
    get_first_server_name,
    get_first_variable_name,
    get_user_aliases,
    get_user_profile_data,
    get_user_servers,
)
from forms import PaymentForm, TermsAcceptanceForm
from cid_presenter import cid_path, format_cid, format_cid_short
from entity_references import (
    extract_references_from_bytes,
    extract_references_from_target,
    extract_references_from_text,
)
from models import CID, CURRENT_TERMS_VERSION
from server_execution import (
    is_potential_server_path,
    is_potential_versioned_server_path,
    try_server_execution,
    try_server_execution_with_partial,
)
from cid_utils import serve_cid_content
from alias_routing import is_potential_alias_path, try_alias_redirect

from . import main_bp


def _extract_exception(error: Exception) -> Exception:
    """Return the underlying exception for Flask HTTP errors."""

    original = getattr(error, "original_exception", None)
    if isinstance(original, Exception):
        return original
    return error


_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


_TYPE_LABELS = {
    'alias': 'Alias',
    'server': 'Server',
    'cid': 'CID',
}


def _make_dom_id(prefix: str, value: Optional[str]) -> str:
    """Return a stable DOM identifier combining a slug and hash suffix."""

    text = (value or '').strip()
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    digest_source = text or prefix
    digest = hashlib.sha1(digest_source.encode('utf-8')).hexdigest()[:8]
    if slug:
        return f"{prefix}-{slug}-{digest}"
    return f"{prefix}-{digest}"


def _entity_key(entity_type: str, identifier: Optional[str]) -> str:
    """Return a unique DOM key for the given entity descriptor."""

    return _make_dom_id(entity_type, identifier or entity_type)


def _reference_key(source_key: str, target_key: str) -> str:
    """Return a DOM key representing a directed relationship."""

    return _make_dom_id('ref', f"{source_key}->{target_key}")


def _preview_text_from_bytes(data: Optional[bytes]) -> Tuple[str, bool]:
    """Return a compact preview and whether it was truncated."""

    if not data:
        return '', False

    try:
        snippet = data.decode('utf-8', errors='replace')
        preview = snippet[:20].replace('\n', ' ').replace('\r', ' ')
        return preview, len(snippet) > 20
    except Exception:
        hex_preview = data[:10].hex()
        return hex_preview, len(data or b'') > 10


def _entity_url(entity_type: str, identifier: str) -> Optional[str]:
    """Return the canonical URL for viewing the given entity."""

    if not identifier:
        return None

    if entity_type == 'alias':
        return url_for('main.view_alias', alias_name=identifier)
    if entity_type == 'server':
        return url_for('main.view_server', server_name=identifier)
    if entity_type == 'cid':
        normalized = format_cid(identifier)
        if not normalized:
            return None
        return url_for('main.meta_route', requested_path=normalized)
    return None


def _build_cross_reference_data(user_id: str) -> Dict[str, Any]:
    """Assemble alias, server, CID, and relationship data for the homepage."""

    aliases = get_user_aliases(user_id)
    servers = get_user_servers(user_id)

    entity_implied: Dict[str, Set[str]] = defaultdict(set)
    entity_outgoing_refs: Dict[str, Set[str]] = defaultdict(set)
    entity_incoming_refs: Dict[str, Set[str]] = defaultdict(set)
    referenced_cids: Set[str] = set()

    def _record_cid_metadata(entry: Optional[Dict[str, Any]]) -> Optional[str]:
        if not entry:
            return None

        cid_value = format_cid(entry.get('cid'))
        if not cid_value:
            return None

        referenced_cids.add(cid_value)
        return cid_value

    references: List[Dict[str, Any]] = []
    reference_seen: Set[Tuple[str, str, str, str]] = set()

    def _register_reference(
        source_type: str,
        source_identifier: str,
        target_type: str,
        target_identifier: str,
    ) -> None:
        if not source_identifier or not target_identifier:
            return

        source_key = _entity_key(source_type, source_identifier)
        target_key = _entity_key(target_type, target_identifier)
        dedupe_key = (source_type, source_identifier, target_type, target_identifier)
        if dedupe_key in reference_seen:
            return
        reference_seen.add(dedupe_key)

        ref_key = _reference_key(source_key, target_key)

        references.append(
            {
                'key': ref_key,
                'source_key': source_key,
                'target_key': target_key,
                'source_type': source_type,
                'target_type': target_type,
                'source_label': _TYPE_LABELS.get(source_type, source_type.title()),
                'target_label': _TYPE_LABELS.get(target_type, target_type.title()),
                'source_name': source_identifier,
                'target_name': target_identifier,
                'source_url': _entity_url(source_type, source_identifier),
                'target_url': _entity_url(target_type, target_identifier),
                'source_cid_short': format_cid_short(source_identifier)
                if source_type == 'cid'
                else None,
                'target_cid_short': format_cid_short(target_identifier)
                if target_type == 'cid'
                else None,
            }
        )

        entity_implied[source_key].add(target_key)
        if source_key != target_key:
            entity_implied[target_key].add(source_key)
        entity_outgoing_refs[source_key].add(ref_key)
        entity_incoming_refs[target_key].add(ref_key)

    def _handle_alias_references(alias_obj) -> None:
        refs = extract_references_from_target(getattr(alias_obj, 'target_path', None), user_id)
        for ref in refs.get('aliases', []):
            target_name = ref.get('name')
            if target_name:
                _register_reference('alias', alias_obj.name, 'alias', target_name)

        for ref in refs.get('servers', []):
            target_name = ref.get('name')
            if target_name:
                _register_reference('alias', alias_obj.name, 'server', target_name)

        for ref in refs.get('cids', []):
            cid_value = _record_cid_metadata(ref)
            if cid_value:
                _register_reference('alias', alias_obj.name, 'cid', cid_value)

    def _handle_server_references(server_obj) -> None:
        refs = extract_references_from_text(getattr(server_obj, 'definition', ''), user_id)
        for ref in refs.get('aliases', []):
            target_name = ref.get('name')
            if target_name:
                _register_reference('server', server_obj.name, 'alias', target_name)

        for ref in refs.get('servers', []):
            target_name = ref.get('name')
            if target_name:
                _register_reference('server', server_obj.name, 'server', target_name)

        for ref in refs.get('cids', []):
            cid_value = _record_cid_metadata(ref)
            if cid_value:
                _register_reference('server', server_obj.name, 'cid', cid_value)

        if getattr(server_obj, 'definition_cid', None):
            cid_value = format_cid(server_obj.definition_cid)
            if cid_value:
                referenced_cids.add(cid_value)
                _register_reference('server', server_obj.name, 'cid', cid_value)

    alias_entries: List[Dict[str, Any]] = []
    for alias in aliases:
        alias_entries.append(
            {
                'type': 'alias',
                'name': alias.name,
                'url': url_for('main.view_alias', alias_name=alias.name),
                'entity_key': _entity_key('alias', alias.name),
                'target_path': getattr(alias, 'target_path', ''),
            }
        )
        _handle_alias_references(alias)

    alias_keys = {entry['entity_key'] for entry in alias_entries}

    server_entries: List[Dict[str, Any]] = []
    for server in servers:
        server_entries.append(
            {
                'type': 'server',
                'name': server.name,
                'url': url_for('main.view_server', server_name=server.name),
                'entity_key': _entity_key('server', server.name),
                'definition_cid': format_cid(getattr(server, 'definition_cid', '')),
            }
        )
        _handle_server_references(server)

    server_keys = {entry['entity_key'] for entry in server_entries}

    cid_paths = [cid_path(value) for value in referenced_cids if cid_path(value)]
    cid_records: Sequence[CID] = []
    if cid_paths:
        cid_records = CID.query.filter(CID.path.in_(cid_paths)).all()

    records_by_cid = {
        format_cid(getattr(record, 'path', '')): record
        for record in cid_records
        if getattr(record, 'path', None)
    }

    cid_candidates: List[Dict[str, Any]] = []
    for cid_value in sorted(referenced_cids):
        record = records_by_cid.get(cid_value)
        file_data = getattr(record, 'file_data', None) if record else None
        preview, truncated = _preview_text_from_bytes(file_data)

        cid_entry = {
            'type': 'cid',
            'cid': cid_value,
            'entity_key': _entity_key('cid', cid_value),
            'preview': preview,
            'preview_truncated': truncated,
            'short_label': format_cid_short(cid_value),
            'meta_url': _entity_url('cid', cid_value),
        }

        if file_data:
            refs = extract_references_from_bytes(file_data, user_id)
            for ref in refs.get('aliases', []):
                target_name = ref.get('name')
                if target_name:
                    _register_reference('cid', cid_value, 'alias', target_name)

            for ref in refs.get('servers', []):
                target_name = ref.get('name')
                if target_name:
                    _register_reference('cid', cid_value, 'server', target_name)

            for ref in refs.get('cids', []):
                target_cid = format_cid(ref.get('cid'))
                if target_cid and target_cid in referenced_cids:
                    _register_reference('cid', cid_value, 'cid', target_cid)

        cid_candidates.append(cid_entry)

    named_entity_keys = alias_keys | server_keys
    cid_entries: List[Dict[str, Any]] = []

    for cid_entry in cid_candidates:
        cid_key = cid_entry['entity_key']
        related_keys = entity_implied.get(cid_key, set())
        has_named_relation = any(key in named_entity_keys for key in related_keys)
        related_reference_keys = entity_outgoing_refs.get(cid_key, set()) | entity_incoming_refs.get(cid_key, set())

        if not has_named_relation or not related_reference_keys:
            continue

        cid_entries.append(cid_entry)

    all_entity_keys = alias_keys | server_keys | {entry['entity_key'] for entry in cid_entries}

    filtered_references: List[Dict[str, Any]] = []
    reference_keys_by_source: Dict[str, Set[str]] = defaultdict(set)
    reference_keys_by_target: Dict[str, Set[str]] = defaultdict(set)
    for ref in references:
        if ref['source_key'] not in all_entity_keys or ref['target_key'] not in all_entity_keys:
            continue
        filtered_references.append(ref)
        reference_keys_by_source[ref['source_key']].add(ref['key'])
        reference_keys_by_target[ref['target_key']].add(ref['key'])

    references = filtered_references

    for entry in alias_entries + server_entries + cid_entries:
        key = entry['entity_key']
        entry['implied_keys'] = sorted(key_value for key_value in entity_implied.get(key, []) if key_value in all_entity_keys)
        entry['outgoing_refs'] = sorted(reference_keys_by_source.get(key, []))
        entry['incoming_refs'] = sorted(reference_keys_by_target.get(key, []))

    references.sort(key=lambda item: (
        item['source_label'],
        item['source_name'],
        item['target_label'],
        item['target_name'],
    ))

    return {
        'aliases': alias_entries,
        'servers': server_entries,
        'cids': cid_entries,
        'references': references,
    }


def derive_name_from_path(path: str) -> Optional[str]:
    """Return the first path segment when it is safe for use as a name."""

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


def _build_stack_trace(error: Exception) -> List[Dict[str, Any]]:
    """Build comprehensive stack trace metadata with /source links for all project files."""

    def _determine_relative_path(
        absolute_path: Path,
        root_path: Path,
        tracked_paths: frozenset[str],
    ) -> Optional[str]:
        # First try to get relative path from project root
        try:
            relative = absolute_path.relative_to(root_path).as_posix()
            return relative
        except ValueError:
            pass

        # Fallback: check if path ends with any tracked path
        normalized = absolute_path.as_posix()
        best_match: Optional[str] = None
        for tracked in tracked_paths:
            if normalized.endswith(tracked):
                if best_match is None or len(tracked) > len(best_match):
                    best_match = tracked
        return best_match

    def _should_create_source_link(relative_path: str, root_path: Path) -> bool:
        """Determine if we should create a source link for this file."""
        if not relative_path:
            return False
        
        # Create links for ALL files within the project directory, not just git-tracked ones
        full_path = root_path / relative_path
        try:
            # Check if file exists and is within project bounds
            resolved_path = full_path.resolve()
            resolved_root = root_path.resolve()
            if full_path.exists() and resolved_root in resolved_path.parents:
                return True
        except (OSError, ValueError):
            pass
        
        return False

    def _get_all_project_files(root_path: Path) -> frozenset[str]:
        """Get all Python files in the project directory for comprehensive source linking."""
        project_files = set()
        try:
            # Get all .py files recursively
            for py_file in root_path.rglob("*.py"):
                try:
                    relative = py_file.relative_to(root_path).as_posix()
                    project_files.add(relative)
                except ValueError:
                    continue
            
            # Also add other common source files
            for pattern in ["*.html", "*.js", "*.css", "*.json", "*.md", "*.txt", "*.yml", "*.yaml"]:
                for file in root_path.rglob(pattern):
                    try:
                        relative = file.relative_to(root_path).as_posix()
                        project_files.add(relative)
                    except ValueError:
                        continue
        except Exception:
            pass
        
        return frozenset(project_files)

    def _get_exception_chain(exc: Exception) -> List[Exception]:
        """Get the full chain of exceptions including __cause__ and __context__."""
        exceptions = []
        current = exc
        seen = set()

        while current and id(current) not in seen:
            seen.add(id(current))
            exceptions.append(current)

            # Follow __cause__ first (explicit chaining), then __context__ (implicit)
            current = getattr(current, '__cause__', None) or getattr(current, '__context__', None)

        return exceptions

    def _strip_project_root_prefix(path_str: str, root_path: Path) -> str:
        """Remove redundant occurrences of the project root from a display path."""

        if not path_str:
            return path_str

        project_fragment = root_path.as_posix().rstrip("/")
        if not project_fragment:
            return path_str

        normalized = path_str.replace("\\", "/")
        updated = normalized
        changed = False

        # Remove every occurrence of the absolute project root, even if repeated.
        while project_fragment and project_fragment in updated:
            changed = True
            start_index = updated.find(project_fragment)
            end_index = start_index + len(project_fragment)
            prefix = updated[:start_index]
            suffix = updated[end_index:]
            if suffix.startswith("/"):
                suffix = suffix[1:]
            updated = (prefix + suffix).lstrip("/")

        if not changed:
            return normalized

        if not updated:
            return normalized or path_str

        return updated

    # Get the primary exception and build comprehensive trace
    exception = _extract_exception(error)
    exception_chain = _get_exception_chain(exception)

    root_path = Path(current_app.root_path).resolve()

    # Get both git-tracked paths and all project files for comprehensive coverage
    try:
        from .source import _get_tracked_paths
        tracked_paths = _get_tracked_paths(current_app.root_path)
    except Exception:  # pragma: no cover - defensive fallback when git unavailable
        tracked_paths = frozenset()
    
    # Get all project files to ensure comprehensive source link coverage
    all_project_files = _get_all_project_files(root_path)
    # Combine tracked and all project files
    comprehensive_paths = tracked_paths | all_project_files

    frames: List[Dict[str, Any]] = []
    
    # Process each exception in the chain
    for exc_index, exc in enumerate(exception_chain):
        traceback_obj = getattr(exc, "__traceback__", None)
        if traceback_obj is None:
            continue
            
        # Add separator for chained exceptions (except for the first one)
        if exc_index > 0:
            frames.append({
                "display_path": "--- Exception Chain ---",
                "lineno": 0,
                "function": f"Caused by: {type(exc).__name__}",
                "code": str(exc) if str(exc) else None,
                "source_link": None,
                "is_separator": True,
            })

        # Extract frames from this exception's traceback
        for frame in traceback.extract_tb(traceback_obj):
            try:
                absolute_path = Path(frame.filename).resolve()
            except OSError:
                absolute_path = Path(frame.filename)

            source_link = None
            display_path = frame.filename

            relative_path = _determine_relative_path(absolute_path, root_path, comprehensive_paths)
            if relative_path:
                display_path = relative_path
                # Create source links for ALL project files, not just git-tracked ones
                if _should_create_source_link(relative_path, root_path):
                    source_link = f"/source/{relative_path}"

            display_path = _strip_project_root_prefix(display_path, root_path)

            # Get more context around the error line if possible (5 lines instead of 2)
            code_context = frame.line
            try:
                if frame.line and absolute_path.exists():
                    # Try to get more lines of context around the error
                    with open(absolute_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if 0 < frame.lineno <= len(lines):
                            # Get 5 lines before and after for better context
                            start_line = max(0, frame.lineno - 6)
                            end_line = min(len(lines), frame.lineno + 5)
                            context_lines = []
                            for i in range(start_line, end_line):
                                line_num = i + 1
                                line_content = lines[i].rstrip()
                                marker = ">>> " if line_num == frame.lineno else "    "
                                context_lines.append(f"{marker}{line_num:4d}: {line_content}")
                            code_context = "\n".join(context_lines)
            except (OSError, UnicodeDecodeError, IndexError):
                # Fall back to the original line if we can't read context
                pass

            frames.append(
                {
                    "display_path": display_path,
                    "lineno": frame.lineno,
                    "function": frame.name,
                    "code": code_context,
                    "source_link": source_link,
                    "is_separator": False,
                }
            )

    return frames


@main_bp.app_context_processor
def inject_observability_info():
    """Expose Logfire and LangSmith availability to all templates."""

    status = current_app.config.get("OBSERVABILITY_STATUS") or {}
    return dict(
        LOGFIRE_AVAILABLE=bool(status.get("logfire_available")),
        LOGFIRE_PROJECT_URL=status.get("logfire_project_url"),
        LOGFIRE_UNAVAILABLE_REASON=status.get("logfire_reason"),
        LANGSMITH_AVAILABLE=bool(status.get("langsmith_available")),
        LANGSMITH_PROJECT_URL=status.get("langsmith_project_url"),
        LANGSMITH_UNAVAILABLE_REASON=status.get("langsmith_reason"),
    )


@main_bp.route('/')
def index():
    """Landing page with marketing and observability information."""
    cross_reference = _build_cross_reference_data(current_user.id)

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
    """Handle subscription payments (mock implementation)."""
    form = PaymentForm()
    if form.validate_on_submit():
        plan_prices = {
            'free': 0.00,
            'annual': 50.00,
        }

        plan = form.plan.data
        amount = plan_prices.get(plan, 0.00)

        create_payment_record(plan, amount, current_user)

        flash(f'Successfully subscribed to {plan.title()} plan!', 'success')
        return redirect(url_for('main.profile'))

    return render_template('subscribe.html', form=form)


@main_bp.route('/accept-terms', methods=['GET', 'POST'])
def accept_terms():
    """Handle terms and conditions acceptance."""
    form = TermsAcceptanceForm()
    if form.validate_on_submit():
        profile_data = get_user_profile_data(current_user.id)
        if profile_data['needs_terms_acceptance']:
            create_terms_acceptance_record(
                current_user,
                request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
            )
            flash('Terms and conditions accepted successfully!', 'success')
        return redirect(url_for('main.profile'))

    return render_template(
        'accept_terms.html',
        form=form,
        terms_version=CURRENT_TERMS_VERSION,
    )


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
def accept_invitation(invitation_code):
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
    """Get counts of a user's saved resources for settings display."""
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


def get_existing_routes():
    """Get set of existing routes that should take precedence over server names."""
    return {
        '/', '/dashboard', '/profile', '/subscribe', '/accept-terms',
        '/plans', '/terms', '/privacy', '/upload',
        '/uploads', '/history', '/servers', '/variables',
        '/secrets', '/settings', '/aliases', '/aliases/new',
        '/edit', '/meta',
        '/export', '/import',
    }


def not_found_error(error):
    """Custom 404 handler that checks CID table and server names for content."""
    path = request.path
    existing_routes = get_existing_routes()

    if is_potential_alias_path(path, existing_routes):
        alias_result = try_alias_redirect(path)
        if alias_result is not None:
            return alias_result

    if is_potential_server_path(path, existing_routes):
        server_result = try_server_execution(path)
        if server_result is not None:
            return server_result

    if is_potential_versioned_server_path(path, existing_routes):
        from .servers import get_server_definition_history

        server_result = try_server_execution_with_partial(path, get_server_definition_history)
        if server_result is not None:
            return server_result

    base_path = path.split('.')[0] if '.' in path else path
    cid_content = get_cid_by_path(base_path)
    if cid_content:
        result = serve_cid_content(cid_content, path)
        if result is not None:
            return result

    return render_template('404.html', path=path), 404


def internal_error(error):
    """Enhanced 500 error handler with comprehensive stack trace reporting."""
    db.session.rollback()
    
    # Always try to build a comprehensive stack trace
    stack_trace = []
    exception = None
    exception_type = "Unknown Error"
    exception_message = "An unexpected error occurred"
    
    try:
        exception = _extract_exception(error)
        exception_type = type(exception).__name__
        exception_message = str(exception) if str(exception) else "No error message available"
        stack_trace = _build_stack_trace(error)
    except Exception as trace_error:
        # If stack trace building fails, create a minimal fallback
        try:
            import sys
            
            # Get the current exception info
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if exc_traceback:
                # Create a basic stack trace as fallback
                stack_trace = [{
                    "display_path": "Error in stack trace generation",
                    "lineno": 0,
                    "function": "internal_error",
                    "code": f"Stack trace generation failed: {trace_error}\n\nOriginal error: {error}",
                    "source_link": None,
                    "is_separator": False,
                }]
            
            # Try to get basic info about the original error
            if not exception:
                exception = error
                exception_type = type(error).__name__
                exception_message = str(error) if str(error) else "Error occurred during error handling"
                
        except Exception:
            # Ultimate fallback - just show basic error info
            stack_trace = [{
                "display_path": "Critical error handling failure",
                "lineno": 0,
                "function": "internal_error",
                "code": f"Both original error and error handling failed.\nOriginal error: {error}",
                "source_link": None,
                "is_separator": False,
            }]

    return (
        render_template(
            '500.html',
            stack_trace=stack_trace,
            exception_type=exception_type,
            exception_message=exception_message,
        ),
        500,
    )


__all__ = [
    'accept_terms',
    'dashboard',
    'get_existing_routes',
    'get_user_settings_counts',
    'index',
    'inject_observability_info',
    'not_found_error',
    'plans',
    'privacy',
    'profile',
    'settings',
    'subscribe',
    'terms',
]
