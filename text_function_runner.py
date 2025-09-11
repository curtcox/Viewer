import builtins
import hashlib
import textwrap
from typing import Dict

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

    # Global namespace with all builtins available
    ns = {"__builtins__": builtins}

    # Define and run
    exec(src, ns, ns)  # defines ns[fn_name]
    fn = ns[fn_name]
    kwargs = {p: arg_map[p] for p in param_names}
    return fn(**kwargs)
