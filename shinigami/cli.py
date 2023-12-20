"""The executable application and its command line interface."""

import asyncio
import inspect
import logging
import logging.config
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
from json import loads
from typing import List, Collection, Union

from asyncssh import SSHClientConnectionOptions

from . import __version__, utils


class Parser(ArgumentParser):
    """Defines the command-line interface and parses command-line arguments"""

    def __init__(self) -> None:
        """Define the command-line interface"""

        # Configure the top level parser
        super().__init__(prog='shinigami', description='Scan Slurm compute nodes and terminate orphan processes.')
        subparsers = self.add_subparsers(required=True, parser_class=ArgumentParser)
        self.add_argument('--version', action='version', version=__version__)

        # The `common` parser holds reusable argument definitions
        common = ArgumentParser(add_help=False)
        ssh_group = common.add_argument_group('ssh options')
        ssh_group.add_argument('-m', dest='max_concurrent', type=int, default=1, help='maximum concurrent SSH connections (Default: 1)')
        ssh_group.add_argument('-t', dest='ssh_timeout', type=int, default=120, help='SSH connection timeout in seconds (Default: 120)')

        debug_group = common.add_argument_group('debugging options')
        debug_group.add_argument('--debug', action='store_true', help='run the application in debug mode')
        debug_group.add_argument('-v', action='count', dest='verbosity', default=0, help='set verbosity to warning (-v), info (-vv), or debug (-vvv)')

        # Subparser for the `Application.scan` method
        scan = subparsers.add_parser(
            'scan', parents=[common], formatter_class=RawTextHelpFormatter,
            help='terminate processes on one or more clusters',
            description=(
                "The `scan` function automatically terminates orphaned processes on all compute nodes in a Slurm cluster.\n"
                "It is provided as a shorthand alternative to calling the `terminate` command with manually defined node names.\n\n"
                "Slurm nodes are identified using the slurm installation on the current machine.\n"
                "User IDs can be specified individually (e.g. `-u 1000 1001 1002 1003`) or as ranges (e.g. `-u 1000 [1001,1003]`)."))

        scan.set_defaults(callable=Application.scan)
        scan_group = scan.add_argument_group('scanning options')
        scan_group.add_argument('-c', dest='clusters', metavar='CLUS', nargs='+', required=True, help='Slurm cluster name(s) to scan')
        scan_group.add_argument('-i', dest='ignore_nodes', metavar='NODE', nargs='*', default=[], help='ignore the given node(s)')
        scan_group.add_argument('-u', dest='uid_whitelist', metavar='UID', nargs='+', type=loads, default=[0], help='only terminate processes owned by the given user IDs')

        # Subparser for the `Application.terminate` method
        terminate = subparsers.add_parser(
            'terminate', parents=[common], formatter_class=RawTextHelpFormatter,
            help='terminate processes on one or more compute nodes',
            description=(
                "Automatically terminate orphaned processes on one or more Slurm compute nodes.\n\n"
                "Processes are only terminated under the following conditions:\n"
                f"    1. The process belongs to a process tree parented by init (PID {utils.INIT_PROCESS_ID})\n"
                "    2. The associated user ID is in the given UID whitelist\n"
                "    3. The user is not running any Slurm jobs on the parent machine\n\n"
                "User IDs can be specified individually (e.g. `-u 1000 1001 1002 1003`) or as ranges (e.g. `-u 1000 [1001,1003]`)."))

        terminate.set_defaults(callable=Application.terminate)
        terminate_group = terminate.add_argument_group('termination options')
        terminate_group.add_argument('-n', dest='nodes', metavar='NODE', nargs='+', required=True, help='the DNS name(s) of the node(s) to terminate')
        terminate_group.add_argument('-u', dest='uid_whitelist', metavar='UID', nargs='+', type=loads, default=[0], help='only terminate processes owned by the given user IDs')

    def error(self, message: str) -> None:
        """Print a usage message and exits the application

        Args:
            message: The usage message
        """

        if len(sys.argv) == 1:
            self.print_help()
            raise SystemExit

        super().error(message)


class Application:
    """Entry point for instantiating and executing the application"""

    @staticmethod
    def _configure_logging(verbosity: int) -> None:
        """Configure Python logging

        Configured loggers include the following:
          - console_logger: For logging to the console only
          - file_logger: For logging to the log file only
          - root: For logging to the console and log file

        Console verbosity levels are defined as following:
          - 0: ERROR
          - 1: WARNING
          - 2: INFO
          - 3: DEBUG
          - Any other value: DEBUG

        Args:
            verbosity: The console verbosity level
        """

        console_log_level = {
            0: logging.ERROR,
            1: logging.WARNING,
            2: logging.INFO,
            3: logging.DEBUG
        }.get(verbosity, logging.DEBUG)

        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': True,
            'formatters': {
                'console_formatter': {
                    'format': '%(levelname)8s: %(message)s'
                },
                'log_file_formatter': {
                    'format': '%(asctime)s | %(levelname)8s | %(message)s'
                },
            },
            'handlers': {
                'console_handler': {
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout',
                    'formatter': 'console_formatter',
                    'level': console_log_level
                },
                'log_file_handler': {
                    'class': 'logging.handlers.SysLogHandler',
                    'formatter': 'log_file_formatter',
                    'level': 'DEBUG',
                },
            },
            'loggers': {
                'console_logger': {'handlers': ['console_handler'], 'level': 0, 'propagate': False},
                'file_logger': {'handlers': ['log_file_handler'], 'level': 0, 'propagate': False},
                '': {'handlers': ['console_handler', 'log_file_handler'], 'level': 0, 'propagate': False},
            }
        })

    @staticmethod
    async def scan(
        clusters: Collection[str],
        ignore_nodes: Collection[str],
        uid_whitelist: Collection[Union[int, List[int]]],
        max_concurrent: int,
        ssh_timeout: int,
        debug: bool
    ) -> None:
        """Terminate orphaned processes on all clusters/nodes configured in application settings.

        Args:
            clusters: Slurm cluster names
            ignore_nodes: List of nodes to ignore
            uid_whitelist: UID values to terminate orphaned processes for
            max_concurrent: Maximum number of concurrent ssh connections
            ssh_timeout: Timeout for SSH connections
            debug: Optionally log but do not terminate processes
        """

        # Clusters are handled synchronously, nodes are handled asynchronously
        for cluster in clusters:
            logging.info(f'Starting scan for nodes in cluster {cluster}')
            nodes = utils.get_nodes(cluster, ignore_nodes)
            await Application.terminate(nodes, uid_whitelist, max_concurrent, ssh_timeout, debug)

    @staticmethod
    async def terminate(
        nodes: Collection[str],
        uid_whitelist: Collection[Union[int, List[int]]],
        max_concurrent: int,
        ssh_timeout: int,
        debug: bool
    ) -> None:
        """Terminate processes on a given node

        Args:
            nodes:
            uid_whitelist: UID values to terminate orphaned processes for
            max_concurrent: Maximum number of concurrent ssh connections
            ssh_timeout: Timeout for SSH connections
            debug: Optionally log but do not terminate processes
        """

        ssh_options = SSHClientConnectionOptions(connect_timeout=ssh_timeout)

        # Launch a concurrent job for each node in the cluster
        coroutines = [
            utils.terminate_errant_processes(
                node=node,
                uid_whitelist=uid_whitelist,
                ssh_limit=asyncio.Semaphore(max_concurrent),
                ssh_options=ssh_options,
                debug=debug)
            for node in nodes
        ]

        # Gather results from each concurrent run and check for errors
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        for node, result in zip(nodes, results):
            if isinstance(result, Exception):
                logging.error(f'Error with node {node}: {result}')

    @classmethod
    def execute(cls, arg_list: List[str] = None) -> None:
        """Parse command line arguments and execute the application

        Args:
            arg_list: Optionally parse the given arguments instead of the command line
        """

        args = Parser().parse_args(arg_list)
        cls._configure_logging(args.verbosity)

        try:
            # Extract the subset of arguments that are valid for the `args.callable` function
            valid_params = inspect.signature(args.callable).parameters
            valid_arguments = {key: value for key, value in vars(args).items() if key in valid_params}
            asyncio.run(args.callable(**valid_arguments))

        except KeyboardInterrupt:  # pragma: nocover
            pass

        except Exception as caught:  # pragma: nocover
            logging.getLogger('file_logger').critical('Application crash', exc_info=caught)
            logging.getLogger('console_logger').critical(str(caught))
