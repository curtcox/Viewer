"""Pipeline debug response formatting.

This module provides functions to format pipeline execution results
for debug mode output in various formats (JSON, HTML, plain text).
"""

import html
import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from flask import Response

from server_execution.pipeline_execution import (
    ParameterInfo,
    PathSegmentInfo,
    PipelineExecutionResult,
)


def parameter_info_to_dict(param: ParameterInfo) -> Dict[str, Any]:
    """Convert a ParameterInfo to a serializable dictionary.

    Args:
        param: The parameter info to convert

    Returns:
        Dictionary representation
    """
    return {
        "name": param.name,
        "required": param.required,
        "source": param.source,
        "value": param.value,
    }


def segment_info_to_dict(segment: PathSegmentInfo) -> Dict[str, Any]:
    """Convert a PathSegmentInfo to a serializable dictionary.

    Converts the dataclass to a dictionary suitable for JSON serialization,
    handling nested dataclasses like ParameterInfo.

    Args:
        segment: The segment info to convert

    Returns:
        Dictionary representation with all fields
    """
    result: Dict[str, Any] = {
        "segment_text": segment.segment_text,
        "segment_type": segment.segment_type,
        "resolution_type": segment.resolution_type,
        "is_valid_cid": segment.is_valid_cid,
        "cid_validation_error": segment.cid_validation_error,
        "aliases_involved": segment.aliases_involved,
        "server_name": segment.server_name,
        "server_definition_cid": segment.server_definition_cid,
        "supports_chaining": segment.supports_chaining,
        "implementation_language": segment.implementation_language,
        "input_parameters": [
            parameter_info_to_dict(p) for p in segment.input_parameters
        ],
        "parameter_values": segment.parameter_values,
        "executed": segment.executed,
        "input_value": segment.input_value,
        "intermediate_output": segment.intermediate_output,
        "intermediate_content_type": segment.intermediate_content_type,
        "server_invocation_cid": segment.server_invocation_cid,
        "errors": segment.errors,
    }
    return result


def result_to_dict(result: PipelineExecutionResult) -> Dict[str, Any]:
    """Convert a PipelineExecutionResult to a serializable dictionary.

    Args:
        result: The pipeline execution result

    Returns:
        Dictionary representation
    """
    return {
        "segments": [segment_info_to_dict(s) for s in result.segments],
        "final_output": result.final_output,
        "final_content_type": result.final_content_type,
        "success": result.success,
        "error_message": result.error_message,
    }


def format_debug_json(result: PipelineExecutionResult) -> Response:
    """Format pipeline result as JSON response.

    Args:
        result: The pipeline execution result

    Returns:
        Flask Response with JSON content
    """
    data = result_to_dict(result)
    json_str = json.dumps(data, indent=2, default=str)
    return Response(json_str, mimetype="application/json")


def _escape_html(value: Any) -> str:
    """Escape a value for safe HTML display."""
    if value is None:
        return '<span class="null">null</span>'
    if isinstance(value, bool):
        return f'<span class="bool">{str(value).lower()}</span>'
    if isinstance(value, (int, float)):
        return f'<span class="number">{value}</span>'
    if isinstance(value, list):
        if not value:
            return '<span class="empty">[]</span>'
        items = ", ".join(_escape_html(v) for v in value)
        return f"[{items}]"
    if isinstance(value, dict):
        if not value:
            return '<span class="empty">{}</span>'
        items = ", ".join(f"{k}: {_escape_html(v)}" for k, v in value.items())
        return f"{{{items}}}"
    return html.escape(str(value))


def _format_segment_html(segment: PathSegmentInfo, index: int) -> str:
    """Format a single segment as HTML.

    Args:
        segment: The segment info
        index: Segment index

    Returns:
        HTML string
    """
    status_class = "success" if not segment.errors else "error"
    executed_badge = (
        '<span class="badge executed">Executed</span>'
        if segment.executed
        else '<span class="badge not-executed">Not Executed</span>'
    )

    errors_html = ""
    if segment.errors:
        error_items = "".join(
            f"<li>{html.escape(e)}</li>" for e in segment.errors
        )
        errors_html = f'<div class="errors"><strong>Errors:</strong><ul>{error_items}</ul></div>'

    params_html = ""
    if segment.input_parameters:
        param_rows = ""
        for p in segment.input_parameters:
            req_class = "required" if p.required else "optional"
            param_rows += f"""
                <tr>
                    <td>{html.escape(p.name)}</td>
                    <td class="{req_class}">{"required" if p.required else "optional"}</td>
                    <td>{html.escape(p.source or "")}</td>
                    <td>{_escape_html(p.value)}</td>
                </tr>"""
        params_html = f"""
            <div class="parameters">
                <strong>Parameters:</strong>
                <table>
                    <tr><th>Name</th><th>Required</th><th>Source</th><th>Value</th></tr>
                    {param_rows}
                </table>
            </div>"""

    aliases_html = ""
    if segment.aliases_involved:
        aliases_list = " → ".join(html.escape(a) for a in segment.aliases_involved)
        aliases_html = f'<div class="aliases"><strong>Aliases:</strong> {aliases_list}</div>'

    intermediate_html = ""
    if segment.intermediate_output is not None:
        output_preview = str(segment.intermediate_output)
        if len(output_preview) > 500:
            output_preview = output_preview[:500] + "..."
        intermediate_html = f"""
            <div class="output">
                <strong>Output:</strong>
                <pre>{html.escape(output_preview)}</pre>
            </div>"""

    return f"""
        <div class="segment {status_class}">
            <h3>Segment {index}: {html.escape(segment.segment_text)} {executed_badge}</h3>
            <table class="info">
                <tr><th>Type:</th><td>{html.escape(segment.segment_type)}</td></tr>
                <tr><th>Resolution:</th><td>{html.escape(segment.resolution_type)}</td></tr>
                <tr><th>Server Name:</th><td>{_escape_html(segment.server_name)}</td></tr>
                <tr><th>Language:</th><td>{_escape_html(segment.implementation_language)}</td></tr>
                <tr><th>Supports Chaining:</th><td>{_escape_html(segment.supports_chaining)}</td></tr>
                <tr><th>Valid CID:</th><td>{_escape_html(segment.is_valid_cid)}</td></tr>
                <tr><th>Definition CID:</th><td>{_escape_html(segment.server_definition_cid)}</td></tr>
                <tr><th>Invocation CID:</th><td>{_escape_html(segment.server_invocation_cid)}</td></tr>
            </table>
            {aliases_html}
            {params_html}
            {errors_html}
            {intermediate_html}
        </div>"""


def format_debug_html(result: PipelineExecutionResult) -> Response:
    """Format pipeline result as HTML response.

    Args:
        result: The pipeline execution result

    Returns:
        Flask Response with HTML content
    """
    status_class = "success" if result.success else "failure"
    status_text = "Success" if result.success else "Failed"

    segments_html = "\n".join(
        _format_segment_html(seg, i) for i, seg in enumerate(result.segments)
    )

    final_output_html = ""
    if result.final_output is not None:
        output_str = str(result.final_output)
        if len(output_str) > 1000:
            output_str = output_str[:1000] + "..."
        final_output_html = f"""
            <div class="final-output">
                <h3>Final Output</h3>
                <pre>{html.escape(output_str)}</pre>
                <p><strong>Content-Type:</strong> {html.escape(result.final_content_type)}</p>
            </div>"""

    error_html = ""
    if result.error_message:
        error_html = f'<div class="error-message"><strong>Error:</strong> {html.escape(result.error_message)}</div>'

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Pipeline Debug</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
        h3 {{ color: #666; margin-bottom: 10px; }}
        .status {{ padding: 10px 20px; border-radius: 5px; display: inline-block; margin-bottom: 20px; }}
        .status.success {{ background: #d4edda; color: #155724; }}
        .status.failure {{ background: #f8d7da; color: #721c24; }}
        .segment {{ border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 15px; }}
        .segment.success {{ border-left: 4px solid #28a745; }}
        .segment.error {{ border-left: 4px solid #dc3545; }}
        .badge {{ padding: 2px 8px; border-radius: 3px; font-size: 12px; }}
        .badge.executed {{ background: #28a745; color: white; }}
        .badge.not-executed {{ background: #6c757d; color: white; }}
        table {{ border-collapse: collapse; margin: 10px 0; }}
        table.info th {{ text-align: left; padding: 4px 10px 4px 0; color: #666; }}
        table.info td {{ padding: 4px 0; }}
        .parameters table {{ width: 100%; }}
        .parameters th, .parameters td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .parameters th {{ background: #f5f5f5; }}
        .required {{ color: #dc3545; }}
        .optional {{ color: #6c757d; }}
        .errors {{ background: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 10px; }}
        .errors ul {{ margin: 5px 0; padding-left: 20px; }}
        .output pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        .final-output {{ background: #e9ecef; padding: 15px; border-radius: 5px; margin-top: 20px; }}
        .final-output pre {{ background: white; }}
        .error-message {{ background: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; }}
        .null {{ color: #999; font-style: italic; }}
        .bool {{ color: #0066cc; }}
        .number {{ color: #0066cc; }}
        .empty {{ color: #999; }}
    </style>
</head>
<body>
    <h1>Pipeline Debug</h1>
    <div class="status {status_class}">{status_text}</div>
    {error_html}

    <h2>Segments ({len(result.segments)})</h2>
    {segments_html}

    {final_output_html}
</body>
</html>"""
    return Response(html_content, mimetype="text/html")


def _format_segment_text(segment: PathSegmentInfo, index: int) -> str:
    """Format a single segment as plain text.

    Args:
        segment: The segment info
        index: Segment index

    Returns:
        Plain text string
    """
    lines = [
        f"=== Segment {index}: {segment.segment_text} ===",
        f"Type:               {segment.segment_type}",
        f"Resolution:         {segment.resolution_type}",
        f"Executed:           {segment.executed}",
    ]

    if segment.server_name:
        lines.append(f"Server Name:        {segment.server_name}")
    if segment.implementation_language:
        lines.append(f"Language:           {segment.implementation_language}")
    if segment.server_definition_cid:
        lines.append(f"Definition CID:     {segment.server_definition_cid}")

    lines.append(f"Supports Chaining:  {segment.supports_chaining}")
    lines.append(f"Valid CID:          {segment.is_valid_cid}")

    if segment.cid_validation_error:
        lines.append(f"CID Error:          {segment.cid_validation_error}")

    if segment.aliases_involved:
        lines.append(f"Aliases:            {' -> '.join(segment.aliases_involved)}")

    if segment.input_parameters:
        lines.append("Parameters:")
        for p in segment.input_parameters:
            req = "required" if p.required else "optional"
            source = p.source or "-"
            value = str(p.value) if p.value is not None else "-"
            lines.append(f"  - {p.name}: {value} ({req}, from {source})")

    if segment.errors:
        lines.append("Errors:")
        for e in segment.errors:
            lines.append(f"  ! {e}")

    if segment.intermediate_output is not None:
        output_str = str(segment.intermediate_output)
        if len(output_str) > 200:
            output_str = output_str[:200] + "..."
        lines.append(f"Output:             {output_str}")

    if segment.server_invocation_cid:
        lines.append(f"Invocation CID:     {segment.server_invocation_cid}")

    return "\n".join(lines)


def format_debug_text(result: PipelineExecutionResult) -> Response:
    """Format pipeline result as plain text response.

    Args:
        result: The pipeline execution result

    Returns:
        Flask Response with plain text content
    """
    lines = [
        "PIPELINE DEBUG",
        "=" * 60,
        f"Status: {'SUCCESS' if result.success else 'FAILED'}",
    ]

    if result.error_message:
        lines.append(f"Error: {result.error_message}")

    lines.append(f"Segments: {len(result.segments)}")
    lines.append("")

    for i, seg in enumerate(result.segments):
        lines.append(_format_segment_text(seg, i))
        lines.append("")

    if result.final_output is not None:
        lines.append("=" * 60)
        lines.append("FINAL OUTPUT")
        lines.append("-" * 60)
        output_str = str(result.final_output)
        if len(output_str) > 500:
            output_str = output_str[:500] + "..."
        lines.append(output_str)
        lines.append(f"Content-Type: {result.final_content_type}")

    return Response("\n".join(lines), mimetype="text/plain")


def format_debug_response(
    result: PipelineExecutionResult, output_format: Optional[str] = None
) -> Response:
    """Format the pipeline execution result as a debug response.

    Respects the output format parameter:
    - "json" or None -> JSON response (default)
    - "html" -> HTML formatted response
    - "txt" or "text" -> Plain text response

    Args:
        result: The pipeline execution result
        output_format: The desired output format (json, html, txt)

    Returns:
        Flask Response with appropriate content type
    """
    if output_format is None:
        output_format = "json"

    fmt = output_format.lower()

    if fmt == "html":
        return format_debug_html(result)
    if fmt in ("txt", "text"):
        return format_debug_text(result)

    # Default to JSON
    return format_debug_json(result)


__all__ = [
    "format_debug_response",
    "format_debug_html",
    "format_debug_json",
    "format_debug_text",
    "parameter_info_to_dict",
    "result_to_dict",
    "segment_info_to_dict",
]
