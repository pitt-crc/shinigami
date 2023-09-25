"""The executable application and its command-line interface."""

import asyncio
import inspect
import json
import logging
import logging.config
import logging.handlers
import sys
from argparse import ArgumentParser
from typing import List, Collection, Union

from . import __version__, utils


class BaseParser(ArgumentParser):
    """Custom argument parser that prints help text on error"""

    def error(self, message: str) -> None:
        """Prints a usage message and exit

        Args:
            message: The usage message
        """

        # Print the help text if less than two commands are typed into the commandline
        if len(sys.argv) <= 2:
            self.print_help()
            super().exit(1)

        else:
            super().error(message)


class Parser(BaseParser):
    """Defines the command-line interface and parses command-line arguments"""

    DEFAULT_CONCURRENT = 1
    DEFAULT_TIMEOUT = 120

    def __init__(self) -> None:
        """Define the command-line interface"""

        # Configure the top level parser
        super().__init__(prog='shinigami', description='Scan Slurm compute nodes and terminate orphan processes.')
        subparsers = self.add_subparsers(required=True, parser_class=BaseParser)
        self.add_argument('--version', action='version', version=__version__)

        # This parser defines reusable arguments and is not exposed to the user
        common = ArgumentParser(add_help=False)
        common_group = common.add_argument_group('debugging options')
        common_group.add_argument('--debug', action='store_true', help='force the application to run in debug mode')
        common_group.add_argument(
            '-v', action='count', dest='verbosity', default=0,
            help='set verbosity to warning (-v), info (-vv), or debug (-vvv)')

        # Subparser for the `Application.scan` method
        scan = subparsers.add_parser('scan', parents=[common], help='terminate processes on one or more clusters')
        scan.set_defaults(callable=Application.scan)
        scan.add_argument('-c', '--clusters', nargs='+', required=True, help='cluster names to scan')
        scan.add_argument('-i', '--ignore-nodes', nargs='*', help='ignore given nodes')
        scan.add_argument('-u', '--uid-whitelist', nargs='+', type=json.loads, required=True, help='whitelisted user IDs')
        scan.add_argument('-m', '--max-concurrent', type=int, default=self.DEFAULT_CONCURRENT, help='maximum SSH connections')
        scan.add_argument('-t', '--ssh-timeout', type=int, default=self.DEFAULT_TIMEOUT, help='SSH Timeout')

        # Subparser for the `Application.terminate` method
        terminate = subparsers.add_parser('terminate', parents=[common], help='terminate processes on a single node')
        terminate.set_defaults(callable=Application.terminate)
        terminate.add_argument('-n', '--nodes', nargs='+', required=True, help='the DNS name of the node to terminate')
        terminate.add_argument('-u', '--uid-whitelist', nargs='+', type=json.loads, required=True, help='whitelisted user IDs')
        terminate.add_argument('-m', '--max-concurrent', type=int, default=self.DEFAULT_CONCURRENT, help='maximum SSH connections')
        terminate.add_argument('-t', '--ssh-timeout', type=int, default=self.DEFAULT_TIMEOUT, help='SSH Timeout')


class Application:
    """Entry point for instantiating and executing the application"""

    @staticmethod
    def _configure_logging(verbosity: int) -> None:
        """Configure Python logging

        Configured loggers include the following:
          - console_logger: For logging to the console only
          - file_logger: For logging to the log file only
          - root: For logging to the console and log file

        Args:
            verbosity: The console verbosity defined as the count passed to the commandline
        """

        verbosity_to_log_level = {0: logging.ERROR, 1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}
        console_log_level = verbosity_to_log_level.get(verbosity, logging.DEBUG)

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
        ssh_timeout: asyncio.Semaphore,
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
        ssh_timeout: asyncio.Semaphore,
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

        # Launch a concurrent job for each node in the cluster
        coroutines = [
            utils.terminate_errant_processes(
                node=node,
                uid_whitelist=uid_whitelist,
                ssh_limit=asyncio.Semaphore(max_concurrent),
                timeout=ssh_timeout,
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
        """Parse command-line arguments and execute the application

        Args:
            arg_list: Optionally parse the given arguments instead of the command line
        """

        args = Parser().parse_args(arg_list)
        cls._configure_logging(args.verbosity)

        try:
            # Extract the subset of arguments that are valid for the function ``args.callable``
            valid_params = inspect.signature(args.callable).parameters
            valid_arguments = {key: value for key, value in vars(args).items() if key in valid_params}
            asyncio.run(args.callable(**valid_arguments))

        except KeyboardInterrupt:
            pass

        except Exception as caught:
            logging.getLogger('file_logger').critical('Application crash', exc_info=caught)
            logging.getLogger('console_logger').critical(str(caught))
