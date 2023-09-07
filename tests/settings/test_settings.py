"""Tests for the ``settings.Settings`` class"""
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase

from shinigami.settings import Settings


class Defaults(TestCase):
    """Test default values"""

    def test_defaults_allow_init(self) -> None:
        """Test default values are sufficient for instantiating a new Settings object"""

        Settings()

    def test_debug_is_false(self) -> None:
        """Test the ``debug`` setting defaults to ``False``"""

        self.assertFalse(Settings().debug)

    def test_ignore_nodes_empty(self) -> None:
        """Test the ``ignore_nodes`` setting is empty"""

        self.assertEqual(tuple(), Settings().ignore_nodes)


class Load(TestCase):
    """Test loading settings from disk via the ``load`` function"""

    def test_file_does_not_exist(self) -> None:
        """Test default settings are used when the file does not exist"""

        self.assertEqual(Settings(), Settings.load())

    def test_file_exists(self) -> None:
        """Test settings are successfully parsed from disk"""

        with NamedTemporaryFile() as temp_file:
            file_path = Path(temp_file.name)
            file_path.write_text('{ "debug": true, "clusters": ["cluster1", "cluster2"] }')
            settings = Settings.load(file_path)

        self.assertTrue(settings.debug)
        self.assertSequenceEqual(["cluster1", "cluster2"], settings.clusters)
