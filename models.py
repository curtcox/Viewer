from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Payment and access control
    is_paid = db.Column(db.Boolean, default=False)
    payment_expires_at = db.Column(db.DateTime)
    current_terms_accepted = db.Column(db.Boolean, default=False)
    
    # Relationships
    payments = db.relationship('Payment', backref='user', lazy=True, cascade='all, delete-orphan')
    terms_acceptances = db.relationship('TermsAcceptance', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_access(self):
        """Check if user has full access (logged in, paid, terms accepted)"""
        return self.is_paid and self.current_terms_accepted and (
            self.payment_expires_at is None or self.payment_expires_at > datetime.utcnow()
        )
    
    def __repr__(self):
        return f'<User {self.username}>'

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    plan_type = db.Column(db.String(50), nullable=False)  # 'basic', 'premium', etc.
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    payment_method = db.Column(db.String(50), default='Mock Payment')
    transaction_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='completed')
    
    def __repr__(self):
        return f'<Payment {self.amount} for {self.plan_type}>'

class TermsAcceptance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    terms_version = db.Column(db.String(10), nullable=False)
    accepted_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # Support IPv6
    
    def __repr__(self):
        return f'<TermsAcceptance {self.terms_version} by user {self.user_id}>'

# Current terms version - update this when terms change
CURRENT_TERMS_VERSION = "1.0"
