"""Application-wide constants for entity types, labels, and magic strings."""

import re
from enum import Enum


class UploadType(Enum):
    """Upload type constants."""

    FILE = "file"
    TEXT = "text"
    URL = "url"


class EntityType(Enum):
    """Entity type constants."""

    ALIAS = "alias"
    SERVER = "server"
    CID = "cid"
    VARIABLE = "variable"
    SECRET = "secret"
    UPLOAD = "upload"
    SERVER_EVENT = "server_event"
    SERVER_TEST = "server-test"


class ActionType(Enum):
    """Action type constants."""

    SAVE = "save"
    SAVE_AS = "save-as"


class ServerMode(Enum):
    """Server test mode constants."""

    MAIN = "main"
    QUERY = "query"


# Entity type constants (for backward compatibility)
ENTITY_TYPE_ALIAS = "alias"
ENTITY_TYPE_SERVER = "server"
ENTITY_TYPE_CID = "cid"
ENTITY_TYPE_VARIABLE = "variable"
ENTITY_TYPE_SECRET = "secret"

# Entity type labels for display
TYPE_LABELS = {
    ENTITY_TYPE_ALIAS: "Alias",
    ENTITY_TYPE_SERVER: "Server",
    ENTITY_TYPE_CID: "CID",
    ENTITY_TYPE_VARIABLE: "Variable",
    ENTITY_TYPE_SECRET: "Secret",
}

# Reserved route paths that take precedence over dynamic routes
RESERVED_ROUTES = {
    "/",
    "/dashboard",
    "/profile",
    "/upload",
    "/uploads",
    "/history",
    "/servers",
    "/variables",
    "/secrets",
    "/settings",
    "/aliases",
    "/aliases/new",
    "/edit",
    "/meta",
    "/search",
    "/search/results",
    "/export",
    "/import",
}


# Validation Patterns
class Patterns:
    """Regular expression patterns for validation.

    Centralized patterns to eliminate duplication across the codebase.
    """

    # Entity name pattern (used by variables, secrets, and other entities)
    # Allows: letters, numbers, dots, hyphens, underscores
    ENTITY_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")

    # Alias for backward compatibility (same as ENTITY_NAME)
    VARIABLE_NAME = ENTITY_NAME
    SECRET_NAME = ENTITY_NAME


# Default entity names
class EntityDefaults:
    """Default entity names and values."""

    # Default server names
    AI_SERVER_NAME = "ai_stub"

    # Default alias names
    AI_ALIAS_NAME = "ai"
    CSS_ALIAS_NAME = "CSS"

    # Default action type
    ACTION = "save"

    # Maximum message length for interaction logs
    MAX_MESSAGE_LENGTH = 500
