"""
Authentication provider abstraction layer for supporting multiple login providers.
"""
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any
from flask import session, redirect, url_for, request, flash
from flask_login import current_user
from database import db
from models import User, Invitation


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this authentication provider is available."""
        pass

    @abstractmethod
    def get_login_url(self) -> str:
        """Get the URL to redirect to for login."""
        pass

    @abstractmethod
    def get_logout_url(self) -> str:
        """Get the URL to redirect to for logout."""
        pass

    @abstractmethod
    def handle_callback(self) -> Optional[User]:
        """Handle authentication callback and return authenticated user."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this authentication provider."""
        pass


class ReplitAuthProvider(AuthProvider):
    """Replit authentication provider."""

    def __init__(self):
        self.blueprint = None
        self._setup_blueprint()

    def _setup_blueprint(self):
        """Setup Replit OAuth blueprint if available."""
        try:
            from replit_auth import make_replit_blueprint
            if os.environ.get('REPL_ID'):
                self.blueprint = make_replit_blueprint()
        except ImportError:
            self.blueprint = None

    def is_available(self) -> bool:
        return self.blueprint is not None and os.environ.get('REPL_ID') is not None

    def get_login_url(self) -> str:
        return url_for('replit_auth.login')

    def get_logout_url(self) -> str:
        return url_for('replit_auth.logout')

    def handle_callback(self) -> Optional[User]:
        # Replit auth handles its own callbacks through the blueprint
        return None

    def get_provider_name(self) -> str:
        return "Replit"


class LocalAuthProvider(AuthProvider):
    """Local development authentication provider."""

    def is_available(self) -> bool:
        return not os.environ.get('REPL_ID')  # Available when not in Replit

    def get_login_url(self) -> str:
        return url_for('local_auth.login')

    def get_logout_url(self) -> str:
        return url_for('local_auth.logout')

    def handle_callback(self) -> Optional[User]:
        # Local auth handles login through a simple form
        return None

    def get_provider_name(self) -> str:
        return "Local Development"


class AuthManager:
    """Manages authentication providers and handles authentication flow."""

    def __init__(self):
        self.providers = {
            'replit': ReplitAuthProvider(),
            'local': LocalAuthProvider()
        }
        self._active_provider = None

    def get_active_provider(self) -> Optional[AuthProvider]:
        """Get the currently active authentication provider."""
        if self._active_provider is None:
            # Auto-detect based on environment
            providers: Dict[str, AuthProvider] = {}

            if isinstance(self.providers, dict):
                providers = self.providers

            replit_provider = providers.get('replit')
            local_provider = providers.get('local')

            if replit_provider and getattr(replit_provider, 'is_available', None):
                if replit_provider.is_available():
                    self._active_provider = replit_provider
            if self._active_provider is None and local_provider and getattr(local_provider, 'is_available', None):
                if local_provider.is_available():
                    self._active_provider = local_provider
        return self._active_provider

    def get_login_url(self) -> str:
        """Get the login URL for the active provider."""
        provider = self.get_active_provider()
        if provider:
            return provider.get_login_url()
        return url_for('main.index')

    def get_logout_url(self) -> str:
        """Get the logout URL for the active provider."""
        provider = self.get_active_provider()
        if provider:
            return provider.get_logout_url()
        return url_for('main.index')

    def is_authentication_available(self) -> bool:
        """Check if any authentication provider is available."""
        return self.get_active_provider() is not None

    def get_provider_name(self) -> str:
        """Get the name of the active provider."""
        provider = self.get_active_provider()
        return provider.get_provider_name() if provider else "None"


# Global auth manager instance
auth_manager = AuthManager()


def require_login(f):
    """Decorator to require authentication for routes."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = get_next_navigation_url(request)
            provider = auth_manager.get_active_provider()

            if provider:
                return redirect(provider.get_login_url())
            else:
                flash('Authentication not available.', 'info')
                return redirect(url_for('main.index'))

        return f(*args, **kwargs)

    return decorated_function


def get_next_navigation_url(request):
    """Get the next URL to redirect to after login."""
    is_navigation_url = (request.headers.get('Sec-Fetch-Mode') == 'navigate' and
                        request.headers.get('Sec-Fetch-Dest') == 'document')
    if is_navigation_url:
        return request.url
    return request.referrer or request.url


def create_local_user(email: str = None, first_name: str = None, last_name: str = None) -> User:
    """Create a local development user."""
    # Generate a unique ID for local users
    user_id = f"local_{uuid.uuid4().hex[:16]}"

    # Check if user already exists (by email if provided)
    if email:
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return existing_user

    # Create new user
    user = User()
    user.id = user_id
    user.email = email or f"local-user-{user_id}@example.com"
    user.first_name = first_name or "Local"
    user.last_name = last_name or "User"
    user.created_at = datetime.now()
    user.updated_at = datetime.now()

    # For local development, give users full access by default
    user.is_paid = True
    user.current_terms_accepted = True
    user.payment_expires_at = None

    db.session.add(user)
    db.session.commit()

    return user


def save_user_from_claims(user_claims: Dict[str, Any], invitation_code: str = None) -> User:
    """Save user from authentication claims (used by OAuth providers)."""
    # Check if user already exists
    existing_user = User.query.filter_by(id=user_claims['sub']).first()

    if existing_user:
        # Update existing user info
        existing_user.email = user_claims.get('email')
        existing_user.first_name = user_claims.get('first_name')
        existing_user.last_name = user_claims.get('last_name')
        existing_user.profile_image_url = user_claims.get('profile_image_url')
        existing_user.updated_at = datetime.now()
        user = existing_user
    else:
        # For new users, require a valid invitation
        if not invitation_code:
            raise ValueError("Invitation code required for new users")

        # Validate invitation
        invitation = Invitation.query.filter_by(invitation_code=invitation_code).first()

        if not invitation or not invitation.is_valid():
            raise ValueError("Invalid or expired invitation code")

        # Create new user with invitation tracking
        user = User()
        user.id = user_claims['sub']
        user.email = user_claims.get('email')
        user.first_name = user_claims.get('first_name')
        user.last_name = user_claims.get('last_name')
        user.profile_image_url = user_claims.get('profile_image_url')
        user.created_at = datetime.now()
        user.updated_at = datetime.now()
        user.invited_by_user_id = invitation.inviter_user_id
        user.invitation_used_id = invitation.id

        # Mark invitation as used
        invitation.mark_used(user.id)

        db.session.add(user)

    try:
        db.session.commit()
        return user
    except Exception as e:
        db.session.rollback()
        print(f"Error saving user: {e}")
        raise e
