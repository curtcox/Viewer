import builtins
import hashlib
import textwrap
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union

import typing

from cid_presenter import cid_path
from cid_utils import store_cid_from_bytes
from db_access import get_cid_by_path
from identity import current_user


def _coerce_to_bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return str(value).encode("utf-8")


def _get_current_user_id():
    try:
        user = current_user
    except Exception:
        return None

    user_id = getattr(user, "id", None)
    if callable(user_id):
        try:
            user_id = user_id()
        except TypeError:
            user_id = None

    if not user_id:
        getter = getattr(user, "get_id", None)
        if callable(getter):
            user_id = getter()

    if user_id is None:
        return None

    return str(user_id)


def _save_content(value):
    user_id = _get_current_user_id()
    if not user_id:
        raise RuntimeError("save() requires an authenticated user with an id")

    content = _coerce_to_bytes(value)
    return store_cid_from_bytes(content, user_id)


def _load_content(cid_value: str, *, encoding: str | None = "utf-8", errors: str = "strict"):
    """Return the stored CID content, optionally decoding it as text."""

    if not isinstance(cid_value, str):
        raise TypeError("cid must be provided as a string")

    normalized_path = cid_path(cid_value)
    if not normalized_path:
        raise ValueError("cid must not be empty")

    record = get_cid_by_path(normalized_path)
    if record is None:
        raise ValueError(f"CID {cid_value!r} does not exist")

    data = getattr(record, "file_data", b"")
    if not isinstance(data, (bytes, bytearray)):
        data = _coerce_to_bytes(data)

    if encoding is None:
        return bytes(data)

    return bytes(data).decode(encoding, errors)

_SAFE_TYPING_GLOBALS = {
    "typing": typing,
    "Any": Any,
    "Callable": typing.Callable,
    "Dict": Dict,
    "Iterable": Iterable,
    "List": List,
    "Mapping": Mapping,
    "Optional": Optional,
    "Sequence": Sequence,
    "Set": Set,
    "Tuple": Tuple,
    "Union": Union,
}


def run_text_function(
    body_text: str,
    arg_map: Dict[str, object],
):
    """
    Define and execute a function from multi-line Python `body_text` in one call.

    - The function name is derived from a hash of `body_text`.
    - Arguments are supplied via `arg_map` (dict of {param_name: value}).
    - The parameter list is derived from sorted(arg_map.keys()) for determinism.
    - All builtins are available to the function.

    Returns: the function's return value.
    """
    if not isinstance(body_text, str):
        raise TypeError("body_text must be a string")
    if not isinstance(arg_map, dict):
        raise TypeError("arg_map must be a dict")

    # Determine parameter names (sorted for determinism)
    param_names = sorted(arg_map.keys())

    # Hash-based function name (deterministic for same body_text)
    h = hashlib.sha256(body_text.encode("utf-8")).hexdigest()[:12]
    fn_name = f"_fn_{h}"

    # Compose the source
    src = f"def {fn_name}({', '.join(param_names)}):\n{textwrap.indent(body_text, '    ')}"

    # Global namespace with all builtins available plus helper utilities
    ns = {
        "__builtins__": builtins,
        "save": _save_content,
        "load": _load_content,
    }
    ns.update(_SAFE_TYPING_GLOBALS)

    # Define and run
    exec(src, ns, ns)  # defines ns[fn_name]
    fn = ns[fn_name]
    kwargs = {p: arg_map[p] for p in param_names}
    return fn(**kwargs)
