import secrets
from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Payment and access control
    is_paid = db.Column(db.Boolean, default=False)
    payment_expires_at = db.Column(db.DateTime)
    current_terms_accepted = db.Column(db.Boolean, default=False)
    
    # Invitation tracking
    invited_by_user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    invitation_used_id = db.Column(db.Integer, db.ForeignKey('invitation.id'), nullable=True)
    
    # Relationships
    payments = db.relationship('Payment', backref='user', lazy=True, cascade='all, delete-orphan')
    terms_acceptances = db.relationship('TermsAcceptance', backref='user', lazy=True, cascade='all, delete-orphan')
    invitations_sent = db.relationship('Invitation', backref='inviter', lazy=True, foreign_keys='Invitation.inviter_user_id')
    invited_by = db.relationship('User', remote_side=[id], backref='invited_users')
    
    def has_access(self):
        """Check if user has full access (logged in, paid, terms accepted)"""
        return self.is_paid and self.current_terms_accepted and (
            self.payment_expires_at is None or self.payment_expires_at > datetime.utcnow()
        )
    
    @property
    def username(self):
        """Compatibility property for templates"""
        return self.first_name or self.email or self.id
    
    def __repr__(self):
        return f'<User {self.id}>'

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    from sqlalchemy import UniqueConstraint
    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    plan_type = db.Column(db.String(50), nullable=False)  # 'free' or 'annual'
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    payment_method = db.Column(db.String(50), default='Mock Payment')
    transaction_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='completed')
    
    def __repr__(self):
        return f'<Payment {self.amount} for {self.plan_type}>'

class TermsAcceptance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    terms_version = db.Column(db.String(10), nullable=False)
    accepted_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # Support IPv6
    
    def __repr__(self):
        return f'<TermsAcceptance {self.terms_version} by user {self.user_id}>'

class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inviter_user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    invitation_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)  # Optional: specific email invite
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)
    used_by_user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, used, expired
    expires_at = db.Column(db.DateTime, nullable=True)  # Optional expiration
    
    # Relationships
    used_by_user = db.relationship('User', foreign_keys=[used_by_user_id], backref='invitation_used')
    
    def is_valid(self):
        """Check if invitation is still valid for use"""
        if self.status != 'pending':
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def mark_used(self, user_id):
        """Mark invitation as used by a specific user"""
        self.status = 'used'
        self.used_at = datetime.utcnow()
        self.used_by_user_id = user_id
    
    def __repr__(self):
        return f'<Invitation {self.invitation_code} by {self.inviter_user_id}>'

class CID(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=True)  # For HTML content
    file_data = db.Column(db.LargeBinary, nullable=True)  # For actual file bytes
    title = db.Column(db.String(255), nullable=True)
    content_type = db.Column(db.String(100), default='html')
    filename = db.Column(db.String(255), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<CID {self.path}>'

# Current terms version - update this when terms change
CURRENT_TERMS_VERSION = "1.0"
