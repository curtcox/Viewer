import os
import logging
from typing import Optional

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

from database import db, init_db

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)


def create_app(config_override: Optional[dict] = None) -> Flask:
    """Application factory for creating configured Flask instances."""
    app = Flask(__name__)

    default_database_uri = os.environ.get("DATABASE_URL") or "sqlite:///secureapp.db"

    app.config.update(
        SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=default_database_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_recycle": 300,
        },
    )

    if config_override:
        app.config.update(config_override)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

    # Initialize database
    init_db(app)

    # Register application components
    from analytics import make_session_permanent, track_page_view
    from local_auth import local_auth_bp
    from routes import main_bp
    from auth_providers import auth_manager

    app.before_request(make_session_permanent)
    app.after_request(track_page_view)

    app.register_blueprint(main_bp)
    app.register_blueprint(local_auth_bp, url_prefix="/auth")
    
    # Register error handlers that work even in debug mode
    from routes.core import internal_error, not_found_error
    
    # Force registration of custom error handlers even in debug mode
    # This ensures our enhanced error pages with source links always work
    app.register_error_handler(500, internal_error)
    app.register_error_handler(404, not_found_error)
    
    # Override Flask's debug mode error handling to use our custom handlers
    # This is necessary because Flask's debug mode bypasses custom error handlers
    def force_custom_error_handling():
        """Force Flask to use our custom error handlers even in debug mode."""
        original_handle_exception = app.handle_exception
        
        def enhanced_handle_exception(e):
            # Always use our custom error handlers, even in debug mode
            if hasattr(e, 'code') and e.code == 404:
                return not_found_error(e)
            else:
                return internal_error(e)
        
        # Only override in debug mode to preserve normal behavior in production
        if app.debug:
            app.handle_exception = enhanced_handle_exception
    
    force_custom_error_handling()

    # Register Replit auth if available
    try:
        from replit_auth import make_replit_blueprint, init_login_manager

        init_login_manager(app)
        providers = getattr(auth_manager, "providers", None)
        replit_provider = None
        if isinstance(providers, dict):
            replit_provider = providers.get("replit")

        if replit_provider and getattr(replit_provider, "blueprint", None):
            app.register_blueprint(replit_provider.blueprint, url_prefix="/auth")
        elif os.environ.get("REPL_ID"):
            app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")
    except ImportError:
        pass

    with app.app_context():
        import models  # noqa: F401 ensure models are registered

        db.create_all()
        logging.info("Database tables created")

    return app


# Maintain module-level application for backwards compatibility
app = create_app()
