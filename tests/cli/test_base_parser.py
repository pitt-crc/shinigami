"""Tests for the ``cli.BaseParser`` class"""

from unittest import TestCase

from shinigami.cli import BaseParser


class ErrorHandling(TestCase):
    """Test parser errors are properly raised and reported"""

    def test_system_exit_error(self) -> None:
        """Test parser errors are raised as ``SystemExit`` exceptions"""

        message = 'This is an error message'
        with self.assertRaises(SystemExit) as error:
            BaseParser().error(message)
            self.assertEqual(message, error)
