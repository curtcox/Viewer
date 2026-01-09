# ruff: noqa: F821, F706
"""Execute MongoDB database operations with connection management."""

from __future__ import annotations

from typing import Any, Dict, Optional
import json

from server_utils.external_api import (
    OperationDefinition,
    RequiredField,
    error_output,
    validate_and_build_payload,
    validation_error,
)
from server_utils.external_api.limit_validator import MONGODB_MAX_LIMIT, get_limit_info, validate_limit


_OPERATIONS = {
    "find": OperationDefinition(required=(RequiredField("collection"),)),
    "find_one": OperationDefinition(required=(RequiredField("collection"),)),
    "insert_one": OperationDefinition(required=(RequiredField("collection"),)),
    "insert_many": OperationDefinition(required=(RequiredField("collection"),)),
    "update_one": OperationDefinition(required=(RequiredField("collection"),)),
    "update_many": OperationDefinition(required=(RequiredField("collection"),)),
    "delete_one": OperationDefinition(required=(RequiredField("collection"),)),
    "delete_many": OperationDefinition(required=(RequiredField("collection"),)),
    "count": OperationDefinition(required=(RequiredField("collection"),)),
}


def _build_preview(
    *,
    operation: str,
    collection: Optional[str],
    query: Optional[Dict[str, Any]],
    document: Optional[Dict[str, Any]],
    uri: str,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a preview of the MongoDB operation."""
    preview: Dict[str, Any] = {
        "operation": operation,
        "uri": uri.split("@")[-1] if "@" in uri else uri,  # Hide credentials
        "auth": "MongoDB URI",
    }
    if collection:
        preview["collection"] = collection
    if query:
        preview["query"] = query
    if document:
        preview["document"] = document

    # Include limit constraint information for find operations
    if limit is not None and operation in ("find", "find_one"):
        preview["limit_constraint"] = get_limit_info(limit, MONGODB_MAX_LIMIT, "limit")

    return preview


def _stringify_id(document: Dict[str, Any]) -> None:
    if "_id" in document:
        document["_id"] = str(document["_id"])


def _handle_find(collection_handle, parsed_query: Dict[str, Any], limit: int, **_: Any) -> Dict[str, Any]:
    cursor = collection_handle.find(parsed_query).limit(limit)
    result = list(cursor)
    for doc in result:
        _stringify_id(doc)
    return {"output": result}


def _handle_find_one(collection_handle, parsed_query: Dict[str, Any], **_: Any) -> Dict[str, Any]:
    result = collection_handle.find_one(parsed_query)
    if result:
        _stringify_id(result)
    return {"output": result}


def _handle_insert_one(collection_handle, parsed_document: Any, **_: Any) -> Dict[str, Any]:
    insert_result = collection_handle.insert_one(parsed_document)
    return {"output": {"inserted_id": str(insert_result.inserted_id)}}


def _handle_insert_many(collection_handle, parsed_document: Any, **_: Any) -> Dict[str, Any]:
    if not isinstance(parsed_document, list):
        return validation_error("insert_many requires a list of documents", field="document")
    insert_result = collection_handle.insert_many(parsed_document)
    return {"output": {"inserted_ids": [str(item_id) for item_id in insert_result.inserted_ids]}}


def _handle_update(collection_handle, parsed_query: Dict[str, Any], parsed_update: Dict[str, Any], many: bool) -> Dict[str, Any]:
    update_func = collection_handle.update_many if many else collection_handle.update_one
    update_result = update_func(parsed_query, parsed_update)
    return {
        "output": {
            "matched_count": update_result.matched_count,
            "modified_count": update_result.modified_count,
        }
    }


def _handle_delete(collection_handle, parsed_query: Dict[str, Any], many: bool) -> Dict[str, Any]:
    delete_func = collection_handle.delete_many if many else collection_handle.delete_one
    delete_result = delete_func(parsed_query)
    return {"output": {"deleted_count": delete_result.deleted_count}}


def _handle_count(collection_handle, parsed_query: Dict[str, Any], **_: Any) -> Dict[str, Any]:
    return {"output": {"count": collection_handle.count_documents(parsed_query)}}


_OPERATION_HANDLERS = {
    "find": _handle_find,
    "find_one": _handle_find_one,
    "insert_one": _handle_insert_one,
    "insert_many": _handle_insert_many,
    "update_one": lambda collection_handle, parsed_query, parsed_update, **_: _handle_update(
        collection_handle, parsed_query, parsed_update, many=False
    ),
    "update_many": lambda collection_handle, parsed_query, parsed_update, **_: _handle_update(
        collection_handle, parsed_query, parsed_update, many=True
    ),
    "delete_one": lambda collection_handle, parsed_query, **_: _handle_delete(
        collection_handle, parsed_query, many=False
    ),
    "delete_many": lambda collection_handle, parsed_query, **_: _handle_delete(
        collection_handle, parsed_query, many=True
    ),
    "count": _handle_count,
}


def main(
    *,
    operation: str = "find",
    collection: str = "",
    query: str = "{}",
    document: str = "{}",
    update: str = "{}",
    limit: int = 100,
    MONGODB_URI: str = "",
    connection_timeout: int = 10,
    query_timeout: int = 60,
    dry_run: bool = True,
    context=None,
) -> Dict[str, Any]:
    """Execute MongoDB database operations.

    Operations:
    - find: Find documents matching query
    - find_one: Find a single document
    - insert_one: Insert a single document
    - insert_many: Insert multiple documents
    - update_one: Update a single document
    - update_many: Update multiple documents
    - delete_one: Delete a single document
    - delete_many: Delete multiple documents
    - count: Count documents matching query
    """

    # Validate credentials
    if not MONGODB_URI:
        return error_output("Missing MONGODB_URI", status_code=401)

    payload_result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        collection=collection,
    )
    if isinstance(payload_result, tuple):
        return validation_error(payload_result[0], field=payload_result[1])

    # Validate limit parameter
    # MongoDB practical limit set to 10000 for performance
    if error := validate_limit(limit, MONGODB_MAX_LIMIT, "limit"):
        return error

    # Parse query, document, and update
    try:
        parsed_query = json.loads(query) if isinstance(query, str) else query
        parsed_document = json.loads(document) if isinstance(document, str) else document
        parsed_update = json.loads(update) if isinstance(update, str) else update
    except json.JSONDecodeError as e:
        return validation_error(f"Invalid JSON: {str(e)}", field="query/document/update")

    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=operation,
                collection=collection,
                query=parsed_query if parsed_query != {} else None,
                document=parsed_document if parsed_document != {} else None,
                uri=MONGODB_URI,
                limit=limit if operation in ("find", "find_one") else None,
            )
        }

    # Execute actual database operation
    try:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError

        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=connection_timeout * 1000,
            socketTimeoutMS=query_timeout * 1000,
        )

        # Extract database name from URI or use default
        db_name = MONGODB_URI.split("/")[-1].split("?")[0] if "/" in MONGODB_URI else "test"
        db = client[db_name]
        coll = db[collection]

        handler = _OPERATION_HANDLERS.get(operation)
        if handler is None:
            return validation_error("Unsupported operation", field="operation")
        result = handler(
            coll,
            parsed_query=parsed_query,
            parsed_document=parsed_document,
            parsed_update=parsed_update,
            limit=limit,
        )

        client.close()

        return result

    except ImportError:
        return error_output(
            "pymongo not installed. Install with: pip install pymongo",
            status_code=500,
        )
    except PyMongoError as e:
        return error_output(f"MongoDB error: {str(e)}", status_code=500)
    except Exception as e:
        return error_output(str(e), status_code=500)
