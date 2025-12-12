from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean

from alias_definition import get_primary_alias_route
from cid import CID as ValidatedCID
from database import db


class CID(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255), unique=True, nullable=False, index=True)
    file_data = db.Column(db.LargeBinary, nullable=False)  # For actual file bytes
    file_size = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f'<CID {self.path}>'


class PageView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), default='GET')
    user_agent = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    viewed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self) -> str:
        return f'<PageView {self.path} at {self.viewed_at}>'


class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    definition = db.Column(db.Text, nullable=False)
    definition_cid = db.Column(db.String(255), nullable=True, index=True)  # Track CID of definition
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    enabled = db.Column(Boolean(), nullable=False, default=True, server_default='1')

    def __repr__(self) -> str:
        return f'<Server {self.name}>'


class Alias(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    definition = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    enabled = db.Column(Boolean(), nullable=False, default=True, server_default='1')

    def get_effective_pattern(self) -> str:
        route = get_primary_alias_route(self)
        if route and route.match_pattern:
            return route.match_pattern
        name = getattr(self, 'name', '') or ''
        return f'/{name}' if name else '/'

    @property
    def match_type(self) -> str:
        route = get_primary_alias_route(self)
        return route.match_type if route else 'literal'

    @property
    def match_pattern(self) -> str:
        return self.get_effective_pattern()

    @property
    def target_path(self) -> Optional[str]:
        route = get_primary_alias_route(self)
        return route.target_path if route else None

    @property
    def ignore_case(self) -> bool:
        route = get_primary_alias_route(self)
        return bool(route.ignore_case) if route else False

    def get_primary_target_path(self) -> str:
        """Get the target path from the primary alias rule."""
        route = get_primary_alias_route(self)
        if route and route.target_path:
            return route.target_path

        # Fallback to name-based path
        name = getattr(self, 'name', '') or ''
        return f'/{name}' if name else '/'

    def get_primary_match_type(self) -> str:
        """Get the match type from the primary alias rule."""
        route = get_primary_alias_route(self)
        return route.match_type if route else 'literal'

    def get_primary_match_pattern(self) -> str:
        """Get the match pattern from the primary alias rule."""
        route = get_primary_alias_route(self)
        if route and route.match_pattern:
            return route.match_pattern

        # Fallback to name-based pattern
        name = getattr(self, 'name', '') or ''
        return f'/{name}' if name else '/'

    def get_primary_ignore_case(self) -> bool:
        """Get the ignore_case flag from the primary alias rule."""
        route = get_primary_alias_route(self)
        return bool(route.ignore_case) if route else False

    def __repr__(self) -> str:
        target = self.get_primary_target_path()
        return f'<Alias {self.name} -> {target}>'


class EntityInteraction(db.Model):
    __tablename__ = 'entity_interactions'

    id = db.Column(db.Integer, primary_key=True)
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

    def __repr__(self) -> str:
        return f'<EntityInteraction {self.entity_type}:{self.entity_name} {self.action}>'


class Variable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    definition = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    enabled = db.Column(Boolean(), nullable=False, default=True, server_default='1')

    def __repr__(self) -> str:
        return f'<Variable {self.name}>'


class Secret(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    definition = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    enabled = db.Column(Boolean(), nullable=False, default=True, server_default='1')

    def __repr__(self) -> str:
        return f'<Secret {self.name}>'


@dataclass(frozen=True)
class ServerInvocationCIDs:
    result: Optional[ValidatedCID]
    servers: Optional[ValidatedCID]
    variables: Optional[ValidatedCID]
    secrets: Optional[ValidatedCID]
    request_details: Optional[ValidatedCID]
    invocation: Optional[ValidatedCID]

    @classmethod
    def from_invocation(cls, invocation: "ServerInvocation") -> "ServerInvocationCIDs":
        return cls(
            result=ValidatedCID.try_from_string(getattr(invocation, "result_cid", None)),
            servers=ValidatedCID.try_from_string(getattr(invocation, "servers_cid", None)),
            variables=ValidatedCID.try_from_string(getattr(invocation, "variables_cid", None)),
            secrets=ValidatedCID.try_from_string(getattr(invocation, "secrets_cid", None)),
            request_details=ValidatedCID.try_from_string(getattr(invocation, "request_details_cid", None)),
            invocation=ValidatedCID.try_from_string(getattr(invocation, "invocation_cid", None)),
        )


class ServerInvocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_name = db.Column(db.String(100), nullable=False)  # Name of the server that was invoked
    result_cid = db.Column(db.String(255), nullable=False, index=True)  # CID of the result produced
    servers_cid = db.Column(db.String(255), nullable=True)  # CID of current servers definitions
    variables_cid = db.Column(db.String(255), nullable=True)  # CID of current variables definitions
    secrets_cid = db.Column(db.String(255), nullable=True)  # CID of current secrets definitions
    request_details_cid = db.Column(db.String(255), nullable=True)  # CID of request details JSON
    invocation_cid = db.Column(db.String(255), nullable=True, index=True)  # CID of this ServerInvocation JSON
    invoked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    @property
    def cids(self) -> ServerInvocationCIDs:
        return ServerInvocationCIDs.from_invocation(self)

    def __repr__(self) -> str:
        return f'<ServerInvocation {self.server_name} -> {self.result_cid}>'


class Export(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cid = db.Column(db.String(255), nullable=False, index=True)  # CID of the export
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self) -> str:
        return f'<Export {self.cid} at {self.created_at}>'
