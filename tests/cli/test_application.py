"""Tests for the `cli.Application` class"""

from unittest import TestCase
from unittest.mock import patch

from shinigami.cli import Application


class MethodRouting(TestCase):
    """Test CLI commands are routed to the correct callable objects"""

    def test_scan_method(self) -> None:
        """Test the `scan` command routes to the `scan` method"""

        with patch.object(Application, 'scan', autospec=True) as scan:
            Application().execute(['scan', '-c', 'cluster1'])
            scan.assert_called_once()

    def test_terminate_method(self) -> None:
        """Test the `terminate` command routes to the `terminate` method"""

        with patch.object(Application, 'terminate', autospec=True) as scan:
            Application().execute(['terminate', '-n', 'node1'])
            scan.assert_called_once()
