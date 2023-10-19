"""Tests for the ``defaults.Defaults`` class"""

from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase

from shinigami.defaults import Defaults


class DefaultValues(TestCase):
    """Test default class values"""

    def test_ignore_nodes_empty(self) -> None:
        """Test the ``ignore_nodes`` setting is empty"""

        self.assertEqual(tuple(), Defaults().ignore_nodes)

    def test_uid_whitelist_empty(self) -> None:
        """Test the ``uid_whitelist`` setting is empty"""

        self.assertEqual(tuple(), Defaults().uid_whitelist)


class Load(TestCase):
    """Test loading values from disk via the ``load`` function"""

    def test_file_does_not_exist(self) -> None:
        """Test class values are used when the file does not exist"""

        self.assertEqual(Defaults(), Defaults.load())

    def test_file_exists(self) -> None:
        """Test values are successfully parsed from disk"""

        with NamedTemporaryFile() as temp_file:
            file_path = Path(temp_file.name)
            file_path.write_text('{ "clusters": ["cluster1", "cluster2"] }')
            parsed_vals = Defaults.load(file_path)

        self.assertSequenceEqual(["cluster1", "cluster2"], parsed_vals.clusters)
