"""Tests for the `utils.get_nodes` module."""

import subprocess
from unittest import TestCase, skipIf

from shinigami import utils

# For information on resources defined in the testing environment
# see https://github.com/pitt-crc/Slurm-Test-Environment/
TEST_CLUSTER = 'development'
TEST_NODES = set(f'c{i}' for i in range(1, 11))


def slurm_is_installed() -> bool:
    """Return whether `sbatch` is installed and accessible on the parent machine"""

    try:
        subprocess.run(['sbatch', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True

    # Catch all errors, but list the expected error(s) explicitly
    except (FileNotFoundError, Exception):
        return False


@skipIf(not slurm_is_installed(), 'These tests require slurm to be installed.')
class GetNodes(TestCase):
    """Tests for the `get_nodes` function"""

    def test_nodes_match_test_env(self) -> None:
        """Test the returned node list matches values defined in the testing environment"""

        self.assertEqual(TEST_NODES, utils.get_nodes(TEST_CLUSTER))

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
        """Test no error is raised when an excluded node does not exist"""

        excluded_nodes = {'c1', 'fake_node'}
        expected_nodes = TEST_NODES - excluded_nodes

        returned_nodes = utils.get_nodes(TEST_CLUSTER, excluded_nodes)
        self.assertCountEqual(expected_nodes, returned_nodes)
