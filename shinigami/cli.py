"""The application commandline interface."""

import logging
import logging.handlers
from argparse import ArgumentParser
from typing import List

from . import __version__
from .main import main
from .settings import SETTINGS


class Parser(ArgumentParser):
    """Responsible for defining the commandline interface and parsing commandline arguments"""

    def __init__(self) -> None:
        """Define arguments for the command line interface"""
        super().__init__(
            prog='shinigami',
            description='...',
        )

        self.add_argument('--version', action='version', version=__version__)
        self.add_argument('--debug', action='store_true', help='run the application but do not send any emails')
        self.add_argument(
            '-v', action='count', dest='verbose', default=0,
            help='set output verbosity to warning (-v), info (-vv), or debug (-vvv)')


class Application:
    """Entry point for instantiating and executing the application"""

    @classmethod
    def _configure_logging(cls, console_log_level: int) -> None:
        """Configure python logging to the given level

        Args:
            console_log_level: Logging level to set console logging to
        """

        logger = logging.getLogger('shinigami')
        syslog_handler = logging.handlers.SysLogHandler('/dev/log')
        formatter = logging.Formatter('[%(name)s] %(levelname)s - %(message)s')
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)

    @staticmethod
    def _configure_debug_mode(debug: bool) -> None:
        """Globally configure debug mode

        Args:
            debug: Whether to enable (``True``) or disable (``False``) debug mode
        """

        SETTINGS.debug = debug

    @classmethod
    def execute(cls, arg_list: List[str] = None) -> None:
        """Parse arguments and execute the application

        This method is equivalent to parsing arguments and passing them to the `run` method.

        Args:
            arg_list: Parse the given argument list instead of parsing the command line
        """

        parser = Parser()
        args = parser.parse_args(arg_list)
        if args.debug:
            cls._configure_debug_mode(True)

        cls._configure_logging(args.verbose)

        try:
            main()
        except Exception as excep:
            parser.error(str(excep))