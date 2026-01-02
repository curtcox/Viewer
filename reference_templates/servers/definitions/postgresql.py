# ruff: noqa: F821, F706
"""Execute PostgreSQL database queries with connection management."""

from __future__ import annotations

from typing import Any, Dict, Optional
import json

from server_utils.external_api import error_output, validation_error


def _build_preview(
    *,
    operation: str,
    query: Optional[str],
    host: str,
    database: str,
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a preview of the PostgreSQL operation."""
    preview: Dict[str, Any] = {
        "operation": operation,
        "host": host,
        "database": database,
        "auth": "PostgreSQL username/password",
    }
    if query:
        preview["query"] = query
    if params:
        preview["params"] = params
    return preview


def main(
    *,
    operation: str = "query",
    query: str = "",
    params: Optional[str] = None,
    POSTGRESQL_HOST: str = "",
    POSTGRESQL_PORT: int = 5432,
    POSTGRESQL_USER: str = "",
    POSTGRESQL_PASSWORD: str = "",
    POSTGRESQL_DATABASE: str = "",
    connection_timeout: int = 10,
    query_timeout: int = 60,
    dry_run: bool = True,
    context=None,
) -> Dict[str, Any]:
    """Execute PostgreSQL database queries.
    
    Operations:
    - query: Execute a SELECT query
    - execute: Execute an INSERT/UPDATE/DELETE statement
    - fetchone: Fetch a single row
    - fetchall: Fetch all rows
    """
    
    normalized_operation = operation.lower()
    valid_operations = {"query", "execute", "fetchone", "fetchall"}
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")
    
    # Validate credentials
    if not POSTGRESQL_HOST:
        return error_output("Missing POSTGRESQL_HOST", status_code=401)
    
    if not POSTGRESQL_USER:
        return error_output("Missing POSTGRESQL_USER", status_code=401)
    
    if not POSTGRESQL_PASSWORD:
        return error_output("Missing POSTGRESQL_PASSWORD", status_code=401)
    
    if not POSTGRESQL_DATABASE:
        return error_output("Missing POSTGRESQL_DATABASE", status_code=401)
    
    # Validate query
    if not query:
        return validation_error("Missing required query", field="query")
    
    # Parse params if provided
    parsed_params = None
    if params:
        try:
            parsed_params = json.loads(params) if isinstance(params, str) else params
        except json.JSONDecodeError:
            return validation_error("Invalid JSON for params", field="params")
    
    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=normalized_operation,
                query=query,
                host=POSTGRESQL_HOST,
                database=POSTGRESQL_DATABASE,
                params=parsed_params,
            )
        }
    
    # Execute actual database operation
    try:
        import psycopg2
        from psycopg2 import Error
        from psycopg2.extras import RealDictCursor
        
        connection = psycopg2.connect(
            host=POSTGRESQL_HOST,
            port=POSTGRESQL_PORT,
            user=POSTGRESQL_USER,
            password=POSTGRESQL_PASSWORD,
            database=POSTGRESQL_DATABASE,
            connect_timeout=connection_timeout,
        )
        
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Set statement timeout - validate timeout is a positive integer
        if not isinstance(query_timeout, int) or query_timeout <= 0:
            cursor.close()
            connection.close()
            return error_output("Invalid query_timeout: must be a positive integer", status_code=400)
        
        # Use parameterized query for timeout setting
        cursor.execute("SET statement_timeout = %s", (query_timeout * 1000,))
        
        if parsed_params:
            cursor.execute(query, parsed_params)
        else:
            cursor.execute(query)
        
        if normalized_operation in ("query", "fetchall"):
            result = [dict(row) for row in cursor.fetchall()]
        elif normalized_operation == "fetchone":
            row = cursor.fetchone()
            result = dict(row) if row else None
        else:  # execute
            connection.commit()
            result = {"rows_affected": cursor.rowcount}
        
        cursor.close()
        connection.close()
        
        return {"output": result}
    
    except ImportError:
        return error_output(
            "psycopg2 not installed. Install with: pip install psycopg2-binary",
            status_code=500,
        )
    except Error as e:
        return error_output(f"PostgreSQL error: {str(e)}", status_code=500)
    except Exception as e:
        return error_output(str(e), status_code=500)
