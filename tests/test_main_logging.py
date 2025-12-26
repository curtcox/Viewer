import logging
import os

import main


class TestConfigureLogging:
    def test_configure_logging_sets_debug(self, monkeypatch):
        monkeypatch.delenv("VIEWER_LOG_LEVEL", raising=False)
        root_logger = logging.getLogger()
        original_level = root_logger.level

        try:
            level = main.configure_logging(True)
            assert level == logging.DEBUG
            assert os.environ["VIEWER_LOG_LEVEL"] == "DEBUG"
            assert root_logger.level == logging.DEBUG
        finally:
            logging.basicConfig(level=original_level, force=True)
            root_logger.setLevel(original_level)

    def test_configure_logging_defaults_to_info(self, monkeypatch):
        monkeypatch.setenv("VIEWER_LOG_LEVEL", "DEBUG")
        root_logger = logging.getLogger()
        original_level = root_logger.level

        try:
            level = main.configure_logging(False)
            assert level == logging.INFO
            assert os.environ["VIEWER_LOG_LEVEL"] == "INFO"
            assert root_logger.level == logging.INFO
        finally:
            logging.basicConfig(level=original_level, force=True)
            root_logger.setLevel(original_level)
