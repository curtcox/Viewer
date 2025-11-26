"""API endpoints for CID editor conversion functionality."""

from typing import Any, Dict

from flask import Response, jsonify, request

from cid_editor_helper import (
    CidContentStatus,
    check_cid_content,
    generate_cid_from_content,
    store_content_as_cid,
)
from cid_presenter import render_cid_link

from . import main_bp


@main_bp.route('/api/cid/check', methods=['POST'])
def check_cid_status() -> Response:
    """Check if content is a CID and resolve its contents.

    Request body:
        content: string - The content to check

    Returns:
        JSON response with CID status information
    """
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')

    if not content:
        return jsonify({
            'is_cid': False,
            'status': CidContentStatus.NOT_A_CID.value,
        })

    result = check_cid_content(content)

    response: Dict[str, Any] = {
        'is_cid': result.is_cid,
        'status': result.status.value,
    }

    if result.is_cid:
        response['cid_value'] = result.cid_value
        response['cid_link_html'] = str(render_cid_link(result.cid_value))

        if result.status == CidContentStatus.CONTENT_EMBEDDED:
            response['has_content'] = True
            response['content'] = result.content_text
        elif result.status == CidContentStatus.CONTENT_FOUND:
            response['has_content'] = True
            response['content'] = result.content_text
        else:
            response['has_content'] = False
            response['message'] = 'Content not found'

    return jsonify(response)


@main_bp.route('/api/cid/generate', methods=['POST'])
def generate_cid_for_content() -> Response:
    """Generate a CID for the given content.

    Request body:
        content: string - The content to generate a CID for
        store: boolean (optional) - Whether to store the content in the database

    Returns:
        JSON response with the generated CID
    """
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    should_store = data.get('store', False)

    if should_store:
        cid_value = store_content_as_cid(content)
    else:
        cid_value, _ = generate_cid_from_content(content)

    return jsonify({
        'cid_value': cid_value,
        'cid_link_html': str(render_cid_link(cid_value)),
    })


__all__ = ['check_cid_status', 'generate_cid_for_content']
