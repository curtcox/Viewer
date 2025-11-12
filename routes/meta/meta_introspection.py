"""Source code introspection and route metadata building for meta route."""
from __future__ import annotations

import ast
import inspect
import os
import textwrap
from typing import Any, Dict, List, Optional

from flask import current_app

from .meta_path_utils import dedupe_links


def collect_source_links(obj: Any) -> List[str]:
    """Return /source links associated with the supplied callable if available."""
    if obj is None:
        return []

    candidates: List[str] = []
    repo_root = os.path.abspath(current_app.root_path)

    for target in (obj, inspect.unwrap(obj)):
        try:
            source_path = inspect.getsourcefile(target) or inspect.getfile(target)
        except (TypeError, OSError):
            continue

        if not source_path:
            continue

        abs_path = os.path.abspath(source_path)
        try:
            common = os.path.commonpath([repo_root, abs_path])
        except ValueError:
            continue

        if common != repo_root:
            continue

        relative_path = os.path.relpath(abs_path, repo_root).replace(os.sep, "/")
        candidates.append(f"/source/{relative_path}")

    return dedupe_links(candidates)


def collect_template_links(obj: Any) -> List[str]:
    """Return /source links for templates rendered by the supplied callable."""
    if obj is None:
        return []

    try:
        source = inspect.getsource(obj)
    except (OSError, TypeError):
        return []

    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return []

    template_names: List[str] = []

    class TemplateVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:  # pragma: no cover - simple traversal
            func = node.func
            func_name: Optional[str] = None
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr

            if func_name == "render_template" and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    template_names.append(first_arg.value)

            self.generic_visit(node)

    TemplateVisitor().visit(tree)

    if not template_names:
        return []

    repo_root = os.path.abspath(current_app.root_path)
    links: List[str] = []

    loader = getattr(current_app, "jinja_loader", None)
    search_paths: List[str] = []
    if loader is not None:
        search_paths.extend(getattr(loader, "searchpath", []) or [])

    default_templates = os.path.join(current_app.root_path, "templates")
    if default_templates not in search_paths:
        search_paths.append(default_templates)

    for template_name in template_names:
        found_path: Optional[str] = None
        for base in search_paths:
            candidate = os.path.abspath(os.path.join(base, template_name))
            if os.path.isfile(candidate):
                found_path = candidate
                break

        if not found_path:
            continue

        try:
            relative_path = os.path.relpath(found_path, repo_root).replace(os.sep, "/")
        except ValueError:
            continue

        links.append(f"/source/{relative_path}")

    return dedupe_links(links)


def build_route_resolution(path: str, rule: Any, values: Dict[str, Any], status_code: int = 200, meta_source_link: str = "/source/routes/meta.py") -> Dict[str, Any]:
    """Return metadata for a matched Flask route."""
    endpoint = getattr(rule, "endpoint", None)
    methods = sorted(m for m in (getattr(rule, "methods", None) or []) if m not in {"HEAD", "OPTIONS"})
    view_func = current_app.view_functions.get(endpoint) if endpoint else None
    unwrapped = inspect.unwrap(view_func) if view_func else None

    resolution: Dict[str, Any] = {
        "path": path,
        "status_code": status_code,
        "resolution": {
            "type": "route",
            "endpoint": endpoint,
            "rule": getattr(rule, "rule", None),
            "arguments": values,
            "methods": methods,
            "blueprint": endpoint.split(".", 1)[0] if endpoint and "." in endpoint else None,
            "callable": f"{unwrapped.__module__}.{unwrapped.__name__}" if unwrapped else None,
            "docstring": inspect.getdoc(unwrapped) if unwrapped else None,
        },
        "source_links": dedupe_links(
            collect_source_links(view_func)
            + collect_template_links(view_func)
            + [meta_source_link]
        ),
    }

    return resolution
