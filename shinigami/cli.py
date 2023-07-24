"""The application commandline interface."""

import asyncio
import logging
import logging.handlers
from argparse import ArgumentParser, RawTextHelpFormatter

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

    @staticmethod
    def _configure_logging() -> None:
        """Configure application logging"""

        logger = logging.getLogger()
        syslog_handler = logging.handlers.SysLogHandler('/dev/log')
        formatter = logging.Formatter('[%(name)s] %(levelname)s - %(message)s')
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)

    @classmethod
    async def run(cls) -> None:
        """Terminate errant processes on all clusters/nodes configured in application settings."""

        for cluster in SETTINGS.clusters:
            logging.info(f'Starting scan for nodes in cluster {cluster}')
            await asyncio.gather(
                utils.terminate_errant_processes(cluster, node) for node in utils.get_nodes(cluster)
            )

    @classmethod
    def execute(cls) -> None:
        """Parse commandline arguments and execute the application"""

        parser = Parser()
        args = parser.parse_args()

        # Configure the application
        cls._configure_debug(force_debug=args.debug)
        cls._configure_logging()

        try:
            asyncio.run(cls.run())

        except Exception as excep:
            parser.error(str(excep))
