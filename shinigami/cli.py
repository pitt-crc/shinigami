"""The executable application and its command-line interface."""

import asyncio
import inspect
import logging
import logging.config
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
from json import loads
from pathlib import Path
from typing import List, Collection, Union

from asyncssh import SSHClientConnectionOptions

from . import __version__, utils
from .defaults import Defaults, SETTINGS_PATH


class BaseParser(ArgumentParser):
    """Custom argument parser that prints help text on error"""

    def error(self, message: str) -> None:
        """Prints a usage message and exit

        Args:
            message: The usage message
        """

        if len(sys.argv) == 1:
            self.print_help()

        raise SystemExit(message)


class Parser(BaseParser):
    """Defines the command-line interface and parses command-line arguments"""

    def __init__(self, defaults: Defaults = Defaults()) -> None:
        """Define the command-line interface"""

        # Configure the top level parser
        super().__init__(prog='shinigami', formatter_class=RawTextHelpFormatter, description=self._build_description())
        subparsers = self.add_subparsers(required=True, parser_class=BaseParser)
        self.add_argument('--version', action='version', version=__version__)

        # This parser defines reusable arguments and is not directly exposed to the user
        common = ArgumentParser(add_help=False)
        common.add_argument('-i', '--ignore-nodes', nargs='*', default=defaults.ignore_nodes, help=f'ignore given nodes (default: {defaults.ignore_nodes or None})')
        common.add_argument('-u', '--uid-whitelist', nargs='+', type=loads, default=defaults.uid_whitelist, help=f'user IDs to scan (default: {defaults.uid_whitelist or None})')

        ssh_group = common.add_argument_group('ssh options')
        ssh_group.add_argument('-m', '--max-concurrent', type=int, default=defaults.max_concurrent, help=f'maximum concurrent SSH connections (default: {defaults.max_concurrent})')
        ssh_group.add_argument('-t', '--ssh-timeout', type=int, default=defaults.ssh_timeout, help=f'SSH connection timeout in seconds (default: {defaults.ssh_timeout})')

        debug_group = common.add_argument_group('debugging options')
        debug_group.add_argument('--debug', action='store_true', help='run the application in debug mode')
        debug_group.add_argument('-v', action='count', dest='verbosity', default=0, help='set verbosity to warning (-v), info (-vv), or debug (-vvv)')

        # Subparser for the `Application.scan` method
        scan = subparsers.add_parser('scan', parents=[common], help='terminate processes on one or more clusters')
        scan.add_argument('-c', '--clusters', nargs='+', required=True, help=f'cluster names to scan (default: {defaults.clusters or None})')
        scan.set_defaults(callable=Application.scan)

        # Subparser for the `Application.terminate` method
        terminate = subparsers.add_parser('terminate', parents=[common], help='terminate processes on a single node')
        terminate.set_defaults(callable=Application.terminate)

    @staticmethod
    def _build_description(settings_path: Path = SETTINGS_PATH) -> str:
        """Build the top level parser description

        The returned description warns users if custom default settings are configured on the parent machine.
        """

        base_description = 'Scan Slurm compute nodes and terminate orphan processes.'
        if settings_path.exists():
            base_description += f'\n\nCustom default settings are currently defined in {settings_path}'

        return base_description


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
        max_concurrent: asyncio.Semaphore,
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
        max_concurrent: asyncio.Semaphore,
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
        """Parse command-line arguments and execute the application

        Args:
            arg_list: Optionally parse the given arguments instead of the command line
        """

        defaults = Defaults.load()
        args = Parser(defaults).parse_args(arg_list)
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
