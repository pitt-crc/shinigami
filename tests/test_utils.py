"""Tests for the `utils` module."""

from unittest import TestCase

from shinigami import utils
from shinigami.utils import id_in_whitelist

# For information on resources defined in the testing environment,
# see https://github.com/pitt-crc/Slurm-Test-Environment/
TEST_CLUSTER = 'development'
TEST_NODES = set(f'c{i}' for i in range(1, 11))


class Whitelisting(TestCase):
    """Tests for the ``id_in_whitelist`` function"""

    def test_empty_whitelist(self) -> None:
        """Test the return value is ``False`` for all ID values when the whitelist is empty"""

        self.assertFalse(id_in_whitelist(0, []))
        self.assertFalse(id_in_whitelist(123, []))

    def test_whitelisted_by_id(self) -> None:
        """Test return values for a whitelist of explicit ID values"""

        whitelist = (123, 456, 789)
        self.assertTrue(id_in_whitelist(456, whitelist))
        self.assertFalse(id_in_whitelist(0, whitelist))

    def test_whitelisted_by_id_range(self) -> None:
        """Test return values for a whitelist of ID ranges"""

        whitelist = (0, 1, 2, (100, 300))
        self.assertTrue(id_in_whitelist(123, whitelist))
        self.assertFalse(id_in_whitelist(301, whitelist))


class GetNodes(TestCase):
    """Tests for the ``get_nodes`` function"""

    def test_nodes_match_test_env(self) -> None:
        """Test the returned node list matches values defined in the testing environment"""

        self.assertCountEqual(TEST_NODES, utils.get_nodes(TEST_CLUSTER))

    def test_ignore_substring(self) -> None:
        """Test nodes with the included substring are ignored"""

        exclude_node = 'c1'

        # Create a copy of the test nodes with on element missing
        expected_nodes = TEST_NODES.copy()
        expected_nodes.remove(exclude_node)

        returned_nodes = utils.get_nodes(TEST_CLUSTER, [exclude_node])
        self.assertCountEqual(expected_nodes, returned_nodes)

    def test_missing_cluster(self) -> None:
        """Test an error is raised for a cluster name that does not exist"""

        with self.assertRaisesRegex(RuntimeError, 'No cluster \'fake_cluster\''):
            utils.get_nodes('fake_cluster')

    def test_missing_node(self) -> None:
        """Test no error is raised when an excuded node des not exist"""

        excluded_nodes = {'c1', 'fake_node'}
        expected_nodes = TEST_NODES - excluded_nodes

        returned_nodes = utils.get_nodes(TEST_CLUSTER, excluded_nodes)
        self.assertCountEqual(expected_nodes, returned_nodes)
