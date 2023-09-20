"""The application command-line interface."""

import asyncio
import logging
import logging.config
import logging.handlers
from argparse import RawTextHelpFormatter, ArgumentParser
from typing import List

from . import __version__, utils
from .settings import Settings, SETTINGS_PATH


class Parser(ArgumentParser):
    """Defines the command-line interface and parses command-line arguments"""

    def __init__(self) -> None:
        """Define the command-line interface"""

        super().__init__(
            prog='shinigami',
            formatter_class=RawTextHelpFormatter,  # Allow newlines in description text
            description=(
                'Scan Slurm compute nodes and terminate errant processes.\n\n'
                f'See {SETTINGS_PATH} for the current application settings.'
            ))

        self.add_argument('--version', action='version', version=__version__)
        self.add_argument('--debug', action='store_true', help='force the application to run in debug mode')
        self.add_argument('-v', action='count', dest='verbosity', default=0,
                          help='set output verbosity to warning (-v), info (-vv), or debug (-vvv)')


class Application:
    """Entry point for instantiating and executing the application"""

    def __init__(self, settings: Settings) -> None:
        """Instantiate a new instance of the application

        Args:
            settings: Settings to use when configuring and executing the application
        """

        self._settings = settings
        self._configure_logging()

    def _configure_logging(self) -> None:
        """Configure Python logging

        Configured loggers:
            console_logger: For logging to the console only
            file_logger: For logging to the log file only
            root: For logging to the console and log file
        """

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
                    'level': self._settings.verbosity
                },
                'log_file_handler': {
                    'class': 'logging.FileHandler',
                    'formatter': 'log_file_formatter',
                    'level': self._settings.log_level,
                    'filename': self._settings.log_path
                },
            },
            'loggers': {
                'console_logger': {'handlers': ['console_handler'], 'level': 0, 'propagate': False},
                'file_logger': {'handlers': ['log_file_handler'], 'level': 0, 'propagate': False},
                '': {'handlers': ['console_handler', 'log_file_handler'], 'level': 0, 'propagate': False},
            }
        })

    async def run(self) -> None:
        """Terminate errant processes on all clusters/nodes configured in application settings."""

        if not self._settings.clusters:
            logging.warning('No cluster names configured in application settings.')

        ssh_limit = asyncio.Semaphore(self._settings.max_concurrent)
        for cluster in self._settings.clusters:
            logging.info(f'Starting scan for nodes in cluster {cluster}')

            # Launch a concurrent job for each node in the cluster
            nodes = utils.get_nodes(cluster, self._settings.ignore_nodes)
            coroutines = [
                utils.terminate_errant_processes(
                    node=node,
                    ssh_limit=ssh_limit,
                    uid_whitelist=self._settings.uid_whitelist,
                    timeout=self._settings.ssh_timeout,
                    debug=self._settings.debug)
                for node in nodes
            ]

            # Gather results from each concurrent run and check for errors
            results = await asyncio.gather(*coroutines, return_exceptions=True)
            for node, result in zip(nodes, results):
                if isinstance(result, Exception):
                    logging.error(f'Error with node {node}: {result}')

    @classmethod
    def execute(cls, arg_list: List[str] = None) -> None:
        """Parse command-line arguments and execute the application"""

        args = Parser().parse_args(arg_list)
        verbosity_to_log_level = {0: logging.ERROR, 1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}

        # Load application settings - override defaults using parsed arguments
        settings = Settings.load()
        settings.verbosity = verbosity_to_log_level.get(args.verbosity, logging.DEBUG)
        settings.debug = settings.debug or args.debug

        try:
            application = cls(settings)
            asyncio.run(application.run())

        except KeyboardInterrupt:
            pass

        except Exception as caught:
            logging.getLogger('file_logger').critical('Application crash', exc_info=caught)
            logging.getLogger('console_logger').critical(str(caught))
