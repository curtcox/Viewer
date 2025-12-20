import json

from routes.import_export.change_history import (
    HistoryEvent,
    prepare_history_event,
)
from routes.import_export.import_sources import parse_import_payload
from routes.import_export.import_entities import (
    import_variables_with_names,
    prepare_server_import,
)


def test_parse_import_payload_success():
    payload = json.dumps({"version": 1})

    parsed, error = parse_import_payload(f"\n{payload}\n")

    assert error is None
    assert parsed is not None
    assert parsed.raw_text == payload
    assert parsed.data == {"version": 1}


def test_parse_import_payload_errors():
    parsed, error = parse_import_payload("   ")
    assert parsed is None
    assert error == "Import data was empty."

    parsed, error = parse_import_payload("not json")
    assert parsed is None
    assert error.startswith("Failed to parse JSON:")

    parsed, error = parse_import_payload("[]")
    assert parsed is None
    assert error == "Import file must contain a JSON object."


def test_prepare_server_import_prefers_definition():
    entry = {"name": "demo", "definition": "sample"}
    errors: list[str] = []

    result = prepare_server_import(entry, {}, errors)

    assert not errors
    assert result is not None
    assert result.name == "demo"
    assert result.definition == "sample"


def test_prepare_server_import_falls_back_to_cid():
    entry = {"name": "demo", "definition_cid": "abc"}
    errors: list[str] = []

    result = prepare_server_import(entry, {"abc": b"content"}, errors)

    assert not errors
    assert result is not None
    assert result.definition == "content"


def test_prepare_server_import_reports_missing_data():
    entry = {"name": "demo"}
    errors: list[str] = []

    result = prepare_server_import(entry, {}, errors)

    assert result is None
    assert errors == [
        'Server "demo" entry must include either a definition or a definition_cid.'
    ]


def test_import_variables_supports_definition_file_via_cid_map():
    raw_variables = [
        {
            "name": "AI_SYSTEM_PROMPTS",
            "definition_file": "cid-prompts",
            "enabled": True,
        }
    ]

    imported, errors, names = import_variables_with_names(
        raw_variables,
        cid_map={"cid-prompts": b'{"prompts": []}'},
    )

    assert imported == 1
    assert not errors
    assert names == ["AI_SYSTEM_PROMPTS"]


def test_import_variables_reports_index_and_entry_details_on_missing_definition():
    raw_variables = [{"name": "broken", "enabled": True}]

    imported, errors, names = import_variables_with_names(raw_variables, cid_map={})

    assert imported == 0
    assert not names
    assert len(errors) == 1
    assert "index 0" in errors[0]
    assert "keys=" in errors[0]


def test_prepare_history_event_truncates_long_messages():
    raw_event = {
        "timestamp": "2024-01-01T00:00:00Z",
        "action": "save",
        "message": "x" * 600,
        "content": " body ",
    }
    errors: list[str] = []

    event = prepare_history_event("demo", raw_event, errors)

    assert not errors
    assert isinstance(event, HistoryEvent)
    assert event.message.endswith("…")
    assert len(event.message) == 498  # 497 characters plus ellipsis
    assert event.content == "body"


def test_prepare_history_event_reports_invalid_timestamp():
    raw_event = {
        "timestamp": "invalid",
    }
    errors: list[str] = []

    event = prepare_history_event("demo", raw_event, errors)

    assert event is None
    assert errors == ['History event for "demo" has an invalid timestamp.']
