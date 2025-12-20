"""Property tests covering serialization helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from hypothesis import given, strategies as st

from serialization import model_to_dict


class DummyModel:
    def __init__(self, values: dict[str, object]):
        self.__table__ = SimpleNamespace(
            columns=[SimpleNamespace(name=name) for name in values.keys()]
        )
        for key, value in values.items():
            setattr(self, key, value)


def _value_strategy() -> st.SearchStrategy[object]:
    return st.one_of(
        st.text(max_size=20),
        st.integers(),
        st.booleans(),
        st.datetimes(timezones=st.just(timezone.utc)),
        st.none(),
    )


@given(st.dictionaries(st.text(min_size=1, max_size=8), _value_strategy(), max_size=5))
def test_model_to_dict_preserves_values(mapping: dict[str, object]) -> None:
    model = DummyModel(mapping)

    serialized = model_to_dict(model)

    assert set(serialized.keys()) == set(mapping.keys())

    for key, value in mapping.items():
        if isinstance(value, datetime):
            assert serialized[key] == value.isoformat()
        else:
            assert serialized[key] is value or serialized[key] == value
