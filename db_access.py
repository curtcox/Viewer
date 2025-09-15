from app import db


def log_page_view(page_view):
    """Persist a page view record."""
    db.session.add(page_view)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def save_invitation(invitation):
    """Persist an invitation record."""
    db.session.add(invitation)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return invitation
