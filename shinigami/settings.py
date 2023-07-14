"""Define the application settings schema. """

from __future__ import annotations

from pathlib import Path
from typing import Set, Tuple, Union

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

_settings_path = Path('/etc/shinigami/settings.yml')


class Settings(BaseSettings):
    """Defines the schema and default values for top level application settings"""

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

    # Ignore nodes with names containing the following text
    ignore_nodes: Tuple[str, ...] = Field(
        title='Ignore Nodes',
        default=tuple(),
        description='Do not terminate processes on Slurm nodes containing any of the given substrings in their name.'
    )

    @classmethod
    def load_from_disk(cls, path: Path = _settings_path) -> Settings:
        """Create a new class instance using settings files loaded from disk

        Args:
            path: The path to read values from

        Returns:
            An instance of the parent class

        Raises:
            FileNotFoundError: If the given settings file cannot be found
        """

        if not path.exists():
            raise FileNotFoundError(f'Could not find settings file: {Path}')

        return cls.model_validate(yaml.safe_load(_settings_path))
