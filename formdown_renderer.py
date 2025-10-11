"""Render Formdown documents into HTML forms without client-side JavaScript."""

from __future__ import annotations

import html
import re
import shlex
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union


_FIELD_PATTERN = re.compile(
    r"^@(?P<name>[a-zA-Z0-9_]+)(?:\((?P<label>[^)]*)\))?:\s*\[(?P<descriptor>[^\]]+)\]$"
)
_FORM_PATTERN = re.compile(r"^@form\[(?P<descriptor>[^\]]+)\]$")


@dataclass
class Heading:
    level: int
    text: str


@dataclass
class Paragraph:
    text: str


@dataclass
class HorizontalRule:
    pass


@dataclass
class FormField:
    name: str
    label: Optional[str]
    control_type: str
    attributes: Dict[str, str] = field(default_factory=dict)


FormElement = Union[Heading, Paragraph, HorizontalRule, FormField]


@dataclass
class FormBlock:
    attributes: Dict[str, str]
    elements: List[FormElement] = field(default_factory=list)


DocumentNode = Union[Heading, Paragraph, HorizontalRule, FormBlock]


BOOLEAN_ATTRIBUTES = {
    "autofocus",
    "checked",
    "disabled",
    "multiple",
    "readonly",
    "required",
}

CHOICE_FIELD_TYPES = {"checkbox", "radio"}
TEXT_INPUT_TYPES = {
    "color",
    "date",
    "email",
    "number",
    "range",
    "tel",
    "text",
    "url",
}


def _unescape_attribute_value(value: str) -> str:
    """Reverse the escaping performed when generating formdown attributes."""

    return (
        value.replace("\\n", "\n")
        .replace("\\\\", "\\")
        .replace("\\\"", '"')
    )


def _parse_descriptor(descriptor: str) -> Tuple[str, Dict[str, str]]:
    tokens = shlex.split(descriptor, posix=True)
    if not tokens:
        raise ValueError(f"Descriptor had no tokens: {descriptor!r}")

    control_type, *attribute_tokens = tokens
    attributes: Dict[str, str] = {}
    for token in attribute_tokens:
        if "=" not in token:
            attributes[token] = ""
            continue
        key, value = token.split("=", 1)
        attributes[key] = _unescape_attribute_value(value)
    return control_type, attributes


def _parse_form_attributes(descriptor: str) -> Dict[str, str]:
    _, attributes = _parse_descriptor(f"form {descriptor}")
    return attributes


def _parse_field_line(line: str) -> FormField:
    match = _FIELD_PATTERN.match(line.strip())
    if not match:
        raise ValueError(f"Unable to parse field line: {line!r}")

    descriptor = match.group("descriptor").strip()
    control_type, attributes = _parse_descriptor(descriptor)
    label = match.group("label")
    label = label.strip() if label else None
    return FormField(
        name=match.group("name"),
        label=label,
        control_type=control_type,
        attributes=attributes,
    )


def _parse_line_as_node(line: str) -> Optional[DocumentNode]:
    stripped = line.strip()
    if not stripped:
        return None

    if stripped.startswith("###"):
        return Heading(level=3, text=stripped.lstrip("#").strip())
    if stripped.startswith("##"):
        return Heading(level=2, text=stripped.lstrip("#").strip())
    if stripped.startswith("#"):
        return Heading(level=1, text=stripped.lstrip("#").strip())
    if stripped == "---":
        return HorizontalRule()
    return Paragraph(text=stripped)


def parse_formdown_document(source: str) -> List[DocumentNode]:
    """Parse a formdown fenced block into document nodes."""

    nodes: List[DocumentNode] = []
    current_form: Optional[FormBlock] = None

    for raw_line in source.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        form_match = _FORM_PATTERN.match(stripped)
        if form_match:
            if current_form is not None:
                nodes.append(current_form)
            current_form = FormBlock(attributes=_parse_form_attributes(form_match.group("descriptor")))
            continue

        if stripped.startswith("@") and _FIELD_PATTERN.match(stripped):
            field = _parse_field_line(stripped)
            if current_form is None:
                current_form = FormBlock(attributes={})
            current_form.elements.append(field)
            continue

        node = _parse_line_as_node(stripped)
        if node is None:
            continue

        if current_form is not None:
            current_form.elements.append(node)
        else:
            nodes.append(node)

    if current_form is not None:
        nodes.append(current_form)

    return nodes


def _render_attribute(name: str, value: Optional[str]) -> str:
    if name in BOOLEAN_ATTRIBUTES:
        flag = (value or "").strip().lower()
        if flag in {"", "1", "true", "yes", name}:
            return f" {html.escape(name)}"
        return ""

    if value is None:
        return ""

    return f" {html.escape(name)}=\"{html.escape(value, quote=True)}\""


def _combine_classes(defaults: Sequence[str], custom: Optional[str]) -> str:
    classes: List[str] = [cls for cls in defaults if cls]
    if custom:
        classes.extend(part for part in custom.split() if part)
    return " ".join(dict.fromkeys(classes))


def _generate_field_id(name: str, existing_counts: Dict[str, int]) -> str:
    base = re.sub(r"[^a-zA-Z0-9_-]+", "-", name or "field").strip("-") or "field"
    count = existing_counts.get(base, 0)
    existing_counts[base] = count + 1
    if count:
        return f"{base}-{count + 1}"
    return base


def _render_heading(node: Heading, *, inside_form: bool = False) -> str:
    level = max(1, min(node.level, 6))
    classes = ["formdown-heading"]
    if inside_form:
        classes.append("formdown-heading--form")
    class_attr = " class=\"{}\"".format(" ".join(classes)) if classes else ""
    return f"<h{level}{class_attr}>{html.escape(node.text)}</h{level}>"


def _render_paragraph(node: Paragraph, *, inside_form: bool = False) -> str:
    classes = ["formdown-paragraph"]
    if inside_form:
        classes.append("formdown-paragraph--form")
    class_attr = " class=\"{}\"".format(" ".join(classes)) if classes else ""
    return f"<p{class_attr}>{html.escape(node.text)}</p>"


def _render_horizontal_rule(node: HorizontalRule) -> str:
    return '<hr class="formdown-separator">'


def _parse_choice_options(option_string: str) -> List[Tuple[str, str]]:
    options: List[Tuple[str, str]] = []
    for raw_option in option_string.split(","):
        option = raw_option.strip()
        if not option:
            continue
        if "|" in option:
            value, label = (part.strip() for part in option.split("|", 1))
        elif "=" in option:
            value, label = (part.strip() for part in option.split("=", 1))
        else:
            value = label = option
        options.append((value, label))
    return options


def _render_choice_field(field: FormField, field_id: str) -> str:
    options_attr = field.attributes.pop("options", "")
    options = _parse_choice_options(options_attr)
    if not options:
        return ""

    layout_class = "formdown-options"
    layout = field.attributes.pop("layout", "").strip().lower()
    if layout == "vertical":
        layout_class += " formdown-options--vertical"

    selected_values: Sequence[str]
    raw_value = field.attributes.pop("value", "")
    if isinstance(raw_value, str) and raw_value:
        selected_values = [item.strip() for item in raw_value.split(",") if item.strip()]
    else:
        selected_values = []

    help_text = field.attributes.pop("help", None)
    label_text = field.label or field.attributes.pop("label", None) or field.name

    container = [
        '<fieldset class="formdown-field formdown-field--choices">',
        f"<legend class=\"formdown-label\">{html.escape(label_text)}</legend>",
        f"<div class=\"{layout_class}\">",
    ]

    base_classes = ["formdown-input", f"formdown-input--{field.control_type}"]

    for index, (value, label) in enumerate(options):
        option_id = f"{field_id}-{index + 1}"
        input_attrs = {
            "type": field.control_type,
            "name": field.name,
            "id": option_id,
            "value": value,
            "class": _combine_classes(base_classes, field.attributes.get("class")),
        }

        for key, attr_value in list(field.attributes.items()):
            if key in {"class", "help"}:
                continue
            input_attrs[key] = attr_value

        if value in selected_values:
            input_attrs["checked"] = ""

        rendered_attrs = "".join(_render_attribute(key, input_attrs[key]) for key in sorted(input_attrs))
        container.append(
            f"<label class=\"formdown-option\" for=\"{html.escape(option_id)}\">"
            f"<input{rendered_attrs}>"
            f"<span class=\"formdown-option-label\">{html.escape(label)}</span>"
            "</label>"
        )

    container.append("</div>")
    if help_text:
        container.append(f"<div class=\"formdown-help\">{html.escape(help_text)}</div>")
    container.append("</fieldset>")
    return "\n".join(container)


def _render_select_field(field: FormField, field_id: str) -> str:
    options_attr = field.attributes.pop("options", "")
    options = _parse_choice_options(options_attr)
    help_text = field.attributes.pop("help", None)
    label_text = field.label or field.attributes.pop("label", None) or field.name

    raw_value = field.attributes.pop("value", "")
    selected_values = {item.strip() for item in raw_value.split(",") if item.strip()} if raw_value else set()

    select_attrs = {
        "name": field.name,
        "id": field_id,
        "class": _combine_classes(["formdown-input", "formdown-input--select"], field.attributes.pop("class", None)),
    }

    for key, value in field.attributes.items():
        if key == "help":
            continue
        select_attrs[key] = value

    parts = [
        '<div class="formdown-field">',
        f"<label class=\"formdown-label\" for=\"{html.escape(field_id)}\">{html.escape(label_text)}</label>",
    ]

    rendered_attrs = "".join(_render_attribute(key, select_attrs[key]) for key in sorted(select_attrs))
    parts.append(f"<select{rendered_attrs}>")
    for value, label in options:
        option_attrs = {
            "value": value,
            "selected": "" if value in selected_values else None,
        }
        attr_html = "".join(_render_attribute(key, option_attrs[key]) for key in sorted(option_attrs) if option_attrs[key] is not None)
        parts.append(f"<option{attr_html}>{html.escape(label)}</option>")
    parts.append("</select>")
    if help_text:
        parts.append(f"<div class=\"formdown-help\">{html.escape(help_text)}</div>")
    parts.append("</div>")
    return "\n".join(parts)


def _render_textarea_field(field: FormField, field_id: str) -> str:
    help_text = field.attributes.pop("help", None)
    label_text = field.label or field.attributes.pop("label", None) or field.name

    value = field.attributes.pop("value", "")

    textarea_attrs = {
        "name": field.name,
        "id": field_id,
        "class": _combine_classes(["formdown-input", "formdown-input--textarea"], field.attributes.pop("class", None)),
    }

    for key, attr_value in field.attributes.items():
        textarea_attrs[key] = attr_value

    parts = [
        '<div class="formdown-field">',
        f"<label class=\"formdown-label\" for=\"{html.escape(field_id)}\">{html.escape(label_text)}</label>",
    ]

    rendered_attrs = "".join(_render_attribute(key, textarea_attrs[key]) for key in sorted(textarea_attrs))
    parts.append(f"<textarea{rendered_attrs}>{html.escape(value)}</textarea>")
    if help_text:
        parts.append(f"<div class=\"formdown-help\">{html.escape(help_text)}</div>")
    parts.append("</div>")
    return "\n".join(parts)


def _render_text_input_field(field: FormField, field_id: str) -> str:
    help_text = field.attributes.pop("help", None)
    label_text = field.label or field.attributes.pop("label", None) or field.name

    input_attrs = {
        "type": field.control_type,
        "name": field.name,
        "id": field_id,
        "class": _combine_classes(["formdown-input", f"formdown-input--{field.control_type}"], field.attributes.pop("class", None)),
    }

    for key, value in field.attributes.items():
        input_attrs[key] = value

    parts = [
        '<div class="formdown-field">',
        f"<label class=\"formdown-label\" for=\"{html.escape(field_id)}\">{html.escape(label_text)}</label>",
    ]

    rendered_attrs = "".join(_render_attribute(key, input_attrs[key]) for key in sorted(input_attrs))
    parts.append(f"<input{rendered_attrs}>")
    if help_text:
        parts.append(f"<div class=\"formdown-help\">{html.escape(help_text)}</div>")
    parts.append("</div>")
    return "\n".join(parts)


def _render_file_field(field: FormField, field_id: str) -> str:
    field.attributes.setdefault("class", "")
    return _render_text_input_field(field, field_id)


def _render_action_field(field: FormField) -> str:
    label_text = field.attributes.pop("label", None) or field.label or field.name
    button_type = "submit" if field.control_type == "submit" else "reset"

    button_attrs = {
        "type": button_type,
        "name": field.name,
        "class": _combine_classes(["formdown-button", f"formdown-button--{button_type}"], field.attributes.pop("class", None)),
        "value": field.attributes.pop("value", None),
    }

    for key, value in field.attributes.items():
        button_attrs[key] = value

    attr_html = "".join(_render_attribute(key, button_attrs[key]) for key in sorted(button_attrs) if button_attrs[key] is not None)
    return f"<button{attr_html}>{html.escape(label_text)}</button>"


def _render_form_field(field: FormField, id_counts: Dict[str, int]) -> str:
    field = FormField(
        name=field.name,
        label=field.label,
        control_type=field.control_type.lower(),
        attributes=dict(field.attributes),
    )

    field_id = field.attributes.pop("id", None) or _generate_field_id(field.name, id_counts)

    if field.control_type in CHOICE_FIELD_TYPES:
        return _render_choice_field(field, field_id)
    if field.control_type == "select":
        return _render_select_field(field, field_id)
    if field.control_type == "textarea":
        return _render_textarea_field(field, field_id)
    if field.control_type == "file":
        return _render_file_field(field, field_id)
    if field.control_type in TEXT_INPUT_TYPES:
        return _render_text_input_field(field, field_id)
    if field.control_type in {"submit", "reset"}:
        return _render_action_field(field)

    return ""


def _render_form_block(block: FormBlock) -> str:
    id_counts: Dict[str, int] = {}

    form_attributes = dict(block.attributes)
    method = (form_attributes.pop("method", "get") or "get").lower()
    action = form_attributes.pop("action", "")
    form_id = form_attributes.pop("id", None)
    form_class = _combine_classes(["formdown-form"], form_attributes.pop("class", None))

    has_file_input = any(
        isinstance(element, FormField) and element.control_type.lower() == "file"
        for element in block.elements
    )

    if has_file_input and "enctype" not in form_attributes:
        form_attributes["enctype"] = "multipart/form-data"

    attr_pairs = {
        "action": action,
        "method": method or "get",
        "class": form_class,
    }
    if form_id:
        attr_pairs["id"] = form_id

    attr_pairs.update(form_attributes)

    rendered_attrs = "".join(_render_attribute(key, attr_pairs[key]) for key in sorted(attr_pairs))

    parts = [f"<form{rendered_attrs}>"]
    for element in block.elements:
        if isinstance(element, FormField):
            parts.append(_render_form_field(element, id_counts))
        elif isinstance(element, Heading):
            parts.append(_render_heading(element, inside_form=True))
        elif isinstance(element, Paragraph):
            parts.append(_render_paragraph(element, inside_form=True))
        elif isinstance(element, HorizontalRule):
            parts.append(_render_horizontal_rule(element))
    parts.append("</form>")
    return "\n".join(parts)


def render_formdown_html(source: str) -> str:
    """Render a formdown fenced block into HTML."""

    nodes = parse_formdown_document(source)
    parts: List[str] = ['<div class="formdown-document">']
    for node in nodes:
        if isinstance(node, FormBlock):
            parts.append(_render_form_block(node))
        elif isinstance(node, Heading):
            parts.append(_render_heading(node))
        elif isinstance(node, Paragraph):
            parts.append(_render_paragraph(node))
        elif isinstance(node, HorizontalRule):
            parts.append(_render_horizontal_rule(node))
    parts.append("</div>")
    return "\n".join(parts)

