from datetime import datetime, timezone
from database import db

class CID(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255), unique=True, nullable=False, index=True)
    file_data = db.Column(db.LargeBinary, nullable=False)  # For actual file bytes
    file_size = db.Column(db.Integer, nullable=True)
    uploaded_by_user_id = db.Column(db.String, nullable=True)  # Track uploader
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<CID {self.path}>'

class PageView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, nullable=False)
    path = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), default='GET')
    user_agent = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    viewed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f'<PageView {self.path} by {self.user_id} at {self.viewed_at}>'

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    definition = db.Column(db.Text, nullable=False)
    definition_cid = db.Column(db.String(255), nullable=True, index=True)  # Track CID of definition
    user_id = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Unique constraint: each user can only have one server with a given name
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_server_name'),)

    def __repr__(self):
        return f'<Server {self.name} by {self.user_id}>'


class Alias(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    definition = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_alias_name'),)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if getattr(self, 'definition', None) in ("",):
            self.definition = None

    def get_primary_parsed_definition(self):
        """Parse the definition and return the primary route configuration.

        Returns a ParsedAliasDefinition object or None if parsing fails.
        This provides access to match_type, match_pattern, target_path, and ignore_case
        from the definition field.
        """
        from alias_definition import parse_alias_definition, AliasDefinitionError

        definition = getattr(self, 'definition', None)
        if not definition:
            return None

        try:
            return parse_alias_definition(definition, alias_name=getattr(self, 'name', None))
        except AliasDefinitionError:
            return None

    def __repr__(self):
        parsed = self.get_primary_parsed_definition()
        if parsed:
            return f'<Alias {self.name} -> {parsed.target_path}>'
        return f'<Alias {self.name}>'


class EntityInteraction(db.Model):
    __tablename__ = 'entity_interactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, nullable=False, index=True)
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

    def __repr__(self):
        return f'<EntityInteraction {self.entity_type}:{self.entity_name} {self.action}>'


class Variable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    definition = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Unique constraint: each user can only have one variable with a given name
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_variable_name'),)

    def __repr__(self):
        return f'<Variable {self.name} by {self.user_id}>'

class Secret(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    definition = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Unique constraint: each user can only have one secret with a given name
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_secret_name'),)

    def __repr__(self):
        return f'<Secret {self.name} by {self.user_id}>'

class ServerInvocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, nullable=False)
    server_name = db.Column(db.String(100), nullable=False)  # Name of the server that was invoked
    result_cid = db.Column(db.String(255), nullable=False, index=True)  # CID of the result produced
    servers_cid = db.Column(db.String(255), nullable=True)  # CID of current servers definitions
    variables_cid = db.Column(db.String(255), nullable=True)  # CID of current variables definitions
    secrets_cid = db.Column(db.String(255), nullable=True)  # CID of current secrets definitions
    request_details_cid = db.Column(db.String(255), nullable=True)  # CID of request details JSON
    invocation_cid = db.Column(db.String(255), nullable=True, index=True)  # CID of this ServerInvocation JSON
    invoked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f'<ServerInvocation {self.server_name} by {self.user_id} -> {self.result_cid}>'
