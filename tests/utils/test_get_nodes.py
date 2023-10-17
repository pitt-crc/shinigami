"""Tests for the ``utils.get_nodes`` function"""

from unittest import TestCase

from shinigami import utils

# For information on resources defined in the testing environment,
# see https://github.com/pitt-crc/Slurm-Test-Environment/
TEST_CLUSTER = 'development'
TEST_NODES = set(f'c{i}' for i in range(1, 11))


class NodesMatchTestEnvironment(TestCase):
    """Test the returned node list matches values defined in the testing environment"""

    def test_returned_nodes(self) -> None:
        """Test returned nodes match hose defined in the slurm test env"""

        self.assertSequenceEqual(TEST_NODES, utils.get_nodes(TEST_CLUSTER, []))
