from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from app import db
from models import (
    Payment,
    TermsAcceptance,
    Invitation,
    CURRENT_TERMS_VERSION,
    User,
    Server,
    Variable,
    Secret,
    ServerInvocation,
    CID,
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


def validate_invitation_code(invitation_code: str) -> Optional[Invitation]:
    """Validate an invitation code and return the invitation if valid."""
    invitation = Invitation.query.filter_by(invitation_code=invitation_code).first()
    if invitation and invitation.is_valid():
        return invitation
    return None


def get_user_servers(user_id: str):
    return Server.query.filter_by(user_id=user_id).order_by(Server.name).all()


def get_server_by_name(user_id: str, name: str):
    return Server.query.filter_by(user_id=user_id, name=name).first()


def get_user_variables(user_id: str):
    return Variable.query.filter_by(user_id=user_id).order_by(Variable.name).all()


def get_variable_by_name(user_id: str, name: str):
    return Variable.query.filter_by(user_id=user_id, name=name).first()


def get_user_secrets(user_id: str):
    return Secret.query.filter_by(user_id=user_id).order_by(Secret.name).all()


def get_secret_by_name(user_id: str, name: str):
    return Secret.query.filter_by(user_id=user_id, name=name).first()


def count_user_servers(user_id: str) -> int:
    return Server.query.filter_by(user_id=user_id).count()


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
