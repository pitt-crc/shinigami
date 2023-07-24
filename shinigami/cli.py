"""The application commandline interface."""

import asyncio
import logging
import logging.config
import logging.handlers
from argparse import ArgumentParser, RawTextHelpFormatter
from typing import List

from . import __version__, utils
from .settings import SETTINGS, _settings_path


class Parser(ArgumentParser):
    """Defines the commandline interface and parses commandline arguments"""

    def __init__(self) -> None:
        """Define the commandline interface"""

        super().__init__(
            prog='shinigami',
            formatter_class=RawTextHelpFormatter,  # Allow newlines in description text
            description=(
                'Scan slurm compute nodes and terminate errant processes.\n\n'
                f'See {_settings_path} for current application settings.'
            ))

        self.add_argument('--version', action='version', version=__version__)
        self.add_argument('--debug', action='store_true', help='force the application to run in debug mode')
        self.add_argument(
            '-v', action='count', dest='verbose', default=0,
            help='set output verbosity to warning (-v), info (-vv), or debug (-vvv)')


class Application:
    """Entry point for instantiating and executing the application"""

    @staticmethod
    def _configure_debug(force_debug: bool = False) -> None:
        """Optionally force the application to run in debug mode

        Args:
            force_debug: If ``True`` force the application to run in debug mode
        """

        SETTINGS.debug = SETTINGS.debug or force_debug
        if SETTINGS.debug:
            logging.warning('Application is running in debug mode')

    @classmethod
    def _configure_logging(cls, console_log_level: int) -> None:
        """Configure python logging to the given level

        Args:
            console_log_level: Logging level to set console logging to
        """

        # Logging levels are set at the handler level instead of the logger level
        # This allows more flexible usage of the root logger

        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': True,
            'formatters': {
                'console_formatter': {
                    'format': '%(levelname)8s: %(message)s'
                },
                'log_file_formatter': {
                    'format': '%(levelname)8s | %(asctime)s | %(message)s'
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
                    'class': 'logging.FileHandler',
                    'formatter': 'log_file_formatter',
                    'level': SETTINGS.log_level,
                    'filename': SETTINGS.log_path
                },
            },
            'loggers': {
                'console_logger': {'handlers': ['console_handler'], 'level': 0, 'propagate': False},
                'file_logger': {'handlers': ['log_file_handler'], 'level': 0, 'propagate': False},
                '': {'handlers': ['console_handler', 'log_file_handler'], 'level': 0, 'propagate': False},
            }
        })

    @classmethod
    async def run(cls) -> None:
        """Terminate errant processes on all clusters/nodes configured in application settings."""

        if not SETTINGS.clusters:
            logging.warning('No cluster names configured in application settings.')

        for cluster in SETTINGS.clusters:
            logging.info(f'Starting scan for nodes in cluster {cluster}')

            try:
                await asyncio.gather(
                    *[utils.terminate_errant_processes(cluster, node) async for node in utils.get_nodes(cluster)]
                )

            except Exception as caught:
                logging.error(f'Error for cluster {cluster}: {caught}')

    @classmethod
    def execute(cls, arg_list: List[str] = None) -> None:
        """Parse commandline arguments and execute the application"""

        parser = Parser()
        args = parser.parse_args(arg_list)

        # Calculate the numeric logging level for the console.
        verbosity = 40 - (10 * args.verbose)

        # Configure the application
        cls._configure_logging(console_log_level=verbosity)
        cls._configure_debug(force_debug=args.debug)

        try:
            asyncio.run(cls.run())

        except Exception as caught:
            logging.getLogger('file_logger').critical('Application crash', exc_info=caught)
            logging.getLogger('console_logger').critical(str(caught))
