"""Utilities for fetching system information and terminating processes."""

import asyncio
import logging
from io import StringIO
from shlex import split
from subprocess import Popen, PIPE
from typing import Union, Tuple, Collection, List

import asyncssh
import pandas as pd

# Technically the init process ID may vary with the system
# architecture, but 1 is an almost universal default
INIT_PROCESS_ID = 1


def get_nodes(cluster: str, ignore_nodes: Collection[str] = tuple()) -> set:
    """Return a set of nodes included in a given Slurm cluster

    Args:
        cluster: Name of the cluster to fetch nodes for
        ignore_nodes: Do not return nodes included in the provided list

    Returns:
        A set of cluster names
    """

    logging.debug(f'Fetching node list for cluster {cluster}')
    sub_proc = Popen(split(f"sinfo -M {cluster} -N -o %N -h"), stdout=PIPE, stderr=PIPE)
    stdout, stderr = sub_proc.communicate()
    if stderr:
        raise RuntimeError(stderr)

    all_nodes = stdout.decode().strip().split('\n')
    return set(all_nodes) - set(ignore_nodes)


async def get_remote_processes(conn: asyncssh.SSHClientConnection) -> pd.DataFrame:
    """Fetch running process data from a remote machine

    The returned DataFrame is guaranteed to have columns `PID`, `PPID`, `PGID`,
    `UID`, and `CND`.

    Args:
        conn: Open SSH connection to the machine

    Returns:
        A pandas DataFrame with process data
    """

    # Add 1 to column widths when parsing ps output to account for space between columns
    ps_return = await conn.run('ps -eo pid:10,ppid:10,pgid:10,uid:10,cmd:500', check=True)
    return pd.read_fwf(StringIO(ps_return.stdout), widths=[11, 11, 11, 11, 500])


def include_orphaned_processes(df: pd.DataFrame) -> pd.DataFrame:
    """Filter a DataFrame to only include orphaned processes

    Given a DataFrame with system process data, return a subset of the data
    containing processes parented by `INIT_PROCESS_ID`.

    See the `get_remote_processes` function for the assumed DataFrame data model.

    Args:
        df: A DataFrame with process data

    Returns:
        A copy of the given DataFrame
    """

    return df[df['PPID'] == INIT_PROCESS_ID]


def include_user_whitelist(df: pd.DataFrame, uid_whitelist: Collection[Union[int, Tuple[int, int]]]) -> pd.DataFrame:
    """Filter a DataFrame to only include a subset of user IDs

    Given a DataFrame with system process data, return a subset of the data
    containing processes owned by the given user IDs.

    See the `get_remote_processes` function for the assumed DataFrame data model.

    Args:
        df: A DataFrame with process data
        uid_whitelist: List of user IDs to whitelist

    Returns:
        A copy of the given DataFrame
    """

    whitelisted_uid_values = []
    for elt in uid_whitelist:
        if isinstance(elt, int):
            whitelisted_uid_values.append(elt)

        else:
            umin, umax = elt
            whitelisted_uid_values.extend(range(umin, umax))

    return df[df['UID'].isin(whitelisted_uid_values)]


def exclude_active_slurm_users(df: pd.DataFrame) -> pd.DataFrame:
    """Filter a DataFrame to exclude user IDs tied to a running slurm job

    Given a DataFrame with system process data, return a subset of the data
    that excludes processes owned by users running a `slurmd` command.

    See the `get_remote_processes` function for the assumed DataFrame data model.

    Args:
        df: A DataFrame with process data

    Returns:
        A copy of the given DataFrame
    """

    is_slurm = df['CMD'].str.contains('slurmd')
    slurm_uids = df['UID'][is_slurm].unique()
    return df[~df['UID'].isin(slurm_uids)]


async def terminate_errant_processes(
    node: str,
    uid_whitelist: Collection[Union[int, List[int]]],
    ssh_limit: asyncio.Semaphore = asyncio.Semaphore(1),
    ssh_options: asyncssh.SSHClientConnectionOptions = None,
    debug: bool = False
) -> None:
    """Terminate orphaned processes on a given node

    Args:
        node: The DNS resolvable name of the node to terminate processes on
        uid_whitelist: Do not terminate processes owned by the given UIDs
        ssh_limit: Semaphore object used to limit concurrent SSH connections
        ssh_options: Options for configuring the outbound SSH connection
        debug: Log which process to terminate but do not terminate them
    """

    logging.debug(f'[{node}] Waiting for SSH pool')
    async with ssh_limit, asyncssh.connect(node, options=ssh_options) as conn:
        logging.info(f'[{node}] Scanning for processes')
        process_df = await get_remote_processes(conn)

        # Filter process data by various whitelist/blacklist criteria
        # Outputs from each filter function call are passed to the next filter
        # so the order of the function calls matter significantly
        process_df = exclude_active_slurm_users(process_df)
        process_df = include_orphaned_processes(process_df)
        process_df = include_user_whitelist(process_df, uid_whitelist)

        for _, row in process_df.iterrows():  # pragma: nocover
            logging.info(f'[{node}] Marking for termination {dict(row)}')

        if process_df.empty:  # pragma: nocover
            logging.info(f'[{node}] no processes found')

        elif not debug:
            proc_id_str = ','.join(process_df.PGID.unique().astype(str))
            logging.info(f"[{node}] Sending termination signal for process groups {proc_id_str}")
            await conn.run(f"pkill --signal 9 --pgroup {proc_id_str}", check=True)
