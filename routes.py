from datetime import datetime, timezone
from flask import Blueprint, render_template, flash, redirect, url_for, request, session, jsonify, abort
from flask_login import current_user
from database import db
from models import Invitation, Server, Variable, Secret, CURRENT_TERMS_VERSION, ServerInvocation
from analytics import get_paginated_page_views, get_user_history_statistics
from db_access import (
    get_user_profile_data,
    create_payment_record,
    create_terms_acceptance_record,
    validate_invitation_code,
    get_user_servers,
    get_server_by_name,
    get_user_variables,
    get_variable_by_name,
    get_user_secrets,
    get_secret_by_name,
    count_user_servers,
    count_user_variables,
    count_user_secrets,
    save_entity,
    delete_entity,
    get_cid_by_path,
    create_cid_record,
    get_user_uploads,
)
from forms import PaymentForm, TermsAcceptanceForm, FileUploadForm, InvitationForm, InvitationCodeForm, ServerForm, VariableForm, SecretForm
from auth_providers import require_login, auth_manager, save_user_from_claims
from secrets import token_urlsafe as secrets_token_urlsafe
from cid_utils import (
    generate_cid,
    process_file_upload,
    process_text_upload,
    process_url_upload,
    save_server_definition_as_cid,
    store_server_definitions_cid,
    get_current_server_definitions_cid,
    store_variable_definitions_cid,
    get_current_variable_definitions_cid,
    store_secret_definitions_cid,
    get_current_secret_definitions_cid,
    get_extension_from_mime_type,
    serve_cid_content,
)
from server_execution import (
    is_potential_server_path,
    is_potential_versioned_server_path,
    try_server_execution,
    try_server_execution_with_partial,
)

# Blueprint for main application routes
main_bp = Blueprint('main', __name__)


# Make authentication info available to all templates
@main_bp.app_context_processor
def inject_auth_info():
    return dict(
        AUTH_AVAILABLE=auth_manager.is_authentication_available(),
        AUTH_PROVIDER=auth_manager.get_provider_name(),
        LOGIN_URL=auth_manager.get_login_url(),
        LOGOUT_URL=auth_manager.get_logout_url()
    )

@main_bp.route('/')
def index():
    """Landing page - shows different content based on user status"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@require_login
def dashboard():
    """User dashboard - redirects based on access level"""
    if current_user.has_access():
        return redirect(url_for('main.content'))
    return redirect(url_for('main.profile'))

@main_bp.route('/profile')
@require_login
def profile():
    """User profile showing payment history and terms acceptance"""
    profile_data = get_user_profile_data(current_user.id)
    return render_template('profile.html', **profile_data)

@main_bp.route('/subscribe', methods=['GET', 'POST'])
@require_login
def subscribe():
    """Handle subscription payments (mock implementation)"""
    form = PaymentForm()
    if form.validate_on_submit():
        plan_prices = {
            'free': 0.00,
            'annual': 50.00
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
    """Handle terms and conditions acceptance"""
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

    return render_template('accept_terms.html', form=form, terms_version=CURRENT_TERMS_VERSION)

@main_bp.route('/content')
@require_login
def content():
    """Protected content area - displays HTTP request details"""
    if not current_user.has_access():
        flash('Access denied. Please ensure you have an active subscription and have accepted the current terms and conditions.', 'warning')
        return redirect(url_for('main.profile'))

    request_info = gather_request_info()
    return render_template('content.html', request_info=request_info)

@main_bp.route('/plans')
def plans():
    """Display pricing plans"""
    return render_template('plans.html')

@main_bp.route('/terms')
def terms():
    """Display terms and conditions"""
    return render_template('terms.html', current_version=CURRENT_TERMS_VERSION)

@main_bp.route('/privacy')
def privacy():
    """Display privacy policy"""
    return render_template('privacy.html')

def get_server_definition_history(user_id, server_name):
    """Get historical server definitions for a specific server, ordered by time (latest first)"""
    from models import CID, db
    
    # Get all CIDs that contain server definitions for this user
    # We need to check the content of each CID to see if it contains the server
    cids = db.session.query(CID).filter(
        CID.uploaded_by_user_id == user_id
    ).order_by(CID.created_at.desc()).all()
    
    history = []
    
    # Some tests may mock db and return a non-iterable; gracefully handle that
    try:
        iterator = iter(cids)
    except TypeError:
        return history

    for cid in iterator:
        try:
            # Decode the CID content
            content = cid.file_data.decode('utf-8')
            
            # Check if this is a server definition by trying to parse as JSON
            try:
                import json
                server_definitions = json.loads(content)
                
                # If this CID contains our server, add it to history
                if isinstance(server_definitions, dict) and server_name in server_definitions:
                    # Compute the content-addressed CID for just this server's definition
                    definition_text = server_definitions[server_name]
                    definition_bytes = definition_text.encode('utf-8')
                    per_server_cid = generate_cid(definition_bytes)

                    # Prepare snapshot CID without leading slash for clean URL building
                    snapshot_cid_no_slash = cid.path[1:] if cid.path.startswith('/') else cid.path

                    history.append({
                        'definition': definition_text,
                        'definition_cid': per_server_cid,  # hash only, no leading slash
                        'snapshot_cid': snapshot_cid_no_slash,  # hash only, no leading slash
                        'snapshot_path': cid.path,  # original path, with leading slash
                        'created_at': cid.created_at,
                        'is_current': False  # We'll mark the current one later
                    })
            except (json.JSONDecodeError, TypeError):
                # This might be an individual server definition CID
                # Check if the content matches any historical definition for this server
                # For now, we'll skip individual CIDs and focus on the JSON collections
                pass
                
        except (UnicodeDecodeError, AttributeError):
            # Skip binary or malformed content
            continue
    
    # Mark the most recent entry as current if we have any
    if history:
        history[0]['is_current'] = True
    
    return history

def update_server_definitions_cid(user_id):
    """Update the server definitions CID after server changes"""
    return store_server_definitions_cid(user_id)

# ============================================================================
# VARIABLE DEFINITIONS CID HELPERS
# ============================================================================

def update_variable_definitions_cid(user_id):
    """Update the variable definitions CID after variable changes"""
    return store_variable_definitions_cid(user_id)

# ============================================================================
# SERVER DEFINITIONS CID HELPERS
# ============================================================================

def update_secret_definitions_cid(user_id):
    """Update the secret definitions CID after secret changes"""
    return store_secret_definitions_cid(user_id)

@main_bp.route('/upload', methods=['GET', 'POST'])
@require_login
def upload():
    """File upload page with IPFS CID storage - supports both file upload and text input"""
    form = FileUploadForm()

    if form.validate_on_submit():
        try:
            detected_mime_type = None
            original_filename = None

            if form.upload_type.data == 'file':
                file_content, original_filename = process_file_upload(form)
            elif form.upload_type.data == 'text':
                file_content = process_text_upload(form)
            else:  # url upload
                file_content, detected_mime_type = process_url_upload(form)
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('upload.html', form=form)

        # Generate IPFS-like CID
        cid = generate_cid(file_content)

        # Check if CID already exists
        existing = get_cid_by_path(f"/{cid}")
        if existing:
            flash(f'Content with this hash already exists! CID: {cid}', 'warning')
        else:
            create_cid_record(cid, file_content, current_user.id)
            flash(f'Content uploaded successfully! CID: {cid}', 'success')

        # Determine the appropriate file extension for the view URL based on upload method
        view_url_extension = ""

        if form.upload_type.data == 'text':
            # Pasted text always gets .txt extension
            view_url_extension = "txt"
        elif form.upload_type.data == 'file' and original_filename:
            # File upload uses original file extension
            if '.' in original_filename:
                view_url_extension = original_filename.rsplit('.', 1)[1].lower()
        elif detected_mime_type:
            # URL upload uses MIME type detection
            extension = get_extension_from_mime_type(detected_mime_type)
            if extension:
                view_url_extension = extension.lstrip('.')

        return render_template('upload_success.html',
                             cid=cid,
                             file_size=len(file_content),
                             detected_mime_type=detected_mime_type,
                             view_url_extension=view_url_extension)

    return render_template('upload.html', form=form)

@main_bp.route('/invitations')
@require_login
def invitations():
    """Manage user invitations"""
    user_invitations = Invitation.query.filter_by(inviter_user_id=current_user.id).order_by(Invitation.created_at.desc()).all()
    return render_template('invitations.html', invitations=user_invitations)

@main_bp.route('/create-invitation', methods=['GET', 'POST'])
@require_login
def create_invitation():
    """Create a new invitation"""
    form = InvitationForm()

    if form.validate_on_submit():
        # Generate unique invitation code
        invitation_code = secrets_token_urlsafe(16)

        invitation = Invitation(
            inviter_user_id=current_user.id,
            invitation_code=invitation_code,
            email=form.email.data if form.email.data else None
        )

        db.session.add(invitation)
        db.session.commit()

        flash(f'Invitation created! Code: {invitation_code}', 'success')
        return redirect(url_for('main.invitations'))

    return render_template('create_invitation.html', form=form)

@main_bp.route('/require-invitation', methods=['GET', 'POST'])
def require_invitation():
    """Handle invitation code requirement for new users"""
    form = InvitationCodeForm()
    error_message = session.pop('invitation_error', None)

    if form.validate_on_submit():
        invitation_code = form.invitation_code.data
        invitation = validate_invitation_code(invitation_code)

        if invitation:
            # Store invitation code in session and retry authentication
            session['invitation_code'] = invitation_code

            # Try to handle pending authentication
            auth_result = handle_pending_authentication(invitation_code)
            if auth_result:
                return auth_result

            # Just store invitation for future auth attempt
            flash('Invitation validated! Please sign in.', 'success')
            return redirect(auth_manager.get_login_url())
        else:
            flash('Invalid or expired invitation code.', 'danger')

    return render_template('require_invitation.html', form=form, error_message=error_message)

@main_bp.route('/invite/<invitation_code>')
def accept_invitation(invitation_code):
    """Direct link to accept an invitation"""
    invitation = validate_invitation_code(invitation_code)

    if invitation:
        session['invitation_code'] = invitation_code
        flash('Invitation accepted! Please sign in to complete your registration.', 'success')
        return redirect(auth_manager.get_login_url())
    else:
        flash('Invalid or expired invitation link.', 'danger')
        return redirect(url_for('main.require_invitation'))

@main_bp.route('/uploads')
@require_login
def uploads():
    """Display user's uploaded files"""
    user_uploads = get_user_uploads(current_user.id)

    # Add content preview to each upload
    for upload in user_uploads:
        if upload.file_data:
            try:
                # Try to decode as UTF-8 and get first 20 characters
                content_text = upload.file_data.decode('utf-8', errors='replace')
                upload.content_preview = content_text[:20].replace('\n', ' ').replace('\r', ' ')
            except Exception:
                # If decoding fails, show hex representation
                upload.content_preview = upload.file_data[:10].hex()
        else:
            upload.content_preview = ""

    # Calculate total storage used
    total_storage = sum(upload.file_size or 0 for upload in user_uploads)

    return render_template('uploads.html',
                         uploads=user_uploads,
                         total_uploads=len(user_uploads),
                         total_storage=total_storage)

# ============================================================================
# SERVER INVOCATION HISTORY HELPERS
# ============================================================================

def _invocation_to_dict(inv):
    return {
        'result_cid': inv.result_cid,
        'invoked_at': inv.invoked_at,
        'servers_cid': inv.servers_cid,
        'variables_cid': inv.variables_cid,
        'secrets_cid': inv.secrets_cid,
        'request_details_cid': getattr(inv, 'request_details_cid', None),
        'invocation_cid': getattr(inv, 'invocation_cid', None),
    }

def get_server_invocation_extremes(user_id, server_name):
    """Return first 3 and last 3 invocations for a server name (by time).

    If there are fewer than 7 total invocations, return all of them (ascending by time)
    under the key 'all_invocations'. Otherwise return 'first_invocations' and
    'last_invocations' lists.
    """
    base_query = ServerInvocation.query.filter_by(user_id=user_id, server_name=server_name)
    total = base_query.count()
    result = { 'total_count': total }

    if total == 0:
        return result

    if total < 7:
        all_inv = base_query.order_by(ServerInvocation.invoked_at.asc(), ServerInvocation.id.asc()).all()
        result['all_invocations'] = [_invocation_to_dict(i) for i in all_inv]
        return result

    first_three = base_query.order_by(ServerInvocation.invoked_at.asc(), ServerInvocation.id.asc()).limit(3).all()
    last_three = base_query.order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc()).limit(3).all()

    result['first_invocations'] = [_invocation_to_dict(i) for i in first_three]
    # Ensure last_three is in descending time; render as latest first is fine
    result['last_invocations'] = [_invocation_to_dict(i) for i in last_three]
    return result

@main_bp.route('/history')
@require_login
def history():
    """Display user's page view history"""
    # Get page parameter for pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Show 50 entries per page

    # Get paginated page views
    page_views = get_paginated_page_views(current_user.id, page, per_page)

    # Get statistics
    stats = get_user_history_statistics(current_user.id)

    return render_template('history.html',
                         page_views=page_views,
                         **stats)

# ============================================================================
# USER DATA QUERY HELPERS
# ============================================================================

def user_servers():
    return get_user_servers(current_user.id)

@main_bp.route('/servers')
@require_login
def servers():
    """Display user's servers"""
    servers_list = user_servers()
    # Get current server definitions CID if user has servers
    server_definitions_cid = None
    if servers_list:
        server_definitions_cid = get_current_server_definitions_cid(current_user.id)

    return render_template('servers.html',
                         servers=servers_list,
                         server_definitions_cid=server_definitions_cid)

@main_bp.route('/servers/new', methods=['GET', 'POST'])
@require_login
def new_server():
    """Create a new server"""
    form = ServerForm()

    if form.validate_on_submit():
        if create_entity(Server, form, current_user.id, 'server'):
            return redirect(url_for('main.servers'))

    return render_template('server_form.html', form=form, title='Create New Server')

@main_bp.route('/servers/<server_name>')
@require_login
def view_server(server_name):
    """View a specific server"""
    server = get_server_by_name(current_user.id, server_name)
    if not server:
        abort(404)

    # Get historical definitions for this server
    history = get_server_definition_history(current_user.id, server_name)
    # Get invocation extremes (first/last invocations)
    invocations = get_server_invocation_extremes(current_user.id, server_name)

    return render_template('server_view.html', server=server, definition_history=history, server_invocations=invocations)

@main_bp.route('/servers/<server_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_server(server_name):
    """Edit a specific server"""
    server = get_server_by_name(current_user.id, server_name)
    if not server:
        abort(404)

    form = ServerForm(obj=server)

    # Get historical definitions for this server
    history = get_server_definition_history(current_user.id, server_name)
    # Get invocation extremes (first/last invocations)
    invocations = get_server_invocation_extremes(current_user.id, server_name)

    if form.validate_on_submit():
        if update_entity(server, form, 'server'):
            return redirect(url_for('main.view_server', server_name=server.name))
        else:
            return render_template('server_form.html', form=form, title=f'Edit Server "{server.name}"', server=server, definition_history=history, server_invocations=invocations)

    return render_template('server_form.html', form=form, title=f'Edit Server "{server.name}"', server=server, definition_history=history, server_invocations=invocations)

@main_bp.route('/servers/<server_name>/delete', methods=['POST'])
@require_login
def delete_server(server_name):
    """Delete a specific server"""
    server = get_server_by_name(current_user.id, server_name)
    if not server:
        abort(404)

    user_id = server.user_id  # Store user_id before deletion
    delete_entity(server)

    # Update the server definitions CID after deletion
    update_server_definitions_cid(user_id)

    flash(f'Server "{server_name}" deleted successfully!', 'success')
    return redirect(url_for('main.servers'))

def user_variables():
    return get_user_variables(current_user.id)

@main_bp.route('/variables')
@require_login
def variables():
    """Display user's variables"""
    variables_list = user_variables()
    variable_definitions_cid = get_current_variable_definitions_cid(current_user.id) if variables_list else None
    return render_template('variables.html', variables=variables_list, variable_definitions_cid=variable_definitions_cid)

@main_bp.route('/variables/new', methods=['GET', 'POST'])
@require_login
def new_variable():
    """Create a new variable"""
    form = VariableForm()

    if form.validate_on_submit():
        if create_entity(Variable, form, current_user.id, 'variable'):
            return redirect(url_for('main.variables'))

    return render_template('variable_form.html', form=form, title='Create New Variable')

@main_bp.route('/variables/<variable_name>')
@require_login
def view_variable(variable_name):
    """View a specific variable"""
    variable = get_variable_by_name(current_user.id, variable_name)
    if not variable:
        abort(404)

    return render_template('variable_view.html', variable=variable)

@main_bp.route('/variables/<variable_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_variable(variable_name):
    """Edit a specific variable"""
    variable = get_variable_by_name(current_user.id, variable_name)
    if not variable:
        abort(404)

    form = VariableForm(obj=variable)

    if form.validate_on_submit():
        if update_entity(variable, form, 'variable'):
            return redirect(url_for('main.view_variable', variable_name=variable.name))
        else:
            return render_template('variable_form.html', form=form, title=f'Edit Variable "{variable.name}"', variable=variable)

    return render_template('variable_form.html', form=form, title=f'Edit Variable "{variable.name}"', variable=variable)

@main_bp.route('/variables/<variable_name>/delete', methods=['POST'])
@require_login
def delete_variable(variable_name):
    """Delete a specific variable"""
    variable = get_variable_by_name(current_user.id, variable_name)
    if not variable:
        abort(404)

    delete_entity(variable)

    # Update variable definitions CID after deletion
    update_variable_definitions_cid(current_user.id)

    flash(f'Variable "{variable_name}" deleted successfully!', 'success')
    return redirect(url_for('main.variables'))

def user_secrets():
    return get_user_secrets(current_user.id)

# ============================================================================
# CRUD OPERATION HELPERS

# ============================================================================

def check_name_exists(model_class, name, user_id, exclude_id=None):
    """Check if a name already exists for a user, optionally excluding a specific record"""
    if model_class.__name__ == 'Server':
        entity = get_server_by_name(user_id, name)
    elif model_class.__name__ == 'Variable':
        entity = get_variable_by_name(user_id, name)
    elif model_class.__name__ == 'Secret':
        entity = get_secret_by_name(user_id, name)
    else:
        entity = None
    if entity and exclude_id and getattr(entity, 'id', None) == exclude_id:
        return False
    return entity is not None

def create_entity(model_class, form, user_id, entity_type):
    """Generic function to create a new entity (server, variable, or secret)"""
    if check_name_exists(model_class, form.name.data, user_id):
        flash(f'A {entity_type} named "{form.name.data}" already exists', 'danger')
        return False

    # Create entity with basic fields
    entity_data = {
        'name': form.name.data,
        'definition': form.definition.data,
        'user_id': user_id
    }

    # If this is a Server, save definition as CID
    if model_class.__name__ == 'Server':
        definition_cid = save_server_definition_as_cid(form.definition.data, user_id)
        entity_data['definition_cid'] = definition_cid

    entity = model_class(**entity_data)
    save_entity(entity)

    # Update the appropriate definitions CID
    if model_class.__name__ == 'Server':
        update_server_definitions_cid(user_id)
    elif model_class.__name__ == 'Variable':
        update_variable_definitions_cid(user_id)
    elif model_class.__name__ == 'Secret':
        update_secret_definitions_cid(user_id)

    flash(f'{entity_type.title()} "{form.name.data}" created successfully!', 'success')
    return True

def update_entity(entity, form, entity_type):
    """Generic function to update an entity (server, variable, or secret)"""
    # Check if new name conflicts with existing entity (if name changed)
    if form.name.data != entity.name:
        if check_name_exists(type(entity), form.name.data, entity.user_id, entity.id):
            flash(f'A {entity_type} named "{form.name.data}" already exists', 'danger')
            return False

    # If this is a Server and definition changed, save new definition as CID
    if type(entity).__name__ == 'Server':
        # Check if definition actually changed to avoid unnecessary CID generation
        if form.definition.data != entity.definition:
            definition_cid = save_server_definition_as_cid(form.definition.data, entity.user_id)
            entity.definition_cid = definition_cid

    entity.name = form.name.data
    entity.definition = form.definition.data
    entity.updated_at = datetime.now(timezone.utc)

    save_entity(entity)

    # Update the appropriate definitions CID
    if type(entity).__name__ == 'Server':
        update_server_definitions_cid(entity.user_id)
    elif type(entity).__name__ == 'Variable':
        update_variable_definitions_cid(entity.user_id)
    elif type(entity).__name__ == 'Secret':
        update_secret_definitions_cid(entity.user_id)

    flash(f'{entity_type.title()} "{entity.name}" updated successfully!', 'success')
    return True

# ============================================================================
# REQUEST PROCESSING HELPERS
# ============================================================================

def gather_request_info():
    """Gather comprehensive HTTP request information"""
    return {
        'method': request.method,
        'url': request.url,
        'path': request.path,
        'query_string': request.query_string.decode('utf-8'),
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string,
        'headers': dict(request.headers),
        'form_data': dict(request.form) if request.form else {},
        'args': dict(request.args) if request.args else {},
        'endpoint': request.endpoint,
        'blueprint': request.blueprint,
        'scheme': request.scheme,
        'host': request.host,
        'environ_vars': {
            'HTTP_X_FORWARDED_FOR': request.environ.get('HTTP_X_FORWARDED_FOR'),
            'HTTP_X_REAL_IP': request.environ.get('HTTP_X_REAL_IP'),
            'HTTP_REFERER': request.environ.get('HTTP_REFERER'),
            'HTTP_ACCEPT_LANGUAGE': request.environ.get('HTTP_ACCEPT_LANGUAGE'),
            'HTTP_ACCEPT_ENCODING': request.environ.get('HTTP_ACCEPT_ENCODING'),
        }
    }

def handle_pending_authentication(invitation_code):
    """Handle pending authentication with invitation code"""
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
        except ValueError as e:
            flash(f'Error: {str(e)}', 'danger')
            return None
@main_bp.route('/secrets')
@require_login
def secrets():
    """Display user's secrets"""
    secrets_list = user_secrets()
    secret_definitions_cid = get_current_secret_definitions_cid(current_user.id) if secrets_list else None
    return render_template('secrets.html', secrets=secrets_list, secret_definitions_cid=secret_definitions_cid)

@main_bp.route('/secrets/new', methods=['GET', 'POST'])
@require_login
def new_secret():
    """Create a new secret"""
    form = SecretForm()

    if form.validate_on_submit():
        if create_entity(Secret, form, current_user.id, 'secret'):
            return redirect(url_for('main.secrets'))

    return render_template('secret_form.html', form=form, title='Create New Secret')

@main_bp.route('/secrets/<secret_name>')
@require_login
def view_secret(secret_name):
    """View a specific secret"""
    secret = get_secret_by_name(current_user.id, secret_name)
    if not secret:
        abort(404)

    return render_template('secret_view.html', secret=secret)

@main_bp.route('/secrets/<secret_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_secret(secret_name):
    """Edit a specific secret"""
    secret = get_secret_by_name(current_user.id, secret_name)
    if not secret:
        abort(404)

    form = SecretForm(obj=secret)

    if form.validate_on_submit():
        if update_entity(secret, form, 'secret'):
            return redirect(url_for('main.view_secret', secret_name=secret.name))
        else:
            return render_template('secret_form.html', form=form, title=f'Edit Secret "{secret.name}"', secret=secret)

    return render_template('secret_form.html', form=form, title=f'Edit Secret "{secret.name}"', secret=secret)

@main_bp.route('/secrets/<secret_name>/delete', methods=['POST'])
@require_login
def delete_secret(secret_name):
    """Delete a specific secret"""
    secret = get_secret_by_name(current_user.id, secret_name)
    if not secret:
        abort(404)

    delete_entity(secret)

    # Update secret definitions CID after deletion
    update_secret_definitions_cid(current_user.id)

    flash(f'Secret "{secret_name}" deleted successfully!', 'success')
    return redirect(url_for('main.secrets'))

# ============================================================================
# SETTINGS DATA HELPERS
# ============================================================================

def get_user_settings_counts(user_id):
    """Get counts of user's servers, variables, and secrets for settings display"""
    return {
        'server_count': count_user_servers(user_id),
        'variable_count': count_user_variables(user_id),
        'secret_count': count_user_secrets(user_id)
    }

@main_bp.route('/settings')
@require_login
def settings():
    """Settings page with links to servers, variables, and secrets"""
    counts = get_user_settings_counts(current_user.id)
    return render_template('settings.html', **counts)

@main_bp.route('/meta/<cid>')
def meta_cid(cid):
    """Serve metadata about a CID as JSON"""
    # Look up the CID in the database
    cid_record = get_cid_by_path(f"/{cid}")

    if not cid_record:
        return jsonify({'error': 'CID not found'}), 404

    # Build metadata response
    metadata = {
        'cid': cid,
        'path': cid_record.path,
        'file_size': cid_record.file_size,
        'created_at': cid_record.created_at.isoformat() if cid_record.created_at else None,
        'uploaded_by_user_id': cid_record.uploaded_by_user_id
    }

    # Add uploader information if available
    if cid_record.uploaded_by:
        metadata['uploaded_by'] = {
            'user_id': cid_record.uploaded_by.id,
            'username': cid_record.uploaded_by.username,
            'email': cid_record.uploaded_by.email
        }

    return jsonify(metadata)


# ============================================================================
# ERROR HANDLING HELPERS
# ============================================================================

def get_existing_routes():
    """Get set of existing routes that should take precedence over server names"""
    return {
        '/', '/dashboard', '/profile', '/subscribe', '/accept-terms', '/content',
        '/plans', '/terms', '/privacy', '/upload', '/invitations', '/create-invitation',
        '/require-invitation', '/uploads', '/history', '/servers', '/variables',
        '/secrets', '/settings'
    }

@main_bp.app_errorhandler(404)
def not_found_error(error):
    """Custom 404 handler that checks CID table and server names for content"""
    path = request.path
    existing_routes = get_existing_routes()

    # First, check if this is a versioned server invocation like /{server_name}/{partial_CID}
    if is_potential_versioned_server_path(path, existing_routes):
        server_result = try_server_execution_with_partial(path, get_server_definition_history)
        if server_result is not None:
            return server_result

    # Check if this could be a server name and try to execute it
    if is_potential_server_path(path, existing_routes):
        server_result = try_server_execution(path)
        if server_result:
            return server_result

    # Look up the path in the CID table
    # Strip extension for CID lookup since CIDs are stored without extensions
    base_path = path.split('.')[0] if '.' in path else path
    cid_content = get_cid_by_path(base_path)
    if cid_content:
        result = serve_cid_content(cid_content, path)
        if result is not None:
            return result

    # If no content found, show 404 with the path
    return render_template('404.html', path=path), 404

@main_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
