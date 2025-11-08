"""User profile data operations."""

from typing import Any, Dict



def get_user_profile_data(_user_id: str) -> Dict[str, Any]:
    """Return placeholder profile metadata for externally managed accounts.

    Payment and terms of service tracking now live in an external system. The
    application keeps this helper as a compatibility shim so callers receive a
    consistent shape without exposing internal payment details. The returned
    structure intentionally contains empty collections and neutral defaults.
    """
    return {
        "payments": [],
        "terms_history": [],
        "needs_terms_acceptance": False,
        "current_terms_version": None,
    }
