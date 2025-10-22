from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import func, or_

import models
from alias_definition import AliasDefinitionError, parse_alias_definition
from database import db
from models import (
    Alias,
    CID,
    EntityInteraction,
    PageView,
    Secret,
    Server,
    ServerInvocation,
    Variable,
)

_DEFAULT_AI_SERVER_NAME = "ai_stub"
_DEFAULT_AI_ALIAS_NAME = "ai"


def get_user_profile_data(user_id: str) -> Dict[str, Any]:
    """Return placeholder profile metadata for externally managed accounts."""

    # Payment and terms of service tracking now live in an external system. The
    # application keeps this helper as a compatibility shim so callers receive a
    # consistent shape without exposing internal payment details. The returned
    # structure intentionally contains empty collections and neutral defaults.
    return {
        "payments": [],
        "terms_history": [],
        "needs_terms_acceptance": False,
        "current_terms_version": None,
    }


def get_user_servers(user_id: str):
    return Server.query.filter_by(user_id=user_id).order_by(Server.name).all()


def get_server_by_name(user_id: str, name: str):
    return Server.query.filter_by(user_id=user_id, name=name).first()


def get_first_server_name(user_id: str) -> Optional[str]:
    """Return the first server name for a user ordered alphabetically."""

    # Prefer user-created servers over the default AI helper when available.
    preferred = (
        Server.query.filter_by(user_id=user_id)
        .filter(Server.name != _DEFAULT_AI_SERVER_NAME)
        .order_by(Server.name.asc())
        .first()
    )
    if preferred is not None:
        return preferred.name

    fallback = (
        Server.query.filter_by(user_id=user_id)
        .order_by(Server.name.asc())
        .first()
    )
    return fallback.name if fallback else None


def get_user_aliases(user_id: str):
    return Alias.query.filter_by(user_id=user_id).order_by(Alias.name).all()


def get_alias_by_name(user_id: str, name: str):
    return Alias.query.filter_by(user_id=user_id, name=name).first()


def get_first_alias_name(user_id: str) -> Optional[str]:
    """Return the first alias name for a user ordered alphabetically."""

    # Prefer user-created aliases over the default AI helper when available.
    preferred = (
        Alias.query.filter_by(user_id=user_id)
        .filter(Alias.name != _DEFAULT_AI_ALIAS_NAME)
        .order_by(Alias.name.asc())
        .first()
    )
    if preferred is not None:
        return preferred.name

    fallback = (
        Alias.query.filter_by(user_id=user_id)
        .order_by(Alias.name.asc())
        .first()
    )
    return fallback.name if fallback else None


def get_alias_by_target_path(user_id: str, target_path: str):
    return (
        Alias.query.filter_by(
            user_id=user_id,
            target_path=target_path,
            match_type='literal',
        )
        .order_by(Alias.id.asc())
        .first()
    )


def get_user_variables(user_id: str):
    return Variable.query.filter_by(user_id=user_id).order_by(Variable.name).all()


def get_variable_by_name(user_id: str, name: str):
    return Variable.query.filter_by(user_id=user_id, name=name).first()


def get_first_variable_name(user_id: str) -> Optional[str]:
    """Return the first variable name for a user ordered alphabetically."""

    variable = (
        Variable.query.filter_by(user_id=user_id)
        .order_by(Variable.name.asc())
        .first()
    )
    return variable.name if variable else None


def get_user_secrets(user_id: str):
    return Secret.query.filter_by(user_id=user_id).order_by(Secret.name).all()


def get_secret_by_name(user_id: str, name: str):
    return Secret.query.filter_by(user_id=user_id, name=name).first()


def get_first_secret_name(user_id: str) -> Optional[str]:
    """Return the first secret name for a user ordered alphabetically."""

    secret = (
        Secret.query.filter_by(user_id=user_id)
        .order_by(Secret.name.asc())
        .first()
    )
    return secret.name if secret else None


def count_user_servers(user_id: str) -> int:
    return Server.query.filter_by(user_id=user_id).count()


def count_user_aliases(user_id: str) -> int:
    return Alias.query.filter_by(user_id=user_id).count()


def count_user_variables(user_id: str) -> int:
    return Variable.query.filter_by(user_id=user_id).count()


def count_user_secrets(user_id: str) -> int:
    return Secret.query.filter_by(user_id=user_id).count()


def save_entity(entity):
    db.session.add(entity)
    db.session.commit()
    return entity


def delete_entity(entity):
    db.session.delete(entity)
    db.session.commit()


def rollback_session() -> None:
    """Roll back the current database session."""

    db.session.rollback()


def save_page_view(page_view: PageView) -> PageView:
    """Persist a page view record."""

    db.session.add(page_view)
    db.session.commit()
    return page_view


def _normalize_cid_value(value: Optional[str]) -> str:
    """Return a normalized CID component without leading slashes or whitespace."""

    if value is None:
        return ""
    normalized = value.strip().lstrip("/")
    return normalized


def _replace_cid_text(
    text: Optional[str],
    old_path: str,
    new_path: str,
    old_value: str,
    new_value: str,
) -> Tuple[Optional[str], bool]:
    """Return text with CID references replaced and whether a change occurred."""

    if text is None:
        return None, False

    updated = text.replace(old_path, new_path).replace(old_value, new_value)
    if updated == text:
        return text, False
    return updated, True


def update_alias_cid_reference(
    old_cid: str,
    new_cid: str,
    alias_name: str,
) -> Dict[str, Any]:
    """Ensure an alias points to the supplied CID and update its definition.

    Parameters
    ----------
    old_cid:
        The previous CID value associated with the alias. Leading slashes are
        ignored. When empty no text replacement is attempted.
    new_cid:
        The CID that should replace the previous value. Leading slashes are
        ignored.
    alias_name:
        The alias to update. When no alias exists a new record is created for
        the default user.

    Returns
    -------
    Dict[str, Any]
        A mapping describing whether an alias was created and how many existing
        aliases were updated.
    """

    normalized_alias = (alias_name or "").strip()
    normalized_new = _normalize_cid_value(new_cid)
    if not normalized_alias or not normalized_new:
        return {"created": False, "updated": 0}

    normalized_old = _normalize_cid_value(old_cid)
    aliases: List[Alias] = Alias.query.filter_by(name=normalized_alias).all()

    if not aliases:
        from identity import ensure_default_user

        owner = ensure_default_user()
        definition = f"{normalized_alias} -> /{normalized_new}"
        alias = Alias(
            name=normalized_alias,
            user_id=owner.id,
            definition=definition,
            target_path=f"/{normalized_new}",
        )

        try:
            parsed = parse_alias_definition(definition, alias_name=normalized_alias)
        except AliasDefinitionError:
            parsed = None

        if parsed:
            alias.match_type = parsed.match_type
            alias.match_pattern = parsed.match_pattern
            alias.ignore_case = parsed.ignore_case
            alias.target_path = parsed.target_path

        db.session.add(alias)
        db.session.commit()
        return {"created": True, "updated": 1}

    if normalized_old and normalized_old == normalized_new:
        return {"created": False, "updated": 0}

    new_path = f"/{normalized_new}"
    old_path = f"/{normalized_old}" if normalized_old else None
    now = datetime.now(timezone.utc)
    updated_count = 0

    for alias in aliases:
        alias_changed = False

        current_target = getattr(alias, "target_path", None)
        if normalized_old:
            updated_target, target_changed = _replace_cid_text(
                current_target,
                old_path,
                new_path,
                normalized_old,
                normalized_new,
            )
        else:
            target_changed = current_target != new_path
            updated_target = new_path if target_changed else current_target

        if target_changed:
            alias.target_path = updated_target
            alias_changed = True

        updated_definition = getattr(alias, "definition", None)
        definition_changed = False
        if normalized_old:
            updated_definition, definition_changed = _replace_cid_text(
                updated_definition,
                old_path,
                new_path,
                normalized_old,
                normalized_new,
            )

        if definition_changed:
            alias.definition = updated_definition
            alias_changed = True

            parsed = None
            if updated_definition:
                try:
                    parsed = parse_alias_definition(
                        updated_definition,
                        alias_name=getattr(alias, "name", None),
                    )
                except AliasDefinitionError:
                    parsed = None

            if parsed:
                alias.match_type = parsed.match_type
                alias.match_pattern = parsed.match_pattern
                alias.ignore_case = parsed.ignore_case
                alias.target_path = parsed.target_path
                alias_changed = True

        if alias_changed:
            alias.updated_at = now
            updated_count += 1

    if updated_count:
        db.session.commit()

    return {"created": False, "updated": updated_count}


def update_cid_references(old_cid: str, new_cid: str) -> Dict[str, int]:
    """Replace CID references in alias and server definitions.

    Parameters
    ----------
    old_cid:
        The previous CID value. Leading slashes are ignored.
    new_cid:
        The CID that should replace the previous value. Leading slashes are ignored.

    Returns
    -------
    Dict[str, int]
        A mapping containing the counts of updated aliases and servers.
    """

    normalized_old = _normalize_cid_value(old_cid)
    normalized_new = _normalize_cid_value(new_cid)

    if not normalized_old or not normalized_new or normalized_old == normalized_new:
        return {"aliases": 0, "servers": 0}

    old_path = f"/{normalized_old}"
    new_path = f"/{normalized_new}"

    alias_updates = 0
    server_updates = 0
    updated_server_users: Set[str] = set()
    now = datetime.now(timezone.utc)

    aliases: List[Alias] = Alias.query.all()
    for alias in aliases:
        alias_changed = False

        updated_target, target_changed = _replace_cid_text(
            getattr(alias, "target_path", None),
            old_path,
            new_path,
            normalized_old,
            normalized_new,
        )
        if target_changed:
            alias.target_path = updated_target
            alias_changed = True

        updated_definition, definition_changed = _replace_cid_text(
            getattr(alias, "definition", None),
            old_path,
            new_path,
            normalized_old,
            normalized_new,
        )
        if definition_changed:
            alias.definition = updated_definition
            alias_changed = True

            parsed = None
            if updated_definition:
                try:
                    parsed = parse_alias_definition(
                        updated_definition,
                        alias_name=getattr(alias, "name", None),
                    )
                except AliasDefinitionError:
                    parsed = None

            if parsed:
                alias.match_type = parsed.match_type
                alias.match_pattern = parsed.match_pattern
                alias.ignore_case = parsed.ignore_case
                alias.target_path = parsed.target_path

        if alias_changed:
            alias.updated_at = now
            alias_updates += 1

    servers: List[Server] = Server.query.all()
    if servers:
        from cid_utils import save_server_definition_as_cid

        for server in servers:
            updated_definition, definition_changed = _replace_cid_text(
                getattr(server, "definition", None),
                old_path,
                new_path,
                normalized_old,
                normalized_new,
            )
            if definition_changed:
                server.definition = updated_definition
                server.definition_cid = save_server_definition_as_cid(
                    updated_definition,
                    getattr(server, "user_id", ""),
                )
                server.updated_at = now
                server_updates += 1
                if getattr(server, "user_id", None):
                    updated_server_users.add(server.user_id)

    total_updates = alias_updates + server_updates
    if not total_updates:
        return {"aliases": 0, "servers": 0}

    db.session.commit()

    if server_updates and updated_server_users:
        from cid_utils import store_server_definitions_cid

        for user_id in updated_server_users:
            store_server_definitions_cid(user_id)

    return {"aliases": alias_updates, "servers": server_updates}


def count_user_page_views(user_id: str) -> int:
    """Return the number of page views recorded for a user."""

    return PageView.query.filter_by(user_id=user_id).count()


def count_unique_page_view_paths(user_id: str) -> int:
    """Return the number of unique paths viewed by a user."""

    return (
        db.session.query(func.count(func.distinct(PageView.path)))
        .filter_by(user_id=user_id)
        .scalar()
        or 0
    )


def get_popular_page_paths(user_id: str, limit: int = 5):
    """Return the most frequently viewed paths for a user."""

    return (
        db.session.query(PageView.path, func.count(PageView.path).label('count'))
        .filter_by(user_id=user_id)
        .group_by(PageView.path)
        .order_by(func.count(PageView.path).desc())
        .limit(limit)
        .all()
    )


def paginate_user_page_views(user_id: str, page: int, per_page: int = 50):
    """Return paginated page view history for a user."""

    return (
        PageView.query.filter_by(user_id=user_id)
        .order_by(PageView.viewed_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def create_server_invocation(
    user_id: str,
    server_name: str,
    result_cid: str,
    servers_cid: Optional[str] = None,
    variables_cid: Optional[str] = None,
    secrets_cid: Optional[str] = None,
    request_details_cid: Optional[str] = None,
    invocation_cid: Optional[str] = None,
) -> ServerInvocation:
    invocation = ServerInvocation(
        user_id=user_id,
        server_name=server_name,
        result_cid=result_cid,
        servers_cid=servers_cid,
        variables_cid=variables_cid,
        secrets_cid=secrets_cid,
        request_details_cid=request_details_cid,
        invocation_cid=invocation_cid,
    )
    save_entity(invocation)
    return invocation


def get_user_server_invocations(user_id: str) -> List[ServerInvocation]:
    """Return invocation events for a user ordered from newest to oldest."""

    return (
        ServerInvocation.query
        .filter(ServerInvocation.user_id == user_id)
        .order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc())
        .all()
    )


def get_user_server_invocations_by_server(user_id: str, server_name: str) -> List[ServerInvocation]:
    """Return invocation events for a specific server ordered from newest to oldest."""

    return (
        ServerInvocation.query
        .filter(
            ServerInvocation.user_id == user_id,
            ServerInvocation.server_name == server_name,
        )
        .order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc())
        .all()
    )


def get_user_server_invocations_by_result_cids(
    user_id: str,
    result_cids: Iterable[str],
) -> List[ServerInvocation]:
    """Return invocation events matching any of the provided result CIDs."""

    cid_values = {cid for cid in result_cids if cid}
    if not cid_values:
        return []

    return (
        ServerInvocation.query
        .filter(
            ServerInvocation.user_id == user_id,
            ServerInvocation.result_cid.in_(cid_values),
        )
        .order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc())
        .all()
    )


def find_server_invocations_by_cid(cid_value: str) -> List[ServerInvocation]:
    """Return invocation events that reference a CID in any tracked column."""

    if not cid_value:
        return []

    filters = [
        ServerInvocation.result_cid == cid_value,
        ServerInvocation.invocation_cid == cid_value,
        ServerInvocation.request_details_cid == cid_value,
        ServerInvocation.servers_cid == cid_value,
        ServerInvocation.variables_cid == cid_value,
        ServerInvocation.secrets_cid == cid_value,
    ]

    return ServerInvocation.query.filter(or_(*filters)).all()


def get_cid_by_path(path: str) -> Optional[CID]:
    return CID.query.filter_by(path=path).first()


def find_cids_by_prefix(prefix: str) -> List[CID]:
    """Return CID records whose path matches the given CID prefix."""
    if not prefix:
        return []

    normalized = prefix.split('.')[0].lstrip('/')
    if not normalized:
        return []

    pattern = f"/{normalized}%"
    return (
        CID.query
        .filter(CID.path.like(pattern))
        .order_by(CID.path.asc())
        .all()
    )


def create_cid_record(cid: str, file_content: bytes, user_id: str) -> CID:
    record = CID(
        path=f"/{cid}",
        file_data=file_content,
        file_size=len(file_content),
        uploaded_by_user_id=user_id,
    )
    save_entity(record)
    return record


def get_user_uploads(user_id: str):
    """Return all CID uploads for a user ordered from newest to oldest."""

    session_owner = getattr(models, "db", db)
    session = getattr(session_owner, "session", db.session)

    return (
        session.query(CID)
        .filter(CID.uploaded_by_user_id == user_id)
        .order_by(CID.created_at.desc())
        .all()
    )


def get_cids_by_paths(paths: Iterable[str]) -> List[CID]:
    """Return CID records that match any of the supplied paths."""

    normalized_paths = [path for path in paths if path]
    if not normalized_paths:
        return []

    return CID.query.filter(CID.path.in_(normalized_paths)).all()


def get_recent_cids(limit: int = 10) -> List[CID]:
    """Return the most recent CID records."""

    return (
        CID.query
        .order_by(CID.created_at.desc())
        .limit(limit)
        .all()
    )


def get_first_cid() -> Optional[CID]:
    """Return the first CID record in the table."""

    return CID.query.first()


def record_entity_interaction(
    user_id: str,
    entity_type: str,
    entity_name: str,
    action: str,
    message: str | None,
    content: str,
    *,
    created_at: datetime | None = None,
):
    """Persist a change or AI interaction for later recall."""

    if not user_id or not entity_type or not entity_name:
        return None

    action_value = (action or '').strip() or 'save'
    message_value = (message or '').strip()
    if len(message_value) > 500:
        message_value = message_value[:497] + '…'

    created_at_value = created_at
    if created_at_value is not None:
        if created_at_value.tzinfo is None:
            created_at_value = created_at_value.replace(tzinfo=timezone.utc)
        else:
            created_at_value = created_at_value.astimezone(timezone.utc)

        existing = (
            EntityInteraction.query
            .filter_by(
                user_id=user_id,
                entity_type=entity_type,
                entity_name=entity_name,
                action=action_value,
                message=message_value,
            )
            .filter(EntityInteraction.created_at == created_at_value)
            .first()
        )
        if existing:
            if content and content != existing.content:
                existing.content = content
                db.session.commit()
            return existing

    interaction = EntityInteraction(
        user_id=user_id,
        entity_type=entity_type,
        entity_name=entity_name,
        action=action_value,
        message=message_value,
        content=content or '',
        created_at=created_at_value,
    )
    db.session.add(interaction)
    db.session.commit()
    return interaction


def get_recent_entity_interactions(
    user_id: str,
    entity_type: str,
    entity_name: str,
    limit: int = 10,
):
    """Fetch the most recent interactions for an entity."""

    if not user_id or not entity_type or not entity_name:
        return []

    query = (
        EntityInteraction.query
        .filter_by(user_id=user_id, entity_type=entity_type, entity_name=entity_name)
        .order_by(EntityInteraction.created_at.desc(), EntityInteraction.id.desc())
    )

    if limit:
        query = query.limit(limit)

    return list(query.all())


def find_entity_interaction(
    user_id: str,
    entity_type: str,
    entity_name: str,
    action: str,
    message: str,
    created_at,
):
    """Return a single interaction matching the supplied criteria."""

    query = EntityInteraction.query.filter_by(
        user_id=user_id,
        entity_type=entity_type,
        entity_name=entity_name,
        action=action,
        message=message,
    )

    if created_at is not None:
        query = query.filter(EntityInteraction.created_at == created_at)

    return query.first()


def get_entity_interactions(
    user_id: str,
    entity_type: str,
    entity_name: str,
):
    """Return all stored interactions for an entity ordered from oldest to newest."""

    return (
        EntityInteraction.query
        .filter_by(user_id=user_id, entity_type=entity_type, entity_name=entity_name)
        .order_by(EntityInteraction.created_at.asc(), EntityInteraction.id.asc())
        .all()
    )


def get_all_servers() -> List[Server]:
    """Return all server records."""

    return Server.query.all()


def count_cids() -> int:
    return CID.query.count()


def count_page_views() -> int:
    return PageView.query.count()


def count_servers() -> int:
    return Server.query.count()


def count_variables() -> int:
    return Variable.query.count()


def count_secrets() -> int:
    return Secret.query.count()


