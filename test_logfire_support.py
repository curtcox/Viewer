import logging
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from flask import Flask

from logfire_support import initialize_observability


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
            with patch("logfire_support.importlib.import_module", side_effect=ImportError("missing")):
                status = initialize_observability(self.app)

        self.assertFalse(status["logfire_available"])
        self.assertIn("not installed", status["logfire_reason"])

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


if __name__ == "__main__":
    unittest.main()
