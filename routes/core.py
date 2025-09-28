"""Core application routes and helpers."""
from __future__ import annotations

from pathlib import Path
import re
import traceback
from typing import Any, Dict, List, Optional

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user

from auth_providers import require_login, auth_manager, save_user_from_claims
from database import db
from db_access import (
    count_user_aliases,
    count_user_secrets,
    count_user_servers,
    count_user_variables,
    create_payment_record,
    create_terms_acceptance_record,
    get_cid_by_path,
    get_user_profile_data,
    validate_invitation_code,
)
from forms import (
    InvitationCodeForm,
    InvitationForm,
    PaymentForm,
    TermsAcceptanceForm,
)
from models import Invitation, CURRENT_TERMS_VERSION
from secrets import token_urlsafe as secrets_token_urlsafe
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


# Make authentication info available to all templates
@main_bp.app_context_processor
def inject_auth_info():
    return dict(
        AUTH_AVAILABLE=auth_manager.is_authentication_available(),
        AUTH_PROVIDER=auth_manager.get_provider_name(),
        LOGIN_URL=auth_manager.get_login_url(),
        LOGOUT_URL=auth_manager.get_logout_url(),
    )


@main_bp.route('/')
def index():
    """Landing page - shows different content based on user status."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@main_bp.route('/dashboard')
@require_login
def dashboard():
    """User dashboard - directs members to their profile overview."""
    return redirect(url_for('main.profile'))


@main_bp.route('/profile')
@require_login
def profile():
    """User profile showing payment history and terms acceptance."""
    profile_data = get_user_profile_data(current_user.id)
    return render_template('profile.html', **profile_data)


@main_bp.route('/subscribe', methods=['GET', 'POST'])
@require_login
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
@require_login
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
    """Display pricing plans."""
    return render_template('plans.html')


@main_bp.route('/terms')
def terms():
    """Terms of service page."""
    return render_template('terms.html', current_version=CURRENT_TERMS_VERSION)



@main_bp.route('/privacy')
def privacy():
    """Display privacy policy."""
    return render_template('privacy.html')


@main_bp.route('/invitations')
@require_login
def invitations():
    """Manage user invitations."""
    user_invitations = (
        Invitation.query
        .filter_by(inviter_user_id=current_user.id)
        .order_by(Invitation.created_at.desc())
        .all()
    )
    return render_template('invitations.html', invitations=user_invitations)


@main_bp.route('/create-invitation', methods=['GET', 'POST'])
@require_login
def create_invitation():
    """Create a new invitation."""
    form = InvitationForm()

    if form.validate_on_submit():
        invitation_code = secrets_token_urlsafe(16)

        invitation = Invitation(
            inviter_user_id=current_user.id,
            invitation_code=invitation_code,
            email=form.email.data if form.email.data else None,
        )

        db.session.add(invitation)
        db.session.commit()

        flash(f'Invitation created! Code: {invitation_code}', 'success')
        return redirect(url_for('main.invitations'))

    return render_template('create_invitation.html', form=form)


@main_bp.route('/require-invitation', methods=['GET', 'POST'])
def require_invitation():
    """Handle invitation code requirement for new users."""
    form = InvitationCodeForm()
    error_message = session.pop('invitation_error', None)

    if form.validate_on_submit():
        invitation_code = form.invitation_code.data
        invitation = validate_invitation_code(invitation_code)

        if invitation:
            session['invitation_code'] = invitation_code

            auth_result = handle_pending_authentication(invitation_code)
            if auth_result:
                return auth_result

            flash('Invitation validated! Please sign in.', 'success')
            return redirect(auth_manager.get_login_url())
        else:
            flash('Invalid or expired invitation code.', 'danger')

    return render_template(
        'require_invitation.html',
        form=form,
        error_message=error_message,
    )


@main_bp.route('/invite/<invitation_code>')
def accept_invitation(invitation_code):
    """Direct link to accept an invitation."""
    invitation = validate_invitation_code(invitation_code)

    if invitation:
        session['invitation_code'] = invitation_code
        flash('Invitation accepted! Please sign in to complete your registration.', 'success')
        return redirect(auth_manager.get_login_url())

    flash('Invalid or expired invitation link.', 'danger')
    return redirect(url_for('main.require_invitation'))


@main_bp.route('/settings')
@require_login
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
    }


def handle_pending_authentication(invitation_code):
    """Handle pending authentication with invitation code."""
    if 'pending_token' in session and 'pending_user_claims' in session:
        _ = session.pop('pending_token')
        user_claims = session.pop('pending_user_claims')

        try:
            user = save_user_from_claims(user_claims, invitation_code)
            session.pop('invitation_code', None)

            from flask_login import login_user

            login_user(user)

            flash('Welcome! Your account has been created.', 'success')
            return redirect(url_for('main.index'))
        except ValueError as exc:
            flash(f'Error: {str(exc)}', 'danger')
            return None

    return None


def get_existing_routes():
    """Get set of existing routes that should take precedence over server names."""
    return {
        '/', '/dashboard', '/profile', '/subscribe', '/accept-terms',
        '/plans', '/terms', '/privacy', '/upload', '/invitations', '/create-invitation',
        '/require-invitation', '/uploads', '/history', '/servers', '/variables',
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
    'accept_invitation',
    'accept_terms',
    'create_invitation',
    'dashboard',
    'get_existing_routes',
    'get_user_settings_counts',
    'handle_pending_authentication',
    'index',
    'inject_auth_info',
    'invitations',
    'not_found_error',
    'plans',
    'privacy',
    'profile',
    'require_invitation',
    'settings',
    'subscribe',
    'terms',
]
