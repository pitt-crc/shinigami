"""Tests for the ``check_ignore_node`` function."""

from unittest import TestCase

from shinigami.app import shell_command_to_list


class OutputParsing(TestCase):
    """Test STDOUT/STDERR returns are correctly parsed and returned"""

    def test_stdout_is_returned(self) -> None:
        """Test each line writen to STDOUT is an element of the returned list"""

        out = shell_command_to_list('echo -e "1\n2\n3\n"')
        self.assertSequenceEqual(['1', '2', '3'], out)

    def test_raise_on_stderr(self) -> None:
        """Test output to STDERR results in a raised error"""

        # A valid command that outputs to stderr
        with self.assertRaises(Exception):
            shell_command_to_list('ls fake-dir')

        # An invalid command that can't be run by the shell
        with self.assertRaises(Exception):
            shell_command_to_list('fake-command')
