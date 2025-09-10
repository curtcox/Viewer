import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1) # needed for url_for to generate with https

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

# No need to call db.init_app(app) here, it's already done in the constructor.
db = SQLAlchemy(app, model_class=Base)

# Create tables
# Need to put this in module-level to make it work with Gunicorn.
with app.app_context():
    import models  # noqa: F401
    import routes  # noqa: F401 - Import routes to register them
    import local_auth  # noqa: F401 - Import local auth routes

    # Register blueprints
    from local_auth import local_auth_bp
    app.register_blueprint(local_auth_bp, url_prefix="/auth")

    # Register Replit auth if available
    try:
        from replit_auth import make_replit_blueprint
        if os.environ.get('REPL_ID'):
            app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")
    except ImportError:
        pass

    db.create_all()
    logging.info("Database tables created")
