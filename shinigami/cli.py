"""The application commandline interface."""

import logging
import logging.handlers
from argparse import ArgumentParser
from typing import List

from . import __version__, utils
from .settings import SETTINGS


class Parser(ArgumentParser):
    """Responsible for defining the commandline interface and parsing commandline arguments"""

    def __init__(self) -> None:
        """Define arguments for the command line interface"""

        super().__init__(
            prog='shinigami',
            description='Scan slurm compute nodes and terminate errant processes.',
        )

        self.add_argument('--version', action='version', version=__version__)


class Application:
    """Entry point for instantiating and executing the application"""

    @classmethod
    def _configure_logging(cls) -> None:
        """Configure python logging"""

        logger = logging.getLogger('shinigami')
        syslog_handler = logging.handlers.SysLogHandler('/dev/log')
        formatter = logging.Formatter('[%(name)s] %(levelname)s - %(message)s')
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)

    @staticmethod
    def run() -> None:
        """Terminate errant processes on all clusters/nodes configured in application settings."""

        for cluster in SETTINGS.clusters:
            logging.info(f'Starting scan for cluster {cluster}')

            for node in utils.get_nodes(cluster):
                if any(substring in node for substring in SETTINGS.ignore_nodes):
                    logging.info(f'Skipping node {node} on cluster {cluster}')
                    continue

                utils.terminate_errant_processes(cluster, node)

    @classmethod
    def execute(cls, arg_list: List[str] = None) -> None:
        """Parse arguments and execute the application

        This method is equivalent to parsing arguments and passing them to the `run` method.

        Args:
            arg_list: Parse the given argument list instead of parsing the command line
        """

        parser = Parser()
        parser.parse_args(arg_list)

        try:
            cls._configure_logging()
            cls.run()

        except Exception as excep:
            parser.error(str(excep))
