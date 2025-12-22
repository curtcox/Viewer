import builtins
import hashlib
import textwrap
import typing
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from cid_presenter import cid_path
from cid_utils import store_cid_from_bytes
from db_access import get_cid_by_path


def _extract_future_imports(body_text: str) -> tuple[str, str]:
    """Separate ``__future__`` imports from the rest of the body text.

    Future imports must appear at the start of the compiled module. When we wrap
    user code inside a helper function, those imports would otherwise become
    invalid. We hoist them to the module prefix so they apply to the generated
    function definition.
    """

    future_imports: list[str] = []
    remaining_lines: list[str] = []

    for line in body_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("from __future__ import"):
            future_imports.append(stripped)
            continue
        remaining_lines.append(line)

    header = "\n".join(future_imports).strip()
    if header:
        header += "\n\n"

    return header, "\n".join(remaining_lines)


def _coerce_to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return str(value).encode("utf-8")


def _save_content(value: Any) -> str:
    content = _coerce_to_bytes(value)
    return store_cid_from_bytes(content)


def _load_content(
    cid_value: str, *, encoding: str | None = "utf-8", errors: str = "strict"
):
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
) -> Any:
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

    future_imports, cleaned_body = _extract_future_imports(body_text)

    # Compose the source
    src = (
        f"{future_imports}def {fn_name}({', '.join(param_names)}):\n"
        f"{textwrap.indent(cleaned_body, '    ')}"
    )

    # Global namespace with all builtins available plus helper utilities
    ns = {
        "__builtins__": builtins,
        "save": _save_content,
        "load": _load_content,
    }
    ns.update(_SAFE_TYPING_GLOBALS)

    # Define and run
    # pylint: disable=exec-used
    # This is core functionality - dynamically executing user-defined server code.
    # Security: Only authenticated users can define servers, and code runs in app context
    # with proper authentication/authorization checks. All builtins are available by design.
    exec(src, ns, ns)  # defines ns[fn_name]
    fn = ns[fn_name]
    kwargs = {p: arg_map[p] for p in param_names}
    return fn(**kwargs)
