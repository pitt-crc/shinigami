"""The application settings schema.

Settings are automatically loaded at instantiation and cached under
the ``SETTINGS`` variable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Set, Tuple, Union

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

_settings_path = Path('/etc/shinigami/settings.yml')


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
        description='Ignore nodes with names containing any of the provided substrings.'
    )

    max_concurrent: int = Field(
        title='Maximum SSH Connections',
        default=10,
        description='The maximum number of simultaneous SSH connections to open.'
    )


# Load application settings from disk
SETTINGS = Settings()
if _settings_path.exists():
    SETTINGS = SETTINGS.model_validate(yaml.safe_load(_settings_path))
