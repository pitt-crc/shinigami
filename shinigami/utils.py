"""Utilities for fetching system information and terminating processes."""

import asyncio
import logging
from io import StringIO
from shlex import split
from subprocess import Popen, PIPE
from typing import Union, Tuple, Collection

import asyncssh
import pandas as pd


def id_in_blacklist(id_value: int, blacklist: Collection[Union[int, Tuple[int, int]]]) -> bool:
    """Return whether an ID is in a list of ID values

    Args:
        id_value: The ID value to check
        blacklist: A collection of ID values and ID ranges

    Returns:
        Whether the ID is in the blacklist
    """

    for id_def in blacklist:
        if hasattr(id_def, '__getitem__') and (id_def[0] <= id_value <= id_def[1]):
            return True

        elif id_value == id_def:
            return True

    return False


def get_nodes(cluster: str, ignore_substring: Collection[str]) -> set:
    """Return a set of nodes included in a given Slurm cluster

    Args:
        cluster: Name of the cluster to fetch nodes for
        ignore_substring: Do not return nodes containing any of the given substrings

    Returns:
        A set of cluster names
    """

    logging.debug(f'Fetching node list for cluster {cluster}')
    sub_proc = Popen(split(f"sinfo -M {cluster} -N -o %N -h"), stdout=PIPE, stderr=PIPE)
    stdout, stderr = sub_proc.communicate()

    if stderr:
        raise RuntimeError(stderr)

    all_nodes = stdout.decode().strip().split('\n')
    is_valid = lambda node: not any(substring in node for substring in ignore_substring)
    return set(filter(is_valid, all_nodes))


async def terminate_errant_processes(
    node: str,
    ssh_limit: asyncio.Semaphore,
    uid_blacklist,
    timeout: int = 120,
    debug: bool = False
) -> None:
    """Terminate non-Slurm processes on a given node

    Args:
        node: The DNS resolvable name of the node to terminate processes on
        ssh_limit: Semaphore object used to limit concurrent SSH connections
        uid_blacklist: Do not terminate processes owned by the given UID
        timeout: Maximum time in seconds to complete an outbound SSH connection
        debug: Log which process to terminate but do not terminate them
    """

    # Define SSH connection settings
    ssh_options = asyncssh.SSHClientConnectionOptions(connect_timeout=timeout)

    logging.debug(f'[{node}] Waiting for SSH pool')
    async with ssh_limit, asyncssh.connect(node, options=ssh_options) as conn:

        # Fetch running process data from the remote machine
        logging.info(f'[{node}] Scanning for processes')
        ps_data = (await conn.run('ps -eo pid,ppid,pgid,uid,cmd', check=True)).stdout

        # Parse returned data by determining the width of each column
        # Assume columns are right justified and align with the header
        widths = []
        header = ps_data.split('\n')[0]
        for col in header.split():
            widths.append(header.index(col) + len(col) - sum(widths))

        widths[-1] = 500  # The last column is left justified so add some extra width
        process_df = pd.read_fwf(StringIO(ps_data), widths=widths)

        # Identify orphaned processes and filter them by the UID blacklist
        orphaned = process_df[process_df.PPID == 1]
        terminate = orphaned[orphaned['UID'].apply(id_in_blacklist, blacklist=uid_blacklist)]
        for _, row in terminate.iterrows():
            logging.debug(f'[{node}] Marking for termination {dict(row)}')

        if terminate.empty:
            logging.debug(f'[{node}] No orphaned processes found')

        elif not debug:
            proc_id_str = ' '.join(terminate.PGID.astype(str))
            logging.info(f"[{node}] Sending termination signal for process groups {proc_id_str}")
            await conn.run(f"pkill --signal -9 --pgroup {proc_id_str}", check=True)
