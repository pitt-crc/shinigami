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
