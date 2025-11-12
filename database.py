"""Database configuration and initialization."""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):  # type: ignore[misc]  # DeclarativeBase is properly typed but mypy strict mode treats it as Any
    pass

# Create the database instance
db = SQLAlchemy(model_class=Base)

def init_db(app: Flask) -> SQLAlchemy:
    """Initialize the database with the Flask app."""
    db.init_app(app)
    return db
