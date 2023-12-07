"""Tests for the `cli.BaseParser` class"""

from unittest import TestCase

from shinigami.cli import BaseParser


class BaseParsing(TestCase):
    """Test custom parsing login encapsulated by the `BaseParser`  class"""

    def test_errors_raise_system_exit(self) -> None:
        """Test error messages are raised as `SystemExit` instances"""

        with self.assertRaises(SystemExit):
            BaseParser().error("This is an error message")

    def test_errors_include_message(self) -> None:
        """Test parser messages are included as error messages"""

        msg = "This is an error message"
        with self.assertRaisesRegex(SystemExit, msg):
            BaseParser().error(msg)
