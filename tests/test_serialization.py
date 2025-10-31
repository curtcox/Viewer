from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from serialization import model_to_dict


class DummyModel:
    def __init__(self, values: dict[str, object]):
        self.__table__ = SimpleNamespace(
            columns=[SimpleNamespace(name=name) for name in values.keys()]
        )
        for key, value in values.items():
            setattr(self, key, value)


def test_model_to_dict_serializes_datetime_values() -> None:
    created_at = datetime(2024, 5, 1, 12, 30, tzinfo=timezone.utc)
    model = DummyModel({"id": 1, "created_at": created_at, "name": "example"})

    serialized = model_to_dict(model)

    assert serialized["id"] == 1
    assert serialized["name"] == "example"
    assert serialized["created_at"] == created_at.isoformat()


def test_model_to_dict_includes_extra_fields() -> None:
    model = DummyModel({"id": 2, "name": "alias"})

    serialized = model_to_dict(model, {"extra": "value"})

    assert serialized["extra"] == "value"


def test_model_to_dict_requires_table_definition() -> None:
    class NoTable:
        pass

    with pytest.raises(AttributeError):
        model_to_dict(NoTable())
