"""Shinigami is a command-line application for killing errant processes
on Slurm based compute nodes. The application scans for and terminates any
running processes not associated with a currently running Slurm job.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version('crc-shinigami')

except importlib.metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = '0.0.0'
