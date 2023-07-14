"""Shinigami is a stand alone Python application for killing errant processes
on Slurm based compute nodes. The application scans for and terminates any
running processes not associated with a currently running Slurm job. Processes
associated with whitelisted users are ignored.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version('shinigami')

except importlib.metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = '0.0.0'
