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


class VerboseOption(TestCase):
    """Test the verbosity flag"""

    def test_counts_instances(self) -> None:
        """Test the parser counts the number of provided flags"""

        parser = Parser()
        self.assertEqual(0, parser.parse_args([]).verbosity)
        self.assertEqual(1, parser.parse_args(['-v']).verbosity)
        self.assertEqual(2, parser.parse_args(['-vv']).verbosity)
        self.assertEqual(3, parser.parse_args(['-vvv']).verbosity)
        self.assertEqual(5, parser.parse_args(['-vvvvv']).verbosity)
