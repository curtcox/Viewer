"""Unit tests for bash path parameter support ($1).

These tests verify the new feature that allows bash scripts to receive
path parameters as positional arguments when they use $1, $2, etc.
"""

import unittest
from unittest.mock import patch

import pytest

from flask import Flask

from server_execution.code_execution import (
    _bash_script_uses_positional_params,
    _resolve_bash_path_parameters,
    _run_bash_script,
)


class TestBashScriptUsesPositionalParams(unittest.TestCase):
    """Test _bash_script_uses_positional_params function."""

    def test_detects_single_param(self):
        """Script with $1 should be detected."""
        script = '#!/bin/bash\nawk "$1"'
        assert _bash_script_uses_positional_params(script) is True

    def test_detects_multiple_params(self):
        """Script with $1, $2 should be detected."""
        script = '#!/bin/bash\nsed "$1" "$2"'
        assert _bash_script_uses_positional_params(script) is True

    def test_ignores_scripts_without_params(self):
        """Script without positional params should not be detected."""
        script = '#!/bin/bash\necho "hello"'
        assert _bash_script_uses_positional_params(script) is False

    def test_ignores_dollar_zero(self):
        """$0 (script name) should not trigger detection."""
        script = '#!/bin/bash\necho $0'
        assert _bash_script_uses_positional_params(script) is False

    def test_ignores_dollar_at(self):
        """$@ (all args) should not trigger detection."""
        script = '#!/bin/bash\necho $@'
        assert _bash_script_uses_positional_params(script) is False

    def test_ignores_dollar_star(self):
        """$* (all args) should not trigger detection."""
        script = '#!/bin/bash\necho $*'
        assert _bash_script_uses_positional_params(script) is False

    def test_detects_param_in_quotes(self):
        """$1 inside quotes should be detected."""
        script = '#!/bin/bash\njq "$1"'
        assert _bash_script_uses_positional_params(script) is True

    def test_detects_params_1_through_9(self):
        """$1 through $9 should all be detected."""
        for i in range(1, 10):
            script = f'#!/bin/bash\necho "${i}"'
            assert _bash_script_uses_positional_params(script) is True, f"$${i} should be detected"


class TestResolveBashPathParameters(unittest.TestCase):
    """Test _resolve_bash_path_parameters function."""

    def test_returns_none_for_script_without_params(self):
        """Scripts without $1 should return None for script_arg."""
        app = Flask(__name__)
        with app.test_request_context("/server"):
            script_arg, chained_input_path, remaining = _resolve_bash_path_parameters(
                "server", '#!/bin/bash\necho "hello"'
            )
        assert script_arg is None
        assert chained_input_path is None
        assert remaining == []

    def test_extracts_first_segment_as_script_arg(self):
        """First path segment should be extracted as script arg."""
        from app import create_app
        from database import db
        from db_config import DatabaseConfig, DatabaseMode
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        app = create_app({"TESTING": True})
        with app.app_context():
            db.create_all()
            with app.test_request_context("/awk/pattern"):
                script_arg, chained_input_path, remaining = _resolve_bash_path_parameters(
                    "awk", '#!/bin/bash\nawk "$1"'
                )
            assert script_arg == "pattern"
            assert chained_input_path is None
            assert remaining == []
        DatabaseConfig.reset()

    def test_extracts_remaining_path_for_stdin(self):
        """Remaining path after first segment should be for chained input."""
        from app import create_app
        from database import db
        from db_config import DatabaseConfig, DatabaseMode
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        app = create_app({"TESTING": True})
        with app.app_context():
            db.create_all()
            with app.test_request_context("/sed/s/foo/bar/echo/hello"):
                script_arg, chained_input_path, remaining = _resolve_bash_path_parameters(
                    "sed", '#!/bin/bash\nsed "$1"'
                )
            assert script_arg == "s"
            assert chained_input_path == "/foo/bar/echo/hello"
            assert remaining == ["foo", "bar", "echo", "hello"]
        DatabaseConfig.reset()

    def test_returns_none_with_no_remaining_path(self):
        """No remaining path means no script arg."""
        app = Flask(__name__)
        with app.test_request_context("/awk"):
            script_arg, chained_input_path, remaining = _resolve_bash_path_parameters(
                "awk", '#!/bin/bash\nawk "$1"'
            )
        assert script_arg is None
        assert chained_input_path is None


class TestRunBashScriptWithArgs(unittest.TestCase):
    """Test _run_bash_script with script_args parameter."""

    def test_passes_script_args_to_bash(self):
        """Script args should be passed as positional arguments."""
        app = Flask(__name__)
        with app.test_request_context("/test"):
            with patch("server_execution.code_execution.build_request_args", return_value={}):
                stdout, status, stderr = _run_bash_script(
                    '#!/bin/bash\necho "$1"',
                    "test",
                    chained_input=None,
                    script_args=["hello-world"],
                )

        assert b"hello-world" in stdout
        assert status == 200

    def test_passes_multiple_script_args(self):
        """Multiple script args should be passed."""
        app = Flask(__name__)
        with app.test_request_context("/test"):
            with patch("server_execution.code_execution.build_request_args", return_value={}):
                stdout, status, stderr = _run_bash_script(
                    '#!/bin/bash\necho "$1 $2"',
                    "test",
                    chained_input=None,
                    script_args=["arg1", "arg2"],
                )

        assert b"arg1 arg2" in stdout
        assert status == 200

    def test_script_args_with_stdin(self):
        """Script args should work alongside stdin input."""
        app = Flask(__name__)
        with app.test_request_context("/test"):
            with patch("server_execution.code_execution.build_request_args", return_value={}):
                stdout, status, stderr = _run_bash_script(
                    '#!/bin/bash\necho "Pattern: $1"\necho "Input: $(cat)"',
                    "test",
                    chained_input="input-data",
                    script_args=["my-pattern"],
                )

        assert b"Pattern: my-pattern" in stdout
        assert b"Input: input-data" in stdout
        assert status == 200


@pytest.mark.integration
class TestAwkServer(unittest.TestCase):
    """Test awk server with path parameters.

    Marked as integration test because it requires gawk binary.
    """

    def test_awk_with_pattern(self):
        """Awk should process pattern from $1."""
        app = Flask(__name__)
        script = '#!/bin/bash\nawk "$1"'
        with app.test_request_context("/awk"):
            with patch("server_execution.code_execution.build_request_args", return_value={}):
                stdout, status, stderr = _run_bash_script(
                    script,
                    "awk",
                    chained_input="hello world",
                    script_args=["{print $1}"],
                )

        assert b"hello" in stdout
        assert status == 200


class TestSedServer(unittest.TestCase):
    """Test sed server with path parameters."""

    def test_sed_with_expression(self):
        """Sed should process expression from $1."""
        app = Flask(__name__)
        script = '#!/bin/bash\nsed "$1"'
        with app.test_request_context("/sed"):
            with patch("server_execution.code_execution.build_request_args", return_value={}):
                stdout, status, stderr = _run_bash_script(
                    script,
                    "sed",
                    chained_input="hello world",
                    script_args=["s/world/universe/"],
                )

        assert b"hello universe" in stdout
        assert status == 200


class TestGrepServer(unittest.TestCase):
    """Test grep server with path parameters."""

    def test_grep_with_pattern(self):
        """Grep should match pattern from $1."""
        app = Flask(__name__)
        script = '#!/bin/bash\ngrep -E "$1" || true'
        with app.test_request_context("/grep"):
            with patch("server_execution.code_execution.build_request_args", return_value={}):
                stdout, status, stderr = _run_bash_script(
                    script,
                    "grep",
                    chained_input="hello world\nfoo bar\nhello again",
                    script_args=["hello"],
                )

        output = stdout.decode("utf-8")
        assert "hello world" in output
        assert "hello again" in output
        assert "foo bar" not in output
        assert status == 200


@pytest.mark.integration
class TestJqServer(unittest.TestCase):
    """Test jq server with path parameters.

    Marked as integration test because it requires jq binary.
    """

    def test_jq_with_filter(self):
        """Jq should apply filter from $1."""
        app = Flask(__name__)
        script = '#!/bin/bash\njq "$1"'
        with app.test_request_context("/jq"):
            with patch("server_execution.code_execution.build_request_args", return_value={}):
                stdout, status, stderr = _run_bash_script(
                    script,
                    "jq",
                    chained_input='{"name": "test", "value": 42}',
                    script_args=[".name"],
                )

        assert b'"test"' in stdout
        assert status == 200


if __name__ == "__main__":
    unittest.main()
