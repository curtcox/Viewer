from datetime import datetime, timezone
from typing import Optional

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

    def get_effective_pattern(self) -> str:
        from alias_definition import get_primary_alias_route

        route = get_primary_alias_route(self)
        if route and route.match_pattern:
            return route.match_pattern
        name = getattr(self, 'name', '') or ''
        return f'/{name}' if name else '/'

    @property
    def match_type(self) -> str:
        from alias_definition import get_primary_alias_route

        route = get_primary_alias_route(self)
        return route.match_type if route else 'literal'

    @property
    def match_pattern(self) -> str:
        return self.get_effective_pattern()

    @property
    def target_path(self) -> Optional[str]:
        from alias_definition import get_primary_alias_route

        route = get_primary_alias_route(self)
        return route.target_path if route else None

    @property
    def ignore_case(self) -> bool:
        from alias_definition import get_primary_alias_route

        route = get_primary_alias_route(self)
        return bool(route.ignore_case) if route else False

    def get_primary_target_path(self) -> str:
        """Get the target path from the primary alias rule."""
        from alias_definition import get_primary_alias_route

        route = get_primary_alias_route(self)
        if route and route.target_path:
            return route.target_path

        # Fallback to name-based path
        name = getattr(self, 'name', '') or ''
        return f'/{name}' if name else '/'

    def get_primary_match_type(self) -> str:
        """Get the match type from the primary alias rule."""
        from alias_definition import get_primary_alias_route

        route = get_primary_alias_route(self)
        return route.match_type if route else 'literal'

    def get_primary_match_pattern(self) -> str:
        """Get the match pattern from the primary alias rule."""
        from alias_definition import get_primary_alias_route

        route = get_primary_alias_route(self)
        if route and route.match_pattern:
            return route.match_pattern

        # Fallback to name-based pattern
        name = getattr(self, 'name', '') or ''
        return f'/{name}' if name else '/'

    def get_primary_ignore_case(self) -> bool:
        """Get the ignore_case flag from the primary alias rule."""
        from alias_definition import get_primary_alias_route

        route = get_primary_alias_route(self)
        return bool(route.ignore_case) if route else False

    def __repr__(self):
        target = self.get_primary_target_path()
        return f'<Alias {self.name} -> {target}>'


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
