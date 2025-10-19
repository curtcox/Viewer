from datetime import datetime, timezone
from database import db
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
            self.payment_expires_at is None or self.payment_expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
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
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
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
    accepted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(45))  # Support IPv6

    def __repr__(self):
        return f'<TermsAcceptance {self.terms_version} by user {self.user_id}>'

class CID(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255), unique=True, nullable=False, index=True)
    file_data = db.Column(db.LargeBinary, nullable=False)  # For actual file bytes
    file_size = db.Column(db.Integer, nullable=True)
    uploaded_by_user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)  # Track uploader
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    uploaded_by = db.relationship('User', backref='uploads')

    def __repr__(self):
        return f'<CID {self.path}>'

class PageView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), default='GET')
    user_agent = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    viewed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = db.relationship('User', backref='page_views')

    def __repr__(self):
        return f'<PageView {self.path} by {self.user_id} at {self.viewed_at}>'

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    definition = db.Column(db.Text, nullable=False)
    definition_cid = db.Column(db.String(255), nullable=True, index=True)  # Track CID of definition
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', backref='servers')

    # Unique constraint: each user can only have one server with a given name
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_server_name'),)

    def __repr__(self):
        return f'<Server {self.name} by {self.user_id}>'


class Alias(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    target_path = db.Column(db.String(255), nullable=False)
    match_type = db.Column(db.String(20), nullable=False, default='literal')
    match_pattern = db.Column(db.String(255), nullable=False, default='')
    ignore_case = db.Column(db.Boolean, nullable=False, default=False)
    definition = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', backref='aliases')

    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_alias_name'),)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, 'match_type', None):
            self.match_type = 'literal'
        if getattr(self, 'match_pattern', None) in (None, ''):
            base_name = getattr(self, 'name', '') or ''
            self.match_pattern = f'/{base_name}' if base_name else '/'
        if getattr(self, 'ignore_case', None) is None:
            self.ignore_case = False
        if getattr(self, 'definition', None) in ("",):
            self.definition = None

    def get_effective_pattern(self) -> str:
        pattern = getattr(self, 'match_pattern', None)
        if pattern:
            return pattern
        name = getattr(self, 'name', '') or ''
        return f'/{name}' if name else '/'

    def __repr__(self):
        return f'<Alias {self.name} -> {self.target_path}>'


class EntityInteraction(db.Model):
    __tablename__ = 'entity_interactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=False, index=True)
    entity_name = db.Column(db.String(255), nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(500), nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user = db.relationship('User', backref='entity_interactions')

    def __repr__(self):
        return f'<EntityInteraction {self.entity_type}:{self.entity_name} {self.action}>'


class Variable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    definition = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', backref='variables')

    # Unique constraint: each user can only have one variable with a given name
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_variable_name'),)

    def __repr__(self):
        return f'<Variable {self.name} by {self.user_id}>'

class Secret(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    definition = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', backref='secrets')

    # Unique constraint: each user can only have one secret with a given name
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_secret_name'),)

    def __repr__(self):
        return f'<Secret {self.name} by {self.user_id}>'

class ServerInvocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    server_name = db.Column(db.String(100), nullable=False)  # Name of the server that was invoked
    result_cid = db.Column(db.String(255), nullable=False, index=True)  # CID of the result produced
    servers_cid = db.Column(db.String(255), nullable=True)  # CID of current servers definitions
    variables_cid = db.Column(db.String(255), nullable=True)  # CID of current variables definitions
    secrets_cid = db.Column(db.String(255), nullable=True)  # CID of current secrets definitions
    request_details_cid = db.Column(db.String(255), nullable=True)  # CID of request details JSON
    invocation_cid = db.Column(db.String(255), nullable=True, index=True)  # CID of this ServerInvocation JSON
    invoked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = db.relationship('User', backref='server_invocations')

    def __repr__(self):
        return f'<ServerInvocation {self.server_name} by {self.user_id} -> {self.result_cid}>'

# Current terms version - update this when terms change
CURRENT_TERMS_VERSION = "1.0"
