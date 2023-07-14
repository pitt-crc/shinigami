from typing import Set, Tuple, Union

from pydantic import Field
from pydantic_settings import BaseSettings


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
        decription='Scan and terminate processes on the given Slurm clusters.')

    # Ignore nodes with names containing the following text
    ignore_nodes: Tuple[str, ...] = Field(
        title='Ignore Nodes',
        description='Do not terminate processes on Slurm nodes containing any of the given substrings in their name.'
    )
