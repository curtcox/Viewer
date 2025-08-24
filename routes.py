from datetime import datetime, timedelta
from flask import render_template, flash, redirect, url_for, request, session
from flask_login import current_user
from app import app, db
from models import User, Payment, TermsAcceptance, CID, Invitation, CURRENT_TERMS_VERSION
from forms import PaymentForm, TermsAcceptanceForm, FileUploadForm, InvitationForm, InvitationCodeForm
import secrets
import hashlib
import base64
from flask import make_response, abort
from replit_auth import require_login, make_replit_blueprint

app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

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
    payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.payment_date.desc()).all()
    terms_history = TermsAcceptance.query.filter_by(user_id=current_user.id).order_by(TermsAcceptance.accepted_at.desc()).all()
    
    # Check if user needs to accept current terms
    current_terms_accepted = TermsAcceptance.query.filter_by(
        user_id=current_user.id, 
        terms_version=CURRENT_TERMS_VERSION
    ).first()
    
    needs_terms_acceptance = current_terms_accepted is None
    
    return render_template('profile.html', 
                         payments=payments, 
                         terms_history=terms_history,
                         needs_terms_acceptance=needs_terms_acceptance,
                         current_terms_version=CURRENT_TERMS_VERSION)

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
        
        # Create mock payment record
        payment = Payment()
        payment.user_id = current_user.id
        payment.amount = amount
        payment.plan_type = plan
        if plan == 'annual':
            payment.expires_at = datetime.utcnow() + timedelta(days=365)
            current_user.is_paid = True
            current_user.payment_expires_at = payment.expires_at
        else:
            # Free plan
            current_user.is_paid = False
            current_user.payment_expires_at = None
        
        payment.transaction_id = f"mock_txn_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
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
            terms_acceptance = TermsAcceptance()
            terms_acceptance.user_id = current_user.id
            terms_acceptance.terms_version = CURRENT_TERMS_VERSION
            terms_acceptance.ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            
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
    
    # Gather comprehensive HTTP request information
    request_info = {
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

def generate_cid(file_data):
    """Generate a simple CID-like hash from file data"""
    # Create SHA-256 hash of the file content
    sha256_hash = hashlib.sha256(file_data).digest()
    # Encode to base64 and create a CID-like string
    encoded = base64.b32encode(sha256_hash).decode('ascii').lower().rstrip('=')
    # Add CID prefix to make it look like an IPFS CID
    return f"bafybei{encoded[:52]}"  # Truncate to reasonable length

@app.route('/upload', methods=['GET', 'POST'])
@require_login
def upload():
    """File upload page with IPFS CID storage"""
    form = FileUploadForm()
    
    if form.validate_on_submit():
        uploaded_file = form.file.data
        
        # Read file content
        file_content = uploaded_file.read()
        
        # Generate IPFS-like CID
        cid = generate_cid(file_content)
        
        # Store actual file bytes and metadata in CID table
        file_record = CID(
            path=f"/{cid}",
            title=form.title.data or f"Uploaded File: {uploaded_file.filename}",
            file_data=file_content,  # Store the actual file bytes
            content_type=uploaded_file.content_type or 'application/octet-stream',
            filename=uploaded_file.filename,
            file_size=len(file_content),
            uploaded_by_user_id=current_user.id  # Track who uploaded the file
        )
        
        # Check if CID already exists
        existing = CID.query.filter_by(path=f"/{cid}").first()
        if existing:
            flash(f'File with this content already exists! CID: {cid}', 'warning')
        else:
            db.session.add(file_record)
            db.session.commit()
            flash(f'File uploaded successfully! CID: {cid}', 'success')
        
        return render_template('upload_success.html', 
                             cid=cid, 
                             filename=uploaded_file.filename,
                             file_size=len(file_content),
                             title=form.title.data,
                             description=form.description.data)
    
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
        invitation_code = secrets.token_urlsafe(16)
        
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
        
        # Validate invitation
        invitation = Invitation.query.filter_by(invitation_code=invitation_code).first()
        
        if invitation and invitation.is_valid():
            # Store invitation code in session and retry authentication
            session['invitation_code'] = invitation_code
            
            # If we have pending auth, complete it
            if 'pending_token' in session and 'pending_user_claims' in session:
                token = session.pop('pending_token')
                user_claims = session.pop('pending_user_claims')
                
                try:
                    from replit_auth import save_user
                    user = save_user(user_claims, invitation_code)
                    session.pop('invitation_code', None)
                    
                    from flask_login import login_user
                    login_user(user)
                    
                    flash('Welcome! Your account has been created.', 'success')
                    return redirect(url_for('index'))
                except ValueError as e:
                    flash(f'Error: {str(e)}', 'danger')
            else:
                # Just store invitation for future auth attempt
                flash('Invitation validated! Please sign in.', 'success')
                return redirect(url_for('replit_auth.login'))
        else:
            flash('Invalid or expired invitation code.', 'danger')
    
    return render_template('require_invitation.html', form=form, error_message=error_message)

@app.route('/invite/<invitation_code>')
def accept_invitation(invitation_code):
    """Direct link to accept an invitation"""
    invitation = Invitation.query.filter_by(invitation_code=invitation_code).first()
    
    if invitation and invitation.is_valid():
        session['invitation_code'] = invitation_code
        flash('Invitation accepted! Please sign in to complete your registration.', 'success')
        return redirect(url_for('replit_auth.login'))
    else:
        flash('Invalid or expired invitation link.', 'danger')
        return redirect(url_for('require_invitation'))

@app.route('/uploads')
@require_login
def uploads():
    """Display user's uploaded files"""
    user_uploads = CID.query.filter_by(uploaded_by_user_id=current_user.id).order_by(CID.created_at.desc()).all()
    
    # Calculate total storage used
    total_storage = sum(upload.file_size or 0 for upload in user_uploads)
    
    return render_template('uploads.html', 
                         uploads=user_uploads,
                         total_uploads=len(user_uploads),
                         total_storage=total_storage)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Custom 404 handler that checks CID table for content"""
    path = request.path
    
    # Look up the path in the CID table
    cid_content = CID.query.filter_by(path=path).first()
    
    if cid_content:
        # If this is a file upload (has file_data), serve the raw bytes
        if cid_content.file_data:
            # Extract CID from path (remove leading slash)
            cid = path[1:] if path.startswith('/') else path
            
            # Check conditional requests using ETag (CID is perfect as ETag since it's content-based hash)
            etag = f'"{cid}"'
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
            response.headers['Content-Type'] = cid_content.content_type
            response.headers['Content-Length'] = len(cid_content.file_data)
            
            # Immutable content caching headers
            response.headers['ETag'] = etag
            response.headers['Last-Modified'] = cid_content.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'  # 1 year
            response.headers['Expires'] = 'Thu, 31 Dec 2037 23:55:55 GMT'  # Far future
            
            # Add content disposition header for downloads if it's not a web-displayable type
            if not cid_content.content_type.startswith(('text/', 'image/', 'video/', 'audio/')):
                response.headers['Content-Disposition'] = f'attachment; filename="{cid_content.filename}"'
            
            return response
        
        # If this is HTML content (legacy), display it in template
        elif cid_content.content:
            return render_template('cid_content.html', 
                                 content=cid_content.content,
                                 title=cid_content.title or f"Content for {path}",
                                 path=path), 200
    
    # If no content found, show 404 with the path
    return render_template('404.html', path=path), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
