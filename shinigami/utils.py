"""Utilities for fetching system information and terminating processes."""

import asyncio
import logging
from io import StringIO
from shlex import split
from subprocess import Popen, PIPE
from typing import Union, Tuple, Collection, List

import asyncssh
import pandas as pd

INIT_PROCESS_ID = 1

Whitelist = Collection[Union[int, Tuple[int, int]]]


def id_in_whitelist(id_value: int, whitelist: Whitelist) -> bool:
    """Return whether an ID is in a list of ID value definitions

    The `whitelist`  of ID values can contain a mix of integers and tuples
    of integer ranges. For example, [0, 1, (2, 9), 10] includes all IDs from
    zero through ten.

    Args:
        id_value: The ID value to check
        whitelist: A collection of ID values and ID ranges

    Returns:
        Whether the ID is in the whitelist
    """

    for id_def in whitelist:
        if hasattr(id_def, '__getitem__') and (id_def[0] <= id_value <= id_def[1]):
            return True

        elif id_value == id_def:
            return True

    return False


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
    return set(node for node in all_nodes if node not in ignore_nodes)


async def get_remote_processes(conn: asyncssh.SSHClientConnection) -> pd.DataFrame:
    """Fetch running process data from the remote machine

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

    Args:
        df: A DataFrame with a `PPID` column

    Returns:
        A copy of the given DataFrame
    """

    return df[df['PPID'] == INIT_PROCESS_ID]


def include_user_whitelist(df: pd.DataFrame, uid_whitelist: Whitelist) -> pd.DataFrame:
    """Filter a DataFrame to only include a subset of user IDs

    Given a DataFrame with system process data, return a subset of the data
    containing processes owned by the given user IDs.

    Args:
        df: A DataFrame with a `UID` column
        uid_whitelist: List of user IDs to whitelist

    Returns:
        A copy of the given DataFrame
    """

    whitelist_index = df['UID'].apply(id_in_whitelist, whitelist=uid_whitelist)
    return df[whitelist_index]


def exclude_active_slurm_users(df: pd.DataFrame) -> pd.DataFrame:
    """Filter a DataFrame to exclude user IDs tied to a running slurm job

    Args:
        df: A DataFrame with `UID` and `CMD` columns

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
        uid_whitelist: Do not terminate processes owned by the given UID
        ssh_limit: Semaphore object used to limit concurrent SSH connections
        ssh_options: Options for configuring the outbound SSH connection
        debug: Log which process to terminate but do not terminate them
    """

    logging.debug(f'[{node}] Waiting for SSH pool')
    async with ssh_limit, asyncssh.connect(node, options=ssh_options) as conn:
        logging.info(f'[{node}] Scanning for processes')
        process_df = await get_remote_processes(conn)

        # Filter them by various whitelist/blacklist criteria
        process_df = include_orphaned_processes(process_df)
        process_df = include_user_whitelist(process_df, uid_whitelist)
        process_df = exclude_active_slurm_users(process_df)

        for _, row in process_df.iterrows():  # pragma: nocover
            logging.info(f'[{node}] Marking for termination {dict(row)}')

        if process_df.empty:  # pragma: nocover
            logging.info(f'[{node}] no processes found')

        elif not debug:
            proc_id_str = ','.join(process_df.PGID.unique().astype(str))
            logging.info(f"[{node}] Sending termination signal for process groups {proc_id_str}")
            await conn.run(f"pkill --signal 9 --pgroup {proc_id_str}", check=True)
