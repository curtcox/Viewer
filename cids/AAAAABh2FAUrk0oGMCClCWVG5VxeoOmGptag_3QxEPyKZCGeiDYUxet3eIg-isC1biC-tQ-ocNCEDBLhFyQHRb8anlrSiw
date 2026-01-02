# ruff: noqa: F821, F706
"""Execute MongoDB database operations with connection management."""

from __future__ import annotations

from typing import Any, Dict, Optional
import json

from server_utils.external_api import error_output, validation_error


def _build_preview(
    *,
    operation: str,
    collection: Optional[str],
    query: Optional[Dict[str, Any]],
    document: Optional[Dict[str, Any]],
    uri: str,
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
    return preview


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
    
    normalized_operation = operation.lower()
    valid_operations = {
        "find", "find_one", "insert_one", "insert_many",
        "update_one", "update_many", "delete_one", "delete_many", "count"
    }
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")
    
    # Validate credentials
    if not MONGODB_URI:
        return error_output("Missing MONGODB_URI", status_code=401)
    
    # Validate collection
    if not collection:
        return validation_error("Missing required collection", field="collection")
    
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
                operation=normalized_operation,
                collection=collection,
                query=parsed_query if parsed_query != {} else None,
                document=parsed_document if parsed_document != {} else None,
                uri=MONGODB_URI,
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
        
        result = None
        
        if normalized_operation == "find":
            cursor = coll.find(parsed_query).limit(limit)
            result = list(cursor)
            # Convert ObjectId to string for JSON serialization
            for doc in result:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
        
        elif normalized_operation == "find_one":
            result = coll.find_one(parsed_query)
            if result and "_id" in result:
                result["_id"] = str(result["_id"])
        
        elif normalized_operation == "insert_one":
            insert_result = coll.insert_one(parsed_document)
            result = {"inserted_id": str(insert_result.inserted_id)}
        
        elif normalized_operation == "insert_many":
            if not isinstance(parsed_document, list):
                return validation_error("insert_many requires a list of documents", field="document")
            insert_result = coll.insert_many(parsed_document)
            result = {"inserted_ids": [str(id) for id in insert_result.inserted_ids]}
        
        elif normalized_operation == "update_one":
            update_result = coll.update_one(parsed_query, parsed_update)
            result = {
                "matched_count": update_result.matched_count,
                "modified_count": update_result.modified_count,
            }
        
        elif normalized_operation == "update_many":
            update_result = coll.update_many(parsed_query, parsed_update)
            result = {
                "matched_count": update_result.matched_count,
                "modified_count": update_result.modified_count,
            }
        
        elif normalized_operation == "delete_one":
            delete_result = coll.delete_one(parsed_query)
            result = {"deleted_count": delete_result.deleted_count}
        
        elif normalized_operation == "delete_many":
            delete_result = coll.delete_many(parsed_query)
            result = {"deleted_count": delete_result.deleted_count}
        
        elif normalized_operation == "count":
            result = {"count": coll.count_documents(parsed_query)}
        
        client.close()
        
        return {"output": result}
    
    except ImportError:
        return error_output(
            "pymongo not installed. Install with: pip install pymongo",
            status_code=500,
        )
    except PyMongoError as e:
        return error_output(f"MongoDB error: {str(e)}", status_code=500)
    except Exception as e:
        return error_output(str(e), status_code=500)
