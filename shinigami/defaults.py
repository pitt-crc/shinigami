"""Defines default application settings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple, Union

from pydantic import Field
from pydantic_settings import BaseSettings

SETTINGS_PATH = Path('/etc/shinigami/settings.json')


class Defaults(BaseSettings):
    """Defines the settings schema and default settings values"""

    uid_whitelist: Tuple[Union[int, Tuple[int, int]], ...] = Field(
        title='Whitelisted User IDs',
        default=(0,),
        description='Only terminate processes launched by users with the given UID values.')

    clusters: Tuple[str, ...] = Field(
        title='Clusters to Scan',
        default=tuple(),
        description='Scan and terminate processes on the given Slurm clusters.')

    ignore_nodes: Tuple[str, ...] = Field(
        title='Ignore Nodes',
        default=tuple(),
        description='Ignore nodes with Slurm names containing any of the provided substrings.')

    max_concurrent: int = Field(
        title='Maximum SSH Connections',
        default=10,
        description='The maximum number of simultaneous SSH connections to open.')

    ssh_timeout: int = Field(
        title='SSH Timeout',
        default=120,
        description='Maximum time in seconds to complete an outbound SSH connection.')

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH) -> Defaults:
        """Factory method for loading application settings from disk

        If a settings file does not exist, return default settings values.

        Args:
            path: The settings file to read

        Returns:
            An instance of the parent class
        """

        if path.exists():
            return cls.model_validate(json.loads(path.read_text()))

        return cls()  # Returns default settings
