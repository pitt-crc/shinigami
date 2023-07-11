"""Tests for the ``check_ignore_node`` function."""

from unittest import TestCase

from shinigami import check_ignore_node


class RegexMatching(TestCase):
    """Test regex pattern matching by the ``check_ignore_node`` function"""

    def test_matches_pattern(self) -> None:
        """Test the return is ``True`` when the input matches the patterns"""

        self.assertTrue(check_ignore_node('ppc-n', (r'.*ppc-n.*',)))
        self.assertTrue(check_ignore_node('mems-n', (r'.*ppc-n.*', r'.*mems-n.*')))

    def test_no_matching_pattern(self) -> None:
        """Test the return is ``False`` when the input doesn't match the patterns"""

        self.assertFalse(check_ignore_node('foo', ('bar',)))
        self.assertFalse(check_ignore_node('foo', ('bar', 'biz')))

    def test_empty_check_string(self) -> None:
        """Test the return is ``False`` when the ``node_name`` argument is empty"""

        self.assertTrue(check_ignore_node('', ('bar',)))
        self.assertTrue(check_ignore_node('', tuple()))
        self.assertTrue(check_ignore_node('', None))

    def test_empty_ignore_patterns(self) -> None:
        """Test the return is ``True`` when the ``patterns`` argument is empty"""

        self.assertTrue(check_ignore_node('foo', tuple()))

    def test_ignore_patterns_none(self) -> None:
        """Test the return is ``True`` when the ``patterns`` argument is None"""

        self.assertTrue(check_ignore_node('foo', None))
