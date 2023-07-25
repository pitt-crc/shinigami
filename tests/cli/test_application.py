"""Tests for the ``Application`` class."""

import logging
from unittest import TestCase

from shinigami.cli import Application


class ConsoleLoggingConfiguration(TestCase):
    """Test the application verbosity is set to match commandline arguments"""

    def test_root_logs_to_console(self) -> None:
        """Test the root logger logs to the console"""

        Application.execute(['--debug'])
        handler_names = [handler.name for handler in logging.getLogger().handlers]
        self.assertIn('console_handler', handler_names)

    def test_console_logger_has_stream_handler(self) -> None:
        """Test the ``console`` logger has a single ``StreamHandler``"""

        Application.execute(['--debug'])
        handlers = logging.getLogger('console_logger').handlers

        self.assertEqual(1, len(handlers))
        self.assertIsInstance(handlers[0], logging.StreamHandler)

    def test_verbose_level_zero(self):
        """Test the application defaults to logging errors and above in the console"""

        Application.execute(['--debug'])
        for handler in logging.getLogger('console_logger').handlers:
            self.assertEqual(logging.ERROR, handler.level)

    def test_verbose_level_one(self):
        """Test a single verbose flag sets the logging level to ``WARNING``"""

        Application.execute(['-v', '--debug'])
        for handler in logging.getLogger('console_logger').handlers:
            self.assertEqual(logging.WARNING, handler.level)

    def test_verbose_level_two(self):
        """Test two verbose flags sets the logging level to ``INFO``"""

        Application.execute(['-vv', '--debug'])
        for handler in logging.getLogger('console_logger').handlers:
            self.assertEqual(logging.INFO, handler.level)

    def test_verbose_level_three(self):
        """Test three verbose flags sets the logging level to ``DEBUG``"""

        Application.execute(['-vvv', '--debug'])
        for handler in logging.getLogger('console_logger').handlers:
            self.assertEqual(logging.DEBUG, handler.level)

    def test_verbose_level_many(self):
        """Test several verbose flags sets the logging level to ``DEBUG``"""

        Application.execute(['-vvvvvvvvvv', '--debug'])
        for handler in logging.getLogger('console_logger').handlers:
            self.assertEqual(logging.DEBUG, handler.level)


class FileLoggingConfiguration(TestCase):
    """Test the configuration for logging to file"""

    def test_root_logs_to_file(self) -> None:
        """Test the root logger logs to the log file"""

        Application.execute(['--debug'])
        handler_names = [handler.name for handler in logging.getLogger().handlers]
        self.assertIn('log_file_handler', handler_names)

    def test_file_logger_has_file_handler(self) -> None:
        """Test the ``file_logger`` logger has a single ``StreamHandler``"""

        Application.execute(['--debug'])
        handlers = logging.getLogger('file_logger').handlers

        self.assertEqual(1, len(handlers))
        self.assertIsInstance(handlers[0], logging.FileHandler)
