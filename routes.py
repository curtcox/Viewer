from datetime import datetime, timedelta, timezone
from flask import render_template, flash, redirect, url_for, request, session
from flask_login import current_user
from app import app, db
from models import Payment, TermsAcceptance, CID, Invitation, PageView, Server, Variable, Secret, CURRENT_TERMS_VERSION
from forms import PaymentForm, TermsAcceptanceForm, FileUploadForm, InvitationForm, InvitationCodeForm, ServerForm, VariableForm, SecretForm
from auth_providers import require_login, auth_manager, save_user_from_claims
from secrets import token_urlsafe
import hashlib
import base64
from flask import make_response, abort
import traceback
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

# ============================================================================
# PROFILE DATA HELPERS
# ============================================================================

def get_user_profile_data(user_id):
    """Gather all profile-related data for a user"""
    payments = Payment.query.filter_by(user_id=user_id).order_by(Payment.payment_date.desc()).all()
    terms_history = TermsAcceptance.query.filter_by(user_id=user_id).order_by(TermsAcceptance.accepted_at.desc()).all()
    
    # Check if user needs to accept current terms
    current_terms_accepted = TermsAcceptance.query.filter_by(
        user_id=user_id,
        terms_version=CURRENT_TERMS_VERSION
    ).first()
    
    needs_terms_acceptance = current_terms_accepted is None
    
    return {
        'payments': payments,
        'terms_history': terms_history,
        'needs_terms_acceptance': needs_terms_acceptance,
        'current_terms_version': CURRENT_TERMS_VERSION
    }

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

        payment = create_payment_record(plan, amount, current_user.id)
        db.session.add(payment)
        db.session.commit()

        flash(f'Successfully subscribed to {plan.title()} plan!', 'success')
        return redirect(url_for('profile'))

    return render_template('subscribe.html', form=form)

@app.route('/accept-terms', methods=['GET', 'POST'])
@require_login
def accept_terms():
    """Handle terms and conditions acceptance"""
    form = TermsAcceptanceForm()
    if form.validate_on_submit():
        # Check if user already accepted current terms
        existing = TermsAcceptance.query.filter_by(
            user_id=current_user.id,
            terms_version=CURRENT_TERMS_VERSION
        ).first()

        if not existing:
            terms_acceptance = create_terms_acceptance_record(current_user.id)
            current_user.current_terms_accepted = True

            db.session.add(terms_acceptance)
            db.session.commit()

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
    """Process file upload from form and return file content"""
    uploaded_file = form.file.data
    file_content = uploaded_file.read()
    return file_content

def process_text_upload(form):
    """Process text upload from form and return file content"""
    text_content = form.text_content.data
    file_content = text_content.encode('utf-8')
    return file_content

def create_cid_record(cid, file_content, user_id):
    """Create and return a CID record for the database"""
    return CID(
        path=f"/{cid}",
        file_data=file_content,  # Store the actual file bytes
        file_size=len(file_content),
        uploaded_by_user_id=user_id  # Track who uploaded the file
    )

@app.route('/upload', methods=['GET', 'POST'])
@require_login
def upload():
    """File upload page with IPFS CID storage - supports both file upload and text input"""
    form = FileUploadForm()

    if form.validate_on_submit():
        if form.upload_type.data == 'file':
            file_content = process_file_upload(form)
        else:
            file_content = process_text_upload(form)

        # Generate IPFS-like CID
        cid = generate_cid(file_content)

        # Store actual file bytes and metadata in CID table
        file_record = create_cid_record(cid, file_content, current_user.id)

        # Check if CID already exists
        existing = CID.query.filter_by(path=f"/{cid}").first()
        if existing:
            flash(f'Content with this hash already exists! CID: {cid}', 'warning')
        else:
            db.session.add(file_record)
            db.session.commit()
            flash(f'Content uploaded successfully! CID: {cid}', 'success')

        return render_template('upload_success.html',
                             cid=cid,
                             file_size=len(file_content))

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
        invitation_code = token_urlsafe(16)

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
    user_uploads = CID.query.filter_by(uploaded_by_user_id=current_user.id).order_by(CID.created_at.desc()).all()

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
    return Server.query.filter_by(user_id=current_user.id).order_by(Server.name).all()

@app.route('/servers')
@require_login
def servers():
    """Display user's servers"""
    return render_template('servers.html', servers=user_servers())

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
    server = Server.query.filter_by(user_id=current_user.id, name=server_name).first()
    if not server:
        abort(404)

    return render_template('server_view.html', server=server)

@app.route('/servers/<server_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_server(server_name):
    """Edit a specific server"""
    server = Server.query.filter_by(user_id=current_user.id, name=server_name).first()
    if not server:
        abort(404)

    form = ServerForm(obj=server)

    if form.validate_on_submit():
        if update_entity(server, form, 'server'):
            return redirect(url_for('view_server', server_name=server.name))
        else:
            return render_template('server_form.html', form=form, title=f'Edit Server "{server.name}"', server=server)

    return render_template('server_form.html', form=form, title=f'Edit Server "{server.name}"', server=server)

@app.route('/servers/<server_name>/delete', methods=['POST'])
@require_login
def delete_server(server_name):
    """Delete a specific server"""
    server = Server.query.filter_by(user_id=current_user.id, name=server_name).first()
    if not server:
        abort(404)

    db.session.delete(server)
    db.session.commit()
    flash(f'Server "{server_name}" deleted successfully!', 'success')
    return redirect(url_for('servers'))

def user_variables():
    return Variable.query.filter_by(user_id=current_user.id).order_by(Variable.name).all()

@app.route('/variables')
@require_login
def variables():
    """Display user's variables"""
    return render_template('variables.html', variables=user_variables())

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
    variable = Variable.query.filter_by(user_id=current_user.id, name=variable_name).first()
    if not variable:
        abort(404)

    return render_template('variable_view.html', variable=variable)

@app.route('/variables/<variable_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_variable(variable_name):
    """Edit a specific variable"""
    variable = Variable.query.filter_by(user_id=current_user.id, name=variable_name).first()
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
    variable = Variable.query.filter_by(user_id=current_user.id, name=variable_name).first()
    if not variable:
        abort(404)

    db.session.delete(variable)
    db.session.commit()
    flash(f'Variable "{variable_name}" deleted successfully!', 'success')
    return redirect(url_for('variables'))

def user_secrets():
    return Secret.query.filter_by(user_id=current_user.id).order_by(Secret.name).all()

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

def build_request_args():
    """Build request arguments dictionary for server execution"""
    return {
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
        'environ': request.environ,
        'variables': model_as_dict(user_variables()),
        'secrets': model_as_dict(user_secrets()),
        'servers': model_as_dict(user_servers()),
    }

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
        
        # Store result in CID table
        cid_record = CID(
            path=f"/{cid}",
            file_data=output_bytes,
            file_size=len(output_bytes),
            uploaded_by_user_id=current_user.id
        )
        
        # Check if CID already exists
        existing = CID.query.filter_by(path=f"/{cid}").first()
        if not existing:
            db.session.add(cid_record)
            db.session.commit()
        
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

    # Immutable content caching headers
    response.headers['ETag'] = etag
    response.headers['Last-Modified'] = cid_content.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'  # 1 year
    response.headers['Expires'] = 'Thu, 31 Dec 2037 23:55:55 GMT'  # Far future

    # Add content disposition header for downloads if it's not a web-displayable type
    if not content_type.startswith(('text/', 'image/', 'video/', 'audio/')):
        response.headers['Content-Disposition'] = f'attachment; filename="{cid}"'

    return response

# ============================================================================
# CRUD OPERATION HELPERS
# ============================================================================

def check_name_exists(model_class, name, user_id, exclude_id=None):
    """Check if a name already exists for a user, optionally excluding a specific record"""
    query = model_class.query.filter_by(user_id=user_id, name=name)
    if exclude_id:
        query = query.filter(model_class.id != exclude_id)
    return query.first() is not None

def create_entity(model_class, form, user_id, entity_type):
    """Generic function to create a new entity (server, variable, or secret)"""
    if check_name_exists(model_class, form.name.data, user_id):
        flash(f'A {entity_type} named "{form.name.data}" already exists', 'danger')
        return False
    
    entity = model_class(
        name=form.name.data,
        definition=form.definition.data,
        user_id=user_id
    )
    db.session.add(entity)
    db.session.commit()
    flash(f'{entity_type.title()} "{form.name.data}" created successfully!', 'success')
    return True

def update_entity(entity, form, entity_type):
    """Generic function to update an entity (server, variable, or secret)"""
    # Check if new name conflicts with existing entity (if name changed)
    if form.name.data != entity.name:
        if check_name_exists(type(entity), form.name.data, entity.user_id, entity.id):
            flash(f'A {entity_type} named "{form.name.data}" already exists', 'danger')
            return False
    
    entity.name = form.name.data
    entity.definition = form.definition.data
    entity.updated_at = datetime.now(timezone.utc)
    db.session.commit()
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

# ============================================================================
# BUSINESS LOGIC HELPERS
# ============================================================================

def create_payment_record(plan, amount, user_id):
    """Create a payment record and update user subscription status"""
    payment = Payment()
    payment.user_id = user_id
    payment.amount = amount
    payment.plan_type = plan
    
    if plan == 'annual':
        payment.expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        current_user.is_paid = True
        current_user.payment_expires_at = payment.expires_at
    else:
        # Free plan
        current_user.is_paid = False
        current_user.payment_expires_at = None

    payment.transaction_id = f"mock_txn_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    return payment

# Invitation handling
def validate_invitation_code(invitation_code):
    """Validate an invitation code and return the invitation if valid"""
    invitation = Invitation.query.filter_by(invitation_code=invitation_code).first()
    return invitation if invitation and invitation.is_valid() else None

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
    return None

def create_terms_acceptance_record(user_id):
    """Create a terms acceptance record for the user"""
    terms_acceptance = TermsAcceptance()
    terms_acceptance.user_id = user_id
    terms_acceptance.terms_version = CURRENT_TERMS_VERSION
    terms_acceptance.ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    return terms_acceptance

@app.route('/secrets')
@require_login
def secrets():
    """Display user's secrets"""
    return render_template('secrets.html', secrets=user_secrets())

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
    secret = Secret.query.filter_by(user_id=current_user.id, name=secret_name).first()
    if not secret:
        abort(404)

    return render_template('secret_view.html', secret=secret)

@app.route('/secrets/<secret_name>/edit', methods=['GET', 'POST'])
@require_login
def edit_secret(secret_name):
    """Edit a specific secret"""
    secret = Secret.query.filter_by(user_id=current_user.id, name=secret_name).first()
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
    secret = Secret.query.filter_by(user_id=current_user.id, name=secret_name).first()
    if not secret:
        abort(404)

    db.session.delete(secret)
    db.session.commit()
    flash(f'Secret "{secret_name}" deleted successfully!', 'success')
    return redirect(url_for('secrets'))

# ============================================================================
# SETTINGS DATA HELPERS
# ============================================================================

def get_user_settings_counts(user_id):
    """Get counts of user's servers, variables, and secrets for settings display"""
    return {
        'server_count': Server.query.filter_by(user_id=user_id).count(),
        'variable_count': Variable.query.filter_by(user_id=user_id).count(),
        'secret_count': Secret.query.filter_by(user_id=user_id).count()
    }

@app.route('/settings')
@require_login
def settings():
    """Settings page with links to servers, variables, and secrets"""
    counts = get_user_settings_counts(current_user.id)
    return render_template('settings.html', **counts)


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
    server = Server.query.filter_by(user_id=current_user.id, name=potential_server_name).first()
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
    cid_content = CID.query.filter_by(path=base_path).first()
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
