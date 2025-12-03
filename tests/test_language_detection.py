from dataclasses import dataclass
from pathlib import Path

import pytest

from server_execution.language_detection import detect_server_language


@dataclass
class LanguageCase:
    name: str
    definition: str | None
    expected: str


LANGUAGE_CASES = [
    LanguageCase(
        name="empty_defaults_to_python",
        definition=None,
        expected="python",
    ),
    LanguageCase(
        name="python_shebang",
        definition="#!/usr/bin/env python3\nprint('hi')",
        expected="python",
    ),
    LanguageCase(
        name="bash_shebang",
        definition="#!/usr/bin/env bash\necho hi",
        expected="bash",
    ),
    LanguageCase(
        name="typescript_export",
        definition="export async function main() {}",
        expected="typescript",
    ),
    LanguageCase(
        name="clojure_namespace",
        definition="(ns example.core)\n(defn main [] (println \"hi\"))",
        expected="clojure",
    ),
    LanguageCase(
        name="common_shell_tokens_majority",
        definition="ls | grep foo\nawk '{print $1}'\nsort",
        expected="bash",
    ),
    LanguageCase(
        name="plain_text_falls_back_to_python",
        definition="This is plain text with nothing special.",
        expected="python",
    ),
    LanguageCase(
        name="not_enough_shell_tokens_for_bash",
        definition="Mention awk once but otherwise prose only.",
        expected="python",
    ),
]


@pytest.mark.parametrize("case", LANGUAGE_CASES, ids=lambda case: case.name)
def test_detect_server_language(case: LanguageCase):
    assert detect_server_language(case.definition) == case.expected


def test_server_form_links_to_language_detection_source():
    template = Path("templates/server_form.html").read_text(encoding="utf-8")
    assert "/source/server_execution/language_detection.py" in template
    assert "Detected automatically" in template
