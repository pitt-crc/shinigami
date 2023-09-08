from unittest import TestCase

from shinigami import utils

# For information on resources defined in the testing environment,
# see https://github.com/pitt-crc/Slurm-Test-Environment/
TEST_CLUSTER = 'development'
TEST_NODES = ('node1',)


class NodesMatchTestEnvironment(TestCase):
    """Test the returned node list matches values defined in the testing environment"""

    def test_returned_nodes(self) -> None:
        self.assertSequenceEqual(TEST_NODES, utils.get_nodes(TEST_CLUSTER, []))
