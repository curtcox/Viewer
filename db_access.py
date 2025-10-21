from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from database import db
from models import (
    Payment,
    TermsAcceptance,
    CURRENT_TERMS_VERSION,
    User,
    Server,
    Alias,
    Variable,
    Secret,
    ServerInvocation,
    CID,
    EntityInteraction,
)


def get_user_profile_data(user_id: str) -> Dict[str, Any]:
    """Gather payment and terms data for a user."""
    payments = (
        Payment.query.filter_by(user_id=user_id)
        .order_by(Payment.payment_date.desc())
        .all()
    )
    terms_history = (
        TermsAcceptance.query.filter_by(user_id=user_id)
        .order_by(TermsAcceptance.accepted_at.desc())
        .all()
    )
    current_terms = TermsAcceptance.query.filter_by(
        user_id=user_id, terms_version=CURRENT_TERMS_VERSION
    ).first()
    return {
        "payments": payments,
        "terms_history": terms_history,
        "needs_terms_acceptance": current_terms is None,
        "current_terms_version": CURRENT_TERMS_VERSION,
    }


def create_payment_record(plan: str, amount: float, user: User) -> Payment:
    """Create and persist a payment record, updating the user as needed."""
    payment = Payment(user_id=user.id, amount=amount, plan_type=plan)
    if plan == "annual":
        payment.expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        user.is_paid = True
        user.payment_expires_at = payment.expires_at
    else:
        user.is_paid = False
        user.payment_expires_at = None
    payment.transaction_id = f"mock_txn_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    db.session.add(payment)
    db.session.commit()
    return payment


def create_terms_acceptance_record(user: User, ip_address: str) -> TermsAcceptance:
    """Create and persist a terms acceptance record for the user."""
    terms_acceptance = TermsAcceptance(
        user_id=user.id,
        terms_version=CURRENT_TERMS_VERSION,
        ip_address=ip_address,
    )
    user.current_terms_accepted = True
    db.session.add(terms_acceptance)
    db.session.commit()
    return terms_acceptance


def get_user_servers(user_id: str):
    return Server.query.filter_by(user_id=user_id).order_by(Server.name).all()


def get_server_by_name(user_id: str, name: str):
    return Server.query.filter_by(user_id=user_id, name=name).first()


def get_first_server_name(user_id: str) -> Optional[str]:
    """Return the first server name for a user ordered alphabetically."""

    server = (
        Server.query.filter_by(user_id=user_id)
        .order_by(Server.name.asc())
        .first()
    )
    return server.name if server else None


def get_user_aliases(user_id: str):
    return Alias.query.filter_by(user_id=user_id).order_by(Alias.name).all()


def get_alias_by_name(user_id: str, name: str):
    return Alias.query.filter_by(user_id=user_id, name=name).first()


def get_first_alias_name(user_id: str) -> Optional[str]:
    """Return the first alias name for a user ordered alphabetically."""

    alias = (
        Alias.query.filter_by(user_id=user_id)
        .order_by(Alias.name.asc())
        .first()
    )
    return alias.name if alias else None


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


def get_aliases_by_target_path(user_id: str, target_path: str):
    return (
        Alias.query.filter_by(
            user_id=user_id,
            target_path=target_path,
            match_type='literal',
        )
        .order_by(Alias.id.asc())
        .all()
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
    return CID.query.filter_by(uploaded_by_user_id=user_id).order_by(CID.created_at.desc()).all()


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
