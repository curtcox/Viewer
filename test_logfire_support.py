import logging
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from flask import Flask

import logfire_support
from logfire_support import initialize_observability, logfire


class DummyApp(Flask):
    def __init__(self):
        super().__init__(__name__)
        # Quiet the logger during tests
        self.logger = logging.getLogger("logfire-support-test")
        self.logger.handlers = []
        self.logger.propagate = False


class LogfireSupportTests(unittest.TestCase):
    def setUp(self):
        self.app = DummyApp()

    def test_initialize_observability_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            status = initialize_observability(self.app)

        self.assertFalse(status["logfire_available"])
        self.assertIn("LOGFIRE_API_KEY", status["logfire_reason"])
        self.assertFalse(status["langsmith_available"])

    def test_initialize_observability_handles_missing_package(self):
        with patch.dict(os.environ, {"LOGFIRE_API_KEY": "abc"}, clear=True):
            def fake_import(name, *_, **__):
                if name == "logfire":
                    raise ImportError("missing")
                return SimpleNamespace()

            with patch("logfire_support.importlib.import_module", side_effect=fake_import):
                status = initialize_observability(self.app)

        self.assertFalse(status["logfire_available"])
        self.assertIn("not installed", status["logfire_reason"])

    def test_initialize_observability_reports_missing_dependencies(self):
        with patch.dict(os.environ, {"LOGFIRE_API_KEY": "abc"}, clear=True):

            def fake_import(name, *_, **__):
                if name == "opentelemetry.instrumentation.flask":
                    raise ImportError("missing flask instrumentation")
                if name == "logfire":
                    return SimpleNamespace()
                return SimpleNamespace()

            with patch("logfire_support.importlib.import_module", side_effect=fake_import):
                status = initialize_observability(self.app)

        self.assertFalse(status["logfire_available"])
        self.assertIn("opentelemetry.instrumentation.flask", status["logfire_reason"])
        self.assertFalse(status["langsmith_available"])
        self.assertIn("dependencies", status["langsmith_reason"])

    def test_initialize_observability_configures_logfire_and_langsmith(self):
        fake_logfire = SimpleNamespace(
            configure=MagicMock(),
            instrument_flask=MagicMock(),
            instrument_sqlalchemy=MagicMock(),
            instrument_langchain=MagicMock(),
        )

        def fake_import(name, *_, **__):
            if name == "logfire":
                return fake_logfire
            if name.startswith("opentelemetry.instrumentation"):
                return SimpleNamespace()
            raise ImportError(name)

        env = {
            "LOGFIRE_API_KEY": "logfire-key",
            "LOGFIRE_PROJECT_URL": "https://logfire.example/project",
            "LANGSMITH_API_KEY": "langsmith-key",
            "LANGSMITH_PROJECT_URL": "https://langsmith.example/project",
        }

        with patch.dict(os.environ, env, clear=True):
            with patch("logfire_support.importlib.import_module", side_effect=fake_import):
                status = initialize_observability(self.app, engine=object())

        fake_logfire.configure.assert_called()
        fake_logfire.instrument_flask.assert_called()
        fake_logfire.instrument_sqlalchemy.assert_called()
        fake_logfire.instrument_langchain.assert_called()

        self.assertTrue(status["logfire_available"])
        self.assertTrue(status["langsmith_available"])
        self.assertEqual(status["logfire_project_url"], env["LOGFIRE_PROJECT_URL"])
        self.assertEqual(status["langsmith_project_url"], env["LANGSMITH_PROJECT_URL"])

    def test_logfire_instrument_records_arguments_result_and_message(self):
        logfire_support._set_logfire_module(None)
        captured = []
        decorator_kwargs = []

        class FakeInstrument:
            def __call__(self, func=None, **kwargs):
                decorator_kwargs.append(kwargs)
                span = kwargs.get("span_name")
                log_args_flag = kwargs.get("log_args") or kwargs.get("record_args") or False
                log_result_flag = (
                    kwargs.get("log_result")
                    or kwargs.get("log_return")
                    or kwargs.get("record_result")
                    or False
                )
                message_value = (
                    kwargs.get("message")
                    or kwargs.get("message_name")
                    or kwargs.get("event_name")
                )

                def decorator(target):
                    def wrapped(*args, **inner_kwargs):
                        captured.append(
                            {
                                "span_name": span or target.__name__,
                                "log_args": bool(log_args_flag),
                                "log_result": bool(log_result_flag),
                                "args": args,
                                "kwargs": inner_kwargs,
                                "message": message_value,
                            }
                        )
                        result = target(*args, **inner_kwargs)
                        captured[-1]["result"] = result
                        return result

                    return wrapped

                if callable(func):
                    return decorator(func)
                return decorator

        fake_logfire = SimpleNamespace(
            configure=MagicMock(),
            instrument=FakeInstrument(),
            instrument_flask=MagicMock(),
            instrument_sqlalchemy=MagicMock(),
            instrument_langchain=MagicMock(),
        )

        def fake_import(name, *_, **__):
            if name == "logfire":
                return fake_logfire
            if name.startswith("opentelemetry.instrumentation"):
                return SimpleNamespace()
            raise ImportError(name)

        env = {
            "LOGFIRE_API_KEY": "logfire-key",
            "LANGSMITH_API_KEY": "langsmith-key",
        }

        with patch.dict(os.environ, env, clear=True):
            with patch("logfire_support.importlib.import_module", side_effect=fake_import):
                initialize_observability(self.app)

        @logfire.instrument(
            span_name="test.span",
            log_args=True,
            log_result=True,
            message="test.span",
        )
        def sample_function(a, b):
            return a + b

        result = sample_function(2, 3)

        self.assertEqual(result, 5)
        self.assertEqual(len(captured), 1)
        call = captured[0]
        self.assertEqual(call["span_name"], "test.span")
        self.assertTrue(call["log_args"])
        self.assertTrue(call["log_result"])
        self.assertEqual(call["args"], (2, 3))
        self.assertEqual(call["kwargs"], {})
        self.assertEqual(call["result"], 5)
        self.assertEqual(call["message"], "test.span")

        # Ensure the decorator attempted to include message metadata in kwargs.
        self.assertTrue(any("message" in kwargs or "message_name" in kwargs or "event_name" in kwargs for kwargs in decorator_kwargs))

        logfire_support._set_logfire_module(None)


if __name__ == "__main__":
    unittest.main()
