# ruff: noqa: F821, F706
"""Execute Snowflake queries using Snowflake SQL API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    operation: str,
    query: Optional[str],
    account: str,
    warehouse: str,
) -> Dict[str, Any]:
    """Build a preview of the Snowflake operation."""
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": f"https://{account}.snowflakecomputing.com/api/v2/statements",
        "method": "POST",
        "auth": "Basic Auth (username/password)",
        "account": account,
        "warehouse": warehouse,
    }
    if query:
        preview["query"] = query
    return preview


def main(
    *,
    operation: str = "query",
    query: str = "",
    database: str = "",
    schema: str = "",
    SNOWFLAKE_ACCOUNT: str = "",
    SNOWFLAKE_USER: str = "",
    SNOWFLAKE_PASSWORD: str = "",
    SNOWFLAKE_WAREHOUSE: str = "",
    SNOWFLAKE_ROLE: str = "",
    timeout: int = 60,
    dry_run: bool = True,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Execute Snowflake queries using Snowflake SQL API.
    
    Operations:
    - query: Execute a SQL query
    - execute: Execute a SQL statement
    """
    
    normalized_operation = operation.lower()
    valid_operations = {"query", "execute"}
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")
    
    # Validate credentials
    if not SNOWFLAKE_ACCOUNT:
        return error_output("Missing SNOWFLAKE_ACCOUNT", status_code=401)
    
    if not SNOWFLAKE_USER:
        return error_output("Missing SNOWFLAKE_USER", status_code=401)
    
    if not SNOWFLAKE_PASSWORD:
        return error_output("Missing SNOWFLAKE_PASSWORD", status_code=401)
    
    if not SNOWFLAKE_WAREHOUSE:
        return error_output("Missing SNOWFLAKE_WAREHOUSE", status_code=401)
    
    # Validate query
    if not query:
        return validation_error("Missing required query", field="query")
    
    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=normalized_operation,
                query=query,
                account=SNOWFLAKE_ACCOUNT,
                warehouse=SNOWFLAKE_WAREHOUSE,
            )
        }
    
    # Execute actual API call
    api_client = client or _DEFAULT_CLIENT
    
    try:
        import base64
        
        # Build auth header
        auth_string = f"{SNOWFLAKE_USER}:{SNOWFLAKE_PASSWORD}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
        }
        
        # Build payload
        payload: Dict[str, Any] = {
            "statement": query,
            "warehouse": SNOWFLAKE_WAREHOUSE,
            "timeout": timeout,
        }
        
        if database:
            payload["database"] = database
        if schema:
            payload["schema"] = schema
        if SNOWFLAKE_ROLE:
            payload["role"] = SNOWFLAKE_ROLE
        
        url = f"https://{SNOWFLAKE_ACCOUNT}.snowflakecomputing.com/api/v2/statements"
        
        response = api_client.post(
            url=url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        
        if not response.ok:
            return error_output(
                f"Snowflake API error: {response.text}",
                status_code=response.status_code,
                response=response.text,
            )
        
        result = response.json()
        
        # Check if query is still running (async)
        if result.get("statementHandle"):
            # Query is async, would need to poll for results
            return {"output": {
                "status": "submitted",
                "statement_handle": result["statementHandle"],
                "message": "Query submitted. Use statement handle to check status.",
            }}
        
        return {"output": result}
    
    except Exception as e:
        return error_output(str(e), status_code=500)
