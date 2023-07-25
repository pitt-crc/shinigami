"""Tests for the ``settings.Settings`` class"""

from unittest import TestCase

from shinigami.settings import Settings


class Defaults(TestCase):
    """Test default values"""

    def test_defaults_allow_init(self) -> None:
        """Test default values are sufficient for instantiating a new Settings object"""

        Settings()

    def test_debug_is_false(self) -> None:
        """Test the ``debug`` settings defaults to ``False``"""

        self.assertFalse(Settings().debug)

    def test_ignore_nodes_empty(self) -> None:
        """Test the ``ignore_nodes`` setting is empty"""

        self.assertEqual(tuple(), Settings().ignore_nodes)

    def test_uid_ignores_root(self) -> None:
        """Test the UID whitelist includes UID 0"""

        self.assertIn(0, Settings().uid_whitelist)

    def test_gid_ignores_root(self) -> None:
        """Test the GID whitelist includes GID 0"""

        self.assertIn(0, Settings().gid_whitelist)
