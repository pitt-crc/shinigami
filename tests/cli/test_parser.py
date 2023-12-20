"""Tests for the `cli.Parser` class"""

from unittest import TestCase

from shinigami.cli import Parser


class ErrorHandling(TestCase):
    """Test custom parsing logic encapsulated by the `BaseParser`  class"""

    def test_errors_raise_system_exit(self) -> None:
        """Test error messages are raised as `SystemExit` instances"""

        with self.assertRaises(SystemExit):
            Parser().error("This is an error message")


class ScanSubParser(TestCase):
    """Test the behavior of the `scan` subparser"""

    def test_debug_arg(self) -> None:
        """Test parsing of the `debug` argument"""

        parser = Parser()
        scan_command = ['scan', '-c', 'development', '-u' '100']
        self.assertFalse(parser.parse_args(scan_command).debug)

        scan_command_debug = ['scan', '-c', 'development', '-u' '100', '--debug']
        self.assertTrue(parser.parse_args(scan_command_debug).debug)

    def test_verbose_arg(self) -> None:
        """Test the verbosity argument counts the number of provided flags"""

        parser = Parser()
        base_command = ['scan', '-c', 'development', '-u' '100']
        self.assertEqual(0, parser.parse_args(base_command).verbosity)
        self.assertEqual(1, parser.parse_args(base_command + ['-v']).verbosity)
        self.assertEqual(2, parser.parse_args(base_command + ['-vv']).verbosity)
        self.assertEqual(3, parser.parse_args(base_command + ['-vvv']).verbosity)
        self.assertEqual(5, parser.parse_args(base_command + ['-vvvvv']).verbosity)

    def test_clusters_arg(self) -> None:
        """Test parsing of the `clusters` argument"""

        parser = Parser()

        single_cluster_out = ['development']
        single_cluster_cmd = ['scan', '-c', *single_cluster_out, '-u', '100']
        self.assertSequenceEqual(single_cluster_out, parser.parse_args(single_cluster_cmd).clusters)

        multi_cluster_out = ['dev1', 'dev2', 'dev3']
        multi_cluster_cmd = ['scan', '-c', *multi_cluster_out, '-u', '100']
        self.assertSequenceEqual(multi_cluster_out, parser.parse_args(multi_cluster_cmd).clusters)

    def test_ignore_nodes_arg(self) -> None:
        """Test parsing of the `ignore-nodes` argument"""

        parser = Parser()
        base_command = ['scan', '-c', 'development', '-u' '100']

        single_node_out = ['node1']
        single_node_cmd = base_command + ['-i', 'node1']
        self.assertSequenceEqual(single_node_out, parser.parse_args(single_node_cmd).ignore_nodes)

        multi_node_out = ['node1', 'node2']
        multi_node_cmd = base_command + ['-i', 'node1', 'node2']
        self.assertSequenceEqual(multi_node_out, parser.parse_args(multi_node_cmd).ignore_nodes)

    def test_uid_whitelist_arg(self) -> None:
        """Test parsing of the `uid-whitelist` argument"""

        parser = Parser()

        # Test for a single integer
        single_int_command = 'scan -c development -u 100'.split()
        single_int_out = [100]
        self.assertSequenceEqual(single_int_out, parser.parse_args(single_int_command).uid_whitelist)

        # Test for a multiple integers
        multi_int_command = 'scan -c development -u 100 200'.split()
        multi_int_out = [100, 200]
        self.assertSequenceEqual(multi_int_out, parser.parse_args(multi_int_command).uid_whitelist)

        # Test for a list type
        single_list_command = 'scan -c development -u [100,200]'.split()
        single_list_out = [[100, 200]]
        self.assertSequenceEqual(single_list_out, parser.parse_args(single_list_command).uid_whitelist)

        # Test for a mix of types
        mixed_command = 'scan -c development -u 100 [200,300] 400 [500,600]'.split()
        mixed_out = [100, [200, 300], 400, [500, 600]]
        self.assertSequenceEqual(mixed_out, parser.parse_args(mixed_command).uid_whitelist)


class TerminateSubParser(TestCase):
    """Test the behavior of the `terminate` subparser"""

    def test_debug_arg(self) -> None:
        """Test the `debug` argument"""

        parser = Parser()
        terminate_command = ['terminate', '-n', 'node1', '-u', '100']
        self.assertFalse(parser.parse_args(terminate_command).debug)

        terminate_command_debug = ['terminate', '-n', 'node1', '-u', '100', '--debug']
        self.assertTrue(parser.parse_args(terminate_command_debug).debug)

    def test_verbose_arg(self) -> None:
        """Test the verbosity argument counts the number of provided flags"""

        parser = Parser()
        base_command = ['terminate', '-n', 'node', '-u' '100']
        self.assertEqual(0, parser.parse_args(base_command).verbosity)
        self.assertEqual(1, parser.parse_args(base_command + ['-v']).verbosity)
        self.assertEqual(2, parser.parse_args(base_command + ['-vv']).verbosity)
        self.assertEqual(3, parser.parse_args(base_command + ['-vvv']).verbosity)
        self.assertEqual(5, parser.parse_args(base_command + ['-vvvvv']).verbosity)

    def test_nodes_arg(self) -> None:
        """Test parsing of the `nodes` argument"""

        parser = Parser()

        single_node_out = ['development']
        single_node_cmd = ['terminate', '-n', *single_node_out, '-u', '100']
        self.assertSequenceEqual(single_node_out, parser.parse_args(single_node_cmd).nodes)

        multi_node_out = ['dev1', 'dev2', 'dev3']
        multi_node_cmd = ['terminate', '-n', *multi_node_out, '-u', '100']
        self.assertSequenceEqual(multi_node_out, parser.parse_args(multi_node_cmd).nodes)

    def test_uid_whitelist_arg(self) -> None:
        """Test parsing of the `uid-whitelist` argument"""

        parser = Parser()

        # Test for a single integer
        single_int_command = 'terminate -n node -u 100'.split()
        single_int_out = [100]
        self.assertSequenceEqual(single_int_out, parser.parse_args(single_int_command).uid_whitelist)

        # Test for a multiple integers
        multi_int_command = 'terminate -n node -u 100 200'.split()
        multi_int_out = [100, 200]
        self.assertSequenceEqual(multi_int_out, parser.parse_args(multi_int_command).uid_whitelist)

        # Test for a list type
        single_list_command = 'terminate -n node -u [100,200]'.split()
        single_list_out = [[100, 200]]
        self.assertSequenceEqual(single_list_out, parser.parse_args(single_list_command).uid_whitelist)

        # Test for a mix of types
        mixed_command = 'terminate -n node -u 100 [200,300] 400 [500,600]'.split()
        mixed_out = [100, [200, 300], 400, [500, 600]]
        self.assertSequenceEqual(mixed_out, parser.parse_args(mixed_command).uid_whitelist)
