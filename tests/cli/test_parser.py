"""Tests for the ``cli.Parser`` class"""

from unittest import TestCase

from shinigami.cli import Parser


class DebugOption(TestCase):
    """Test the behavior of the ``debug`` option"""

    def test_default_is_false(self) -> None:
        """Test the ``debug`` argument defaults to ``False``"""

        args = Parser().parse_args([])
        self.assertFalse(args.debug)

    def test_enabled_is_true(self) -> None:
        """Test the ``debug`` flag stores a ``True`` value"""

        args = Parser().parse_args(['--debug'])
        self.assertTrue(args.debug)
