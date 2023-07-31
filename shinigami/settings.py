"""The application settings schema."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Set, Tuple, Union, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Defines the settings schema and default settings values"""

    debug: bool = Field(
        title='Debug Mode',
        default=False,
        description='When enabled, processes are scanned and logged but not terminated.')

    uid_whitelist: Set[Union[int, Tuple[int, int]]] = Field(
        title='Whitelisted User IDs',
        default=[0],
        description='Do not terminate processes launched by users with the given UID values.')

    gid_whitelist: Set[Union[int, Tuple[int, int]]] = Field(
        title='Whitelisted Group IDs',
        default=[0],
        description='Do not terminate processes launched by users with the given GID values.')

    clusters: Tuple[str, ...] = Field(
        title='Clusters to Scan',
        default=tuple(),
        decription='Scan and terminate processes on the given Slurm clusters.')

    ignore_nodes: Tuple[str, ...] = Field(
        title='Ignore Nodes',
        default=tuple(),
        description='Ignore nodes with Slurm names containing any of the provided substrings.')

    max_concurrent: int = Field(
        title='Maximum SSH Connections',
        default=10,
        description='The maximum number of simultaneous SSH connections to open.')

    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = Field(
        title='Logging Level',
        default='INFO',
        description='Application logging level.')

    log_path: Optional[Path] = Field(
        title='Log Path',
        default_factory=lambda: Path(NamedTemporaryFile().name),
        description='Optionally log application events to a file.')

    verbosity: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = Field(
        title='Default console verbosity',
        default='ERROR',
        description='Default verbosity level for console output.')
