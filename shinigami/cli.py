"""The application commandline interface."""

import logging
import logging.handlers
from argparse import ArgumentParser

from . import __version__, utils
from .settings import SETTINGS, settings_path


class Parser(ArgumentParser):
    """Defines the commandline interface and parses commandline arguments"""

    def __init__(self) -> None:
        """Define arguments for the command line interface"""

        super().__init__(
            prog='shinigami',
            description=(
                'Scan slurm compute nodes and terminate errant processes.\n\n'
                f'See {settings_path} for current application settings.'
            ))

        self.add_argument('--version', action='version', version=__version__)


class Application:
    """Entry point for instantiating and executing the application"""

    @classmethod
    def _configure_logging(cls) -> None:
        """Configure python logging"""

        logger = logging.getLogger()
        syslog_handler = logging.handlers.SysLogHandler('/dev/log')
        formatter = logging.Formatter('[%(name)s] %(levelname)s - %(message)s')
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)

    @staticmethod
    def run() -> None:
        """Terminate errant processes on all clusters/nodes configured in application settings."""

        if SETTINGS.debug:
            logging.warning('Application is running in debug mode')

        for cluster in SETTINGS.clusters:
            logging.info(f'Starting scan for nodes in cluster {cluster}')

            for node in utils.get_nodes(cluster):
                if any(substring in node for substring in SETTINGS.ignore_nodes):
                    logging.info(f'Skipping node {node} on cluster {cluster}')
                    continue

                utils.terminate_errant_processes(cluster, node)

    @classmethod
    def execute(cls) -> None:
        """Parse commandline arguments and execute the application"""

        parser = Parser()
        parser.parse_args()

        try:
            cls._configure_logging()
            cls.run()

        except Exception as excep:
            parser.error(str(excep))
