from datetime import datetime
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
    
    # Relationships
    payments = db.relationship('Payment', backref='user', lazy=True, cascade='all, delete-orphan')
    terms_acceptances = db.relationship('TermsAcceptance', backref='user', lazy=True, cascade='all, delete-orphan')
    
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

# Current terms version - update this when terms change
CURRENT_TERMS_VERSION = "1.0"
