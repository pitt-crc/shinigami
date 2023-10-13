"""Shinigami is a command-line application for killing errant processes
on Slurm based compute nodes. The application scans for and terminates any
running processes not associated with a currently running Slurm job.

Individual users and groups can be whitelisted in the application settings file
via UID and GID values. Specific compute nodes can also be ignored using basic
string matching. See the ``settings`` module for more details.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version('crc-shinigami')

except importlib.metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = '0.0.0'
