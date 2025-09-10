import jwt
import os
import uuid
from functools import wraps
from urllib.parse import urlencode

from flask import g, session, redirect, request, render_template, url_for
from flask_dance.consumer import (
    OAuth2ConsumerBlueprint,
    oauth_authorized,
    oauth_error,
)
from flask_dance.consumer.storage import BaseStorage
from flask_login import LoginManager, login_user, logout_user, current_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from sqlalchemy.exc import NoResultFound
from werkzeug.local import LocalProxy

from app import app, db
from models import OAuth, User

login_manager = LoginManager(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


class UserSessionStorage(BaseStorage):

    def get(self, blueprint):
        try:
            token = db.session.query(OAuth).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).one().token
        except NoResultFound:
            token = None
        return token

    def set(self, blueprint, token):
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name,
        ).delete()
        new_model = OAuth()
        new_model.user_id = current_user.get_id()
        new_model.browser_session_key = g.browser_session_key
        new_model.provider = blueprint.name
        new_model.token = token
        db.session.add(new_model)
        db.session.commit()

    def delete(self, blueprint):
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name).delete()
        db.session.commit()


def make_replit_blueprint():
    try:
        repl_id = os.environ['REPL_ID']
    except KeyError:
        raise SystemExit("the REPL_ID environment variable must be set")

    issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")

    replit_bp = OAuth2ConsumerBlueprint(
        "replit_auth",
        __name__,
        client_id=repl_id,
        client_secret=None,
        base_url=issuer_url,
        authorization_url_params={
            "prompt": "login consent",
        },
        token_url=issuer_url + "/token",
        token_url_params={
            "auth": (),
            "include_client_id": True,
        },
        auto_refresh_url=issuer_url + "/token",
        auto_refresh_kwargs={
            "client_id": repl_id,
        },
        authorization_url=issuer_url + "/auth",
        use_pkce=True,
        code_challenge_method="S256",
        scope=["openid", "profile", "email", "offline_access"],
        storage=UserSessionStorage(),
    )

    @replit_bp.before_app_request
    def set_applocal_session():
        if '_browser_session_key' not in session:
            session['_browser_session_key'] = uuid.uuid4().hex
        session.modified = True
        g.browser_session_key = session['_browser_session_key']
        g.flask_dance_replit = replit_bp.session

    @replit_bp.route("/logout")
    def logout():
        del replit_bp.token
        logout_user()

        end_session_endpoint = issuer_url + "/session/end"
        encoded_params = urlencode({
            "client_id":
            repl_id,
            "post_logout_redirect_uri":
            request.url_root,
        })
        logout_url = f"{end_session_endpoint}?{encoded_params}"

        return redirect(logout_url)

    @replit_bp.route("/error")
    def error():
        return render_template("403.html"), 403

    return replit_bp


def save_user(user_claims, invitation_code=None):
    """Legacy function - now delegates to auth_providers.save_user_from_claims"""
    from auth_providers import save_user_from_claims
    return save_user_from_claims(user_claims, invitation_code)


@oauth_authorized.connect
def logged_in(blueprint, token):
    user_claims = jwt.decode(token['id_token'],
                             options={"verify_signature": False})

    # Check if this is an existing user
    existing_user = User.query.filter_by(id=user_claims['sub']).first()

    if existing_user:
        # Existing user - no invitation required
        user = save_user(user_claims)
        login_user(user)
        blueprint.token = token
        next_url = session.pop("next_url", None)
        if next_url is not None:
            return redirect(next_url)
    else:
        # New user - check for invitation code
        invitation_code = session.get('invitation_code')
        if not invitation_code:
            # Store token temporarily and redirect to invitation page
            session['pending_token'] = token
            session['pending_user_claims'] = user_claims
            return redirect(url_for('require_invitation'))

        try:
            user = save_user(user_claims, invitation_code)
            session.pop('invitation_code', None)  # Clear used invitation
            login_user(user)
            blueprint.token = token
            next_url = session.pop("next_url", None)
            if next_url is not None:
                return redirect(next_url)
        except ValueError as e:
            # Invalid invitation - redirect to invitation page with error
            session['invitation_error'] = str(e)
            session['pending_token'] = token
            session['pending_user_claims'] = user_claims
            return redirect(url_for('require_invitation'))


@oauth_error.connect
def handle_error(blueprint, error, error_description=None, error_uri=None):
    return redirect(url_for('replit_auth.error'))


def require_login(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = get_next_navigation_url(request)
            # Check if REPL_ID is set (Replit auth is available)
            if os.environ.get('REPL_ID'):
                return redirect(url_for('replit_auth.login'))
            else:
                from flask import flash
                flash('Authentication not available in local development mode.', 'info')
                return redirect(url_for('index'))

        try:
            expires_in = replit.token.get('expires_in', 0)
            if expires_in < 0:
                issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")
                refresh_token_url = issuer_url + "/token"
                try:
                    token = replit.refresh_token(token_url=refresh_token_url,
                                                 client_id=os.environ['REPL_ID'])
                except InvalidGrantError:
                    # If the refresh token is invalid, the users needs to re-login.
                    session["next_url"] = get_next_navigation_url(request)
                    if os.environ.get('REPL_ID'):
                        return redirect(url_for('replit_auth.login'))
                    else:
                        from flask import flash
                        flash('Authentication not available in local development mode.', 'info')
                        return redirect(url_for('index'))
                replit.token_updater(token)
        except (AttributeError, KeyError, TypeError) as e:
            # If token doesn't exist or is invalid, redirect to login
            session["next_url"] = get_next_navigation_url(request)
            if os.environ.get('REPL_ID'):
                return redirect(url_for('replit_auth.login'))
            else:
                from flask import flash
                flash('Authentication not available in local development mode.', 'info')
                return redirect(url_for('index'))

        return f(*args, **kwargs)

    return decorated_function


def get_next_navigation_url(request):
    is_navigation_url = request.headers.get(
        'Sec-Fetch-Mode') == 'navigate' and request.headers.get(
            'Sec-Fetch-Dest') == 'document'
    if is_navigation_url:
        return request.url
    return request.referrer or request.url


replit = LocalProxy(lambda: g.flask_dance_replit)