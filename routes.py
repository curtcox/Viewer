from datetime import datetime, timedelta, timezone
from flask import render_template, flash, redirect, url_for, request, session, jsonify, make_response, abort
from flask_login import current_user
from app import app, db
from models import Invitation, PageView, Server, Variable, Secret, CURRENT_TERMS_VERSION, ServerInvocation
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
    create_server_invocation,
    get_cid_by_path,
    create_cid_record,
    get_user_uploads,
)
from forms import PaymentForm, TermsAcceptanceForm, FileUploadForm, InvitationForm, InvitationCodeForm, ServerForm, VariableForm, SecretForm
from auth_providers import require_login, auth_manager, save_user_from_claims
from secrets import token_urlsafe as secrets_token_urlsafe
import hashlib
import base64
import traceback
import json
from text_function_runner import run_text_function

# Make authentication info available to all templates
@app.context_processor
def inject_auth_info():
    return dict(
        AUTH_AVAILABLE=auth_manager.is_authentication_available(),
        AUTH_PROVIDER=auth_manager.get_provider_name(),
        LOGIN_URL=auth_manager.get_login_url(),
        LOGOUT_URL=auth_manager.get_logout_url()
    )

# Make session permanent and track page views
@app.before_request
def make_session_permanent():
    session.permanent = True

# ============================================================================
# PAGE VIEW TRACKING HELPERS
# ============================================================================

def should_track_page_view(response):
    """Determine if the current request should be tracked"""
    if not current_user.is_authenticated or response.status_code != 200:
        return False

    # Skip tracking for static files, API calls, and certain paths
    skip_paths = ['/static/', '/favicon.ico', '/robots.txt', '/api/', '/_']
    if any(request.path.startswith(skip) for skip in skip_paths):
        return False

    # Skip tracking AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return False

    return True

def create_page_view_record():
    """Create a page view record for the current request"""
    return PageView(
        user_id=current_user.id,
        path=request.path,
        method=request.method,
        user_agent=request.headers.get('User-Agent', '')[:500],
        ip_address=request.remote_addr
    )

@app.after_request
def track_page_view(response):
    """Track page views for authenticated users"""
    try:
        if should_track_page_view(response):
            page_view = create_page_view_record()
            db.session.add(page_view)
            db.session.commit()
    except Exception:
        # Don't let tracking errors break the request
        db.session.rollback()

    return response

@app.route('/')
def index():
    """Landing page - shows different content based on user status"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@require_login
def dashboard():
    """User dashboard - redirects based on access level"""
    if current_user.has_access():
        return redirect(url_for('content'))
    return redirect(url_for('profile'))

@app.route('/profile')
@require_login
def profile():
    """User profile showing payment history and terms acceptance"""
    profile_data = get_user_profile_data(current_user.id)
    return render_template('profile.html', **profile_data)

@app.route('/subscribe', methods=['GET', 'POST'])
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
        return redirect(url_for('profile'))

    return render_template('subscribe.html', form=form)

@app.route('/accept-terms', methods=['GET', 'POST'])
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
        return redirect(url_for('profile'))

    return render_template('accept_terms.html', form=form, terms_version=CURRENT_TERMS_VERSION)

@app.route('/content')
@require_login
def content():
    """Protected content area - displays HTTP request details"""
    if not current_user.has_access():
        flash('Access denied. Please ensure you have an active subscription and have accepted the current terms and conditions.', 'warning')
        return redirect(url_for('profile'))

    request_info = gather_request_info()
    return render_template('content.html', request_info=request_info)

@app.route('/plans')
def plans():
    """Display pricing plans"""
    return render_template('plans.html')

@app.route('/terms')
def terms():
    """Display terms and conditions"""
    return render_template('terms.html', current_version=CURRENT_TERMS_VERSION)

@app.route('/privacy')
def privacy():
    """Display privacy policy"""
    return render_template('privacy.html')

# ============================================================================
# FILE UPLOAD AND CID HELPERS
# ============================================================================

def generate_cid(file_data):
    """Generate a simple CID-like hash from file data only"""
    # Create SHA-256 hash of the file content only
    hasher = hashlib.sha256()
    hasher.update(file_data)
    sha256_hash = hasher.digest()

    # Encode to base64 and create a CID-like string
    encoded = base64.b32encode(sha256_hash).decode('ascii').lower().rstrip('=')
    # Add CID prefix to make it look like an IPFS CID
    return f"bafybei{encoded[:52]}"  # Truncate to reasonable length

def process_file_upload(form):
    """Process file upload from form and return file content and filename"""
    uploaded_file = form.file.data
    file_content = uploaded_file.read()
    filename = uploaded_file.filename or 'upload'
    return file_content, filename

def process_text_upload(form):
    """Process text upload from form and return file content"""
    text_content = form.text_content.data
    file_content = text_content.encode('utf-8')
    return file_content

def process_url_upload(form):
    """Process URL upload from form by downloading content and return file content and MIME type"""
    import requests
    from urllib.parse import urlparse

    url = form.url.data.strip()

    try:
        # Set reasonable timeout and headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, timeout=30, headers=headers, stream=True)
        response.raise_for_status()

        # Get MIME type from response headers
        content_type = response.headers.get('content-type', 'application/octet-stream')
        # Clean up MIME type (remove charset and other parameters)
        mime_type = content_type.split(';')[0].strip().lower()

        # Check content length to avoid downloading huge files
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError("File too large (>100MB)")

        # Download content in chunks to handle large files efficiently
        file_content = b''
        downloaded_size = 0
        max_size = 100 * 1024 * 1024  # 100MB limit

        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                downloaded_size += len(chunk)
                if downloaded_size > max_size:
                    raise ValueError("File too large (>100MB)")
                file_content += chunk

        # Extract filename from URL for potential future use
        parsed_url = urlparse(url)
        filename = parsed_url.path.split('/')[-1]

        # If no filename from URL or no extension, use MIME type to determine extension
        if not filename or '.' not in filename:
            extension = get_extension_from_mime_type(mime_type)
            if extension:
                filename = f"download{extension}"
            else:
                filename = "download"

        return file_content, mime_type

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to download from URL: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing URL: {str(e)}")
def save_server_definition_as_cid(definition, user_id):
    """Save server definition as CID and return the CID string"""
    # Convert definition to bytes
    definition_bytes = definition.encode('utf-8')

    # Generate CID for the definition
    cid = generate_cid(definition_bytes)

    # Check if CID already exists to avoid duplicates
    existing_cid = get_cid_by_path(f"/{cid}")
    if not existing_cid:
        create_cid_record(cid, definition_bytes, user_id)

    return cid

# ============================================================================
# SERVER DEFINITIONS CID HELPERS
# ============================================================================

def get_server_definition_history(user_id, server_name):
    """Get historical server definitions for a specific server, ordered by time (latest first)"""
    from models import CID, db
    
    # Get all CIDs that contain server definitions for this user
    # We need to check the content of each CID to see if it contains the server
    cids = db.session.query(CID).filter(
        CID.uploaded_by_user_id == user_id
    ).order_by(CID.created_at.desc()).all()
    
    history = []
    
    for cid in cids:
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

def generate_all_server_definitions_json(user_id):
    """Generate JSON containing all server definitions for a user"""
    servers = get_user_servers(user_id)

    # Create dictionary with server names as keys and definitions as values
    server_definitions = {}
    for server in servers:
        server_definitions[server.name] = server.definition

    # Convert to JSON string
    return json.dumps(server_definitions, indent=2, sort_keys=True)

def store_cid_from_json(json_content, user_id):
    """Store all server definitions as JSON in a CID and return the CID path"""
    json_bytes = json_content.encode('utf-8')

    # Generate CID for the JSON content
    cid = generate_cid(json_bytes)

    # Check if CID already exists to avoid duplicates
    existing_cid = get_cid_by_path(f"/{cid}")
    if not existing_cid:
        create_cid_record(cid, json_bytes, user_id)

    return cid

def store_server_definitions_cid(user_id):
    """Store all server definitions as JSON in a CID and return the CID path"""
    json_content = generate_all_server_definitions_json(user_id)
    return store_cid_from_json(json_content, user_id)

def get_current_server_definitions_cid(user_id):
    """Get the CID path for the current server definitions JSON"""
    # Generate what the current CID should be based on current servers
    json_content = generate_all_server_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    expected_cid = generate_cid(json_bytes)

    # Check if this CID exists in the database
    existing_cid = get_cid_by_path(f"/{expected_cid}")
    if existing_cid:
        return expected_cid
    else:
        # If it doesn't exist, create it
        return store_server_definitions_cid(user_id)

def update_server_definitions_cid(user_id):
    """Update the server definitions CID after server changes"""
    return store_server_definitions_cid(user_id)

# ============================================================================
# VARIABLE DEFINITIONS CID HELPERS
# ============================================================================

def generate_all_variable_definitions_json(user_id):
    """Generate JSON containing all variable definitions for a user"""
    variables = get_user_variables(user_id)

    # Create dictionary with variable names as keys and definitions as values
    variable_definitions = {}
    for variable in variables:
        variable_definitions[variable.name] = variable.definition

    # Convert to JSON string
    return json.dumps(variable_definitions, indent=2, sort_keys=True)

def store_variable_definitions_cid(user_id):
    """Store all variable definitions as JSON in a CID and return the CID path"""
    json_content = generate_all_variable_definitions_json(user_id)
    return store_cid_from_json(json_content, user_id)

def get_current_variable_definitions_cid(user_id):
    """Get the CID path for the current variable definitions JSON"""
    # Generate what the current CID should be based on current variables
    json_content = generate_all_variable_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    expected_cid = generate_cid(json_bytes)

    # Check if this CID exists in the database
    existing_cid = get_cid_by_path(f"/{expected_cid}")
    if existing_cid:
        return expected_cid
    else:
        # If it doesn't exist, create it
        return store_variable_definitions_cid(user_id)

def update_variable_definitions_cid(user_id):
    """Update the variable definitions CID after variable changes"""
    return store_variable_definitions_cid(user_id)

# ============================================================================
# SERVER DEFINITIONS CID HELPERS
# ============================================================================

def generate_all_secret_definitions_json(user_id):
    """Generate JSON containing all secret definitions for a user"""
    secrets = get_user_secrets(user_id)

    # Create dictionary with secret names as keys and definitions as values
    secret_definitions = {}
    for secret in secrets:
        secret_definitions[secret.name] = secret.definition

    # Convert to JSON string
    return json.dumps(secret_definitions, indent=2, sort_keys=True)

def store_secret_definitions_cid(user_id):
    """Store all secret definitions as JSON in a CID and return the CID path"""
    json_content = generate_all_secret_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')

    # Generate CID for the JSON content
    cid = generate_cid(json_bytes)

    # Check if CID already exists to avoid duplicates
    existing_cid = get_cid_by_path(f"/{cid}")
    if not existing_cid:
        create_cid_record(cid, json_bytes, user_id)

    return cid

def get_current_secret_definitions_cid(user_id):
    """Get the CID path for the current secret definitions JSON"""
    # Generate what the current CID should be based on current secrets
    json_content = generate_all_secret_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    expected_cid = generate_cid(json_bytes)

    # Check if this CID exists in the database
    existing_cid = get_cid_by_path(f"/{expected_cid}")
    if existing_cid:
        return expected_cid
    else:
        # If it doesn't exist, create it
        return store_secret_definitions_cid(user_id)

def update_secret_definitions_cid(user_id):
    """Update the secret definitions CID after secret changes"""
    return store_secret_definitions_cid(user_id)

@app.route('/upload', methods=['GET', 'POST'])
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

@app.route('/invitations')
@require_login
def invitations():
    """Manage user invitations"""
    user_invitations = Invitation.query.filter_by(inviter_user_id=current_user.id).order_by(Invitation.created_at.desc()).all()
    return render_template('invitations.html', invitations=user_invitations)

@app.route('/create-invitation', methods=['GET', 'POST'])
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
        return redirect(url_for('invitations'))

    return render_template('create_invitation.html', form=form)

@app.route('/require-invitation', methods=['GET', 'POST'])
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

@app.route('/invite/<invitation_code>')
def accept_invitation(invitation_code):
    """Direct link to accept an invitation"""
    invitation = validate_invitation_code(invitation_code)

    if invitation:
        session['invitation_code'] = invitation_code
        flash('Invitation accepted! Please sign in to complete your registration.', 'success')
        return redirect(auth_manager.get_login_url())
    else:
        flash('Invalid or expired invitation link.', 'danger')
        return redirect(url_for('require_invitation'))

@app.route('/uploads')
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
# HISTORY AND STATISTICS HELPERS
# ============================================================================

def get_user_history_statistics(user_id):
    """Calculate history statistics for a user"""
    from sqlalchemy import func

    # Get total views count
    total_views = PageView.query.filter_by(user_id=user_id).count()

    # Get unique paths count
    unique_paths = db.session.query(func.count(func.distinct(PageView.path)))\
                            .filter_by(user_id=user_id).scalar()

    # Get most visited paths
    popular_paths = db.session.query(PageView.path, func.count(PageView.path).label('count'))\
                             .filter_by(user_id=user_id)\
                             .group_by(PageView.path)\
                             .order_by(func.count(PageView.path).desc())\
                             .limit(5).all()

    return {
        'total_views': total_views,
        'unique_paths': unique_paths,
        'popular_paths': popular_paths
    }

def get_paginated_page_views(user_id, page, per_page=50):
    """Get paginated page views for a user"""
    return PageView.query.filter_by(user_id=user_id)\
                        .order_by(PageView.viewed_at.desc())\
                        .paginate(page=page, per_page=per_page, error_out=False)

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

@app.route('/history')
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

@app.route('/servers')
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

@app.route('/servers/new', methods=['GET', 'POST'])
@require_login
def new_server():
    """Create a new server"""
    form = ServerForm()

    if form.validate_on_submit():
        if create_entity(Server, form, current_user.id, 'server'):
            return redirect(url_for('servers'))

    return render_template('server_form.html', form=form, title='Create New Server')

@app.route('/servers/<server_name>')
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

@app.route('/servers/<server_name>/edit', methods=['GET', 'POST'])
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
            return redirect(url_for('view_server', server_name=server.name))
        else:
            return render_template('server_form.html', form=form, title=f'Edit Server "{server.name}"', server=server, definition_history=history, server_invocations=invocations)

    return render_template('server_form.html', form=form, title=f'Edit Server "{server.name}"', server=server, definition_history=history, server_invocations=invocations)

@app.route('/servers/<server_name>/delete', methods=['POST'])
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
    return redirect(url_for('servers'))

def user_variables():
    return get_user_variables(current_user.id)

@app.route('/variables')
@require_login
def variables():
    """Display user's variables"""
    variables_list = user_variables()
    variable_definitions_cid = get_current_variable_definitions_cid(current_user.id) if variables_list else None
    return render_template('variables.html', variables=variables_list, variable_definitions_cid=variable_definitions_cid)

@app.route('/variables/new', methods=['GET', 'POST'])
@require_login
def new_variable():
    """Create a new variable"""
    form = VariableForm()

    if form.validate_on_submit():
        if create_entity(Variable, form, current_user.id, 'variable'):
            return redirect(url_for('variables'))

    return render_template('variable_form.html', form=form, title='Create New Variable')

@app.route('/variables/<variable_name>')
@require_login
def view_variable(variable_name):
    """View a specific variable"""
    variable = get_variable_by_name(current_user.id, variable_name)
    if not variable:
        abort(404)

    return render_template('variable_view.html', variable=variable)

@app.route('/variables/<variable_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_variable(variable_name):
    """Edit a specific variable"""
    variable = get_variable_by_name(current_user.id, variable_name)
    if not variable:
        abort(404)

    form = VariableForm(obj=variable)

    if form.validate_on_submit():
        if update_entity(variable, form, 'variable'):
            return redirect(url_for('view_variable', variable_name=variable.name))
        else:
            return render_template('variable_form.html', form=form, title=f'Edit Variable "{variable.name}"', variable=variable)

    return render_template('variable_form.html', form=form, title=f'Edit Variable "{variable.name}"', variable=variable)

@app.route('/variables/<variable_name>/delete', methods=['POST'])
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
    return redirect(url_for('variables'))

def user_secrets():
    return get_user_secrets(current_user.id)

# ============================================================================
# SERVER EXECUTION HELPERS
# ============================================================================

def model_as_dict(model_objects):
    """Convert SQLAlchemy model objects to dict with names as keys and definitions as values"""
    if not model_objects:
        return {}

    result = {}
    for obj in model_objects:
        if hasattr(obj, 'name') and hasattr(obj, 'definition'):
            # For Variable, Secret, and Server objects
            result[obj.name] = obj.definition
        else:
            # Fallback for other object types
            result[str(obj)] = str(obj)

    return result

def request_details():
    """Build request arguments for server execution"""
    return {
        'path': request.path,
        'query_string': request.query_string.decode('utf-8'),
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string,
        'headers': {k: v for k, v in request.headers if k.lower() != 'cookie'},
        'form_data': dict(request.form) if request.form else {},
        'args': dict(request.args) if request.args else {},
        'endpoint': request.endpoint,
        'scheme': request.scheme,
        'host': request.host,
        'method': request.method,
    }

def build_request_args():
    """Build request arguments for server execution"""
    context = {
        'variables': model_as_dict(user_variables()),
        'secrets': model_as_dict(user_secrets()),
        'servers': model_as_dict(user_servers()),
    }
    return {
        'request': request_details(),
        'context': context,
    }

def create_server_invocation_record(user_id, server_name, result_cid):
    """Create a ServerInvocation record to track server execution and current definitions"""
    servers_cid = get_current_server_definitions_cid(user_id)
    variables_cid = get_current_variable_definitions_cid(user_id)
    secrets_cid = get_current_secret_definitions_cid(user_id)

    # Build and store request details JSON as a CID
    try:
        req_details = request_details()
        req_json = json.dumps(req_details, indent=2, sort_keys=True)
        req_bytes = req_json.encode('utf-8')
        req_cid = generate_cid(req_bytes)
        if not get_cid_by_path(f"/{req_cid}"):
            create_cid_record(req_cid, req_bytes, user_id)
    except Exception:
        # If anything goes wrong, skip storing request details
        req_cid = None

    # Create base invocation record (without invocation_cid yet)
    invocation = create_server_invocation(
        user_id,
        server_name,
        result_cid,
        servers_cid=servers_cid,
        variables_cid=variables_cid,
        secrets_cid=secrets_cid,
        request_details_cid=req_cid,
        invocation_cid=None,
    )

    # Build the ServerInvocation JSON and store its CID, then update the record
    try:
        inv_payload = {
            'user_id': user_id,
            'server_name': server_name,
            'result_cid': result_cid,
            'servers_cid': servers_cid,
            'variables_cid': variables_cid,
            'secrets_cid': secrets_cid,
            'request_details_cid': req_cid,
            'invoked_at': invocation.invoked_at.isoformat() if invocation.invoked_at else None,
        }
        inv_json = json.dumps(inv_payload, indent=2, sort_keys=True)
        inv_bytes = inv_json.encode('utf-8')
        inv_cid = generate_cid(inv_bytes)
        if not get_cid_by_path(f"/{inv_cid}"):
            create_cid_record(inv_cid, inv_bytes, user_id)

        # Update the invocation with its JSON CID
        invocation.invocation_cid = inv_cid
        save_entity(invocation)
    except Exception:
        pass

    return invocation

def execute_server_code(server, server_name):
    """Execute server code and return CID redirect response or error response"""
    code = server.definition
    args = build_request_args()

    try:
        result = run_text_function(code, args)
        # Store the result in the CID table and redirect to the /<cid> URL
        output = result.get('output', '')
        content_type = result.get('content_type', 'text/html')

        # Convert output to bytes for CID generation
        if isinstance(output, str):
            output_bytes = output.encode('utf-8')
        else:
            output_bytes = output

        # Generate CID for the result
        cid = generate_cid(output_bytes)

        # Store result in CID table if it doesn't already exist
        existing = get_cid_by_path(f"/{cid}")
        if not existing:
            create_cid_record(cid, output_bytes, current_user.id)

        # Create ServerInvocation record to track this server execution
        create_server_invocation_record(current_user.id, server_name, cid)

        # Get appropriate extension for the content type
        extension = get_extension_from_mime_type(content_type)

        # Redirect to the CID URL with extension if available
        if extension:
            return redirect(f"/{cid}.{extension}")
        else:
            return redirect(f"/{cid}")
    except Exception as e:
        text = str(e) + "\n\n" + traceback.format_exc() + "\n\n" + code + "\n\n" + str(args)
        response = make_response(text)
        response.headers['Content-Type'] = 'text/plain'
        response.status_code = 500
        return response

# ============================================================================
# CID CONTENT SERVING HELPERS
# ============================================================================

# Shared MIME type and extension mappings
EXTENSION_TO_MIME = {
    'html': 'text/html',
    'htm': 'text/html',
    'txt': 'text/plain',
    'css': 'text/css',
    'js': 'application/javascript',
    'json': 'application/json',
    'xml': 'application/xml',
    'pdf': 'application/pdf',
    'zip': 'application/zip',
    'tar': 'application/x-tar',
    'gz': 'application/gzip',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'svg': 'image/svg+xml',
    'webp': 'image/webp',
    'ico': 'image/x-icon',
    'mp3': 'audio/mpeg',
    'wav': 'audio/wav',
    'ogg': 'audio/ogg',
    'mp4': 'video/mp4',
    'webm': 'video/webm',
    'avi': 'video/x-msvideo',
    'mov': 'video/quicktime',
    'md': 'text/markdown',
    'csv': 'text/csv',
    'py': 'text/x-python',
    'java': 'text/x-java-source',
    'c': 'text/x-c',
    'cpp': 'text/x-c++',
    'h': 'text/x-c',
    'hpp': 'text/x-c++',
    'sh': 'application/x-sh',
    'bat': 'application/x-msdos-program',
    'exe': 'application/x-msdownload',
    'dmg': 'application/x-apple-diskimage',
    'deb': 'application/vnd.debian.binary-package',
    'rpm': 'application/x-rpm'
}

# Create reverse mapping from MIME types to extensions
MIME_TO_EXTENSION = {}
for ext, mime in EXTENSION_TO_MIME.items():
    if mime not in MIME_TO_EXTENSION:
        # Use the first extension for each MIME type as the preferred one
        MIME_TO_EXTENSION[mime] = ext

def get_mime_type_from_extension(path):
    """Determine MIME type from file extension in URL path"""
    # Extract extension from path
    if '.' in path:
        extension = path.split('.')[-1].lower()
        return EXTENSION_TO_MIME.get(extension, 'application/octet-stream')
    # No extension, return default
    return 'application/octet-stream'

def get_extension_from_mime_type(content_type):
    """Get file extension from MIME type"""
    # Handle MIME types with parameters (e.g., "text/html; charset=utf-8")
    base_mime = content_type.split(';')[0].strip().lower()
    return MIME_TO_EXTENSION.get(base_mime, '')

def extract_filename_from_cid_path(path):
    """
    Extract filename from CID path for content disposition header.

    Rules:
    - /{CID} -> no filename (no content disposition)
    - /{CID}.{ext} -> no filename (no content disposition)
    - /{CID}.{filename}.{ext} -> filename = {filename}.{ext}
    """
    # Remove leading slash
    if path.startswith('/'):
        path = path[1:]

    # Handle empty or invalid paths
    if not path or path in ['.', '..']:
        return None

    # Split by dots
    parts = path.split('.')

    # Need at least 3 parts for filename: CID.filename.ext
    if len(parts) < 3:
        return None

    # First part is CID, rest form the filename
    filename_parts = parts[1:]
    filename = '.'.join(filename_parts)

    return filename

def serve_cid_content(cid_content, path):
    """Serve CID content with appropriate headers and caching"""
    # Check if file_data is None (corrupted or missing data)
    if cid_content is None or cid_content.file_data is None:
        return None  # Return None to indicate content not found, let caller handle 404

    # Extract CID from path (remove leading slash)
    cid = path[1:] if path.startswith('/') else path

    # Determine MIME type from URL extension
    content_type = get_mime_type_from_extension(path)

    # Check conditional requests using ETag (CID is perfect as ETag since it's content-based hash)
    etag = f'"{cid.split(".")[0]}"'  # Use base CID without extension for ETag
    if request.headers.get('If-None-Match') == etag:
        # Client has the file cached, return 304 Not Modified
        response = make_response('', 304)
        response.headers['ETag'] = etag
        return response

    # Check If-Modified-Since (though ETag is more reliable for immutable content)
    if request.headers.get('If-Modified-Since'):
        # Since content is immutable, we can always return 304 if they have any cached version
        response = make_response('', 304)
        response.headers['ETag'] = etag
        response.headers['Last-Modified'] = cid_content.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
        return response

    # Serve the file with aggressive caching headers
    response = make_response(cid_content.file_data)
    response.headers['Content-Type'] = content_type
    response.headers['Content-Length'] = len(cid_content.file_data)

    # Set content disposition header if filename is indicated in the path
    filename = extract_filename_from_cid_path(path)
    if filename:
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Immutable content caching headers
    response.headers['ETag'] = etag
    response.headers['Last-Modified'] = cid_content.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'  # 1 year
    response.headers['Expires'] = 'Thu, 31 Dec 2037 23:55:55 GMT'  # Far future

    return response

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
            return redirect(url_for('index'))
        except ValueError as e:
            flash(f'Error: {str(e)}', 'danger')
            return None
@app.route('/secrets')
@require_login
def secrets():
    """Display user's secrets"""
    secrets_list = user_secrets()
    secret_definitions_cid = get_current_secret_definitions_cid(current_user.id) if secrets_list else None
    return render_template('secrets.html', secrets=secrets_list, secret_definitions_cid=secret_definitions_cid)

@app.route('/secrets/new', methods=['GET', 'POST'])
@require_login
def new_secret():
    """Create a new secret"""
    form = SecretForm()

    if form.validate_on_submit():
        if create_entity(Secret, form, current_user.id, 'secret'):
            return redirect(url_for('secrets'))

    return render_template('secret_form.html', form=form, title='Create New Secret')

@app.route('/secrets/<secret_name>')
@require_login
def view_secret(secret_name):
    """View a specific secret"""
    secret = get_secret_by_name(current_user.id, secret_name)
    if not secret:
        abort(404)

    return render_template('secret_view.html', secret=secret)

@app.route('/secrets/<secret_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_secret(secret_name):
    """Edit a specific secret"""
    secret = get_secret_by_name(current_user.id, secret_name)
    if not secret:
        abort(404)

    form = SecretForm(obj=secret)

    if form.validate_on_submit():
        if update_entity(secret, form, 'secret'):
            return redirect(url_for('view_secret', secret_name=secret.name))
        else:
            return render_template('secret_form.html', form=form, title=f'Edit Secret "{secret.name}"', secret=secret)

    return render_template('secret_form.html', form=form, title=f'Edit Secret "{secret.name}"', secret=secret)

@app.route('/secrets/<secret_name>/delete', methods=['POST'])
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
    return redirect(url_for('secrets'))

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

@app.route('/settings')
@require_login
def settings():
    """Settings page with links to servers, variables, and secrets"""
    counts = get_user_settings_counts(current_user.id)
    return render_template('settings.html', **counts)

@app.route('/meta/<cid>')
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

def is_potential_server_path(path, existing_routes):
    """Check if path could be a server name (single segment, not existing route)"""
    return (path.startswith('/') and
            path.count('/') == 1 and
            path not in existing_routes)

def try_server_execution(path):
    """Try to execute server code if path matches a server name"""
    if not current_user.is_authenticated:
        return None

    # Extract potential server name (remove leading slash)
    potential_server_name = path[1:]

    # Check if this server name exists for the user
    server = get_server_by_name(current_user.id, potential_server_name)
    if server:
        return execute_server_code(server, potential_server_name)

    return None

@app.errorhandler(404)
def not_found_error(error):
    """Custom 404 handler that checks CID table and server names for content"""
    path = request.path
    existing_routes = get_existing_routes()

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

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
