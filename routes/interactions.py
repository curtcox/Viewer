from flask import jsonify, request
from identity import current_user

from db_access import record_entity_interaction
from interaction_log import load_interaction_history, summarise_interaction

from . import main_bp


@main_bp.route('/api/interactions', methods=['POST'])
def create_interaction_entry():
    """Persist an interaction triggered from the client and return updated history."""

    payload = request.get_json(silent=True) or {}

    entity_type = (payload.get('entity_type') or '').strip()
    entity_name = (payload.get('entity_name') or '').strip()
    action = (payload.get('action') or '').strip() or 'ai'
    message = payload.get('message')
    content = payload.get('content') or ''

    if not entity_type or not entity_name:
        return jsonify({'error': 'Entity details are required.'}), 400

    if content is None:
        content = ''

    interaction = record_entity_interaction(
        current_user.id,
        entity_type,
        entity_name,
        action,
        message,
        content,
    )

    history = load_interaction_history(current_user.id, entity_type, entity_name)

    return jsonify(
        {
            'interaction': summarise_interaction(interaction) if interaction else None,
            'interactions': history,
        }
    )


__all__ = ['create_interaction_entry']

