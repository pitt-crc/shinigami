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
        A pandas DataFrame
    """

    # Add 1 to column widths when parsing ps output to account for space between columns
    ps_return = await conn.run('ps -eo pid:10,ppid:10,pgid:10,uid:10,cmd:500', check=True)
    return pd.read_fwf(StringIO(ps_return.stdout), widths=[11, 11, 11, 11, 500])


def filter_orphaned_processes(df: pd.DataFrame, ppid_column: str = 'PPID') -> pd.DataFrame:
    """Filter a DataFrame to only include orphaned processes

    Given a DataFrame with system process data, return a subset of the data
    containing processes parented by `INIT_PROCESS_ID`.

    Args:
        df: DataFrame to filter
        ppid_column: Column name containing parent process ID (PPID) values

    Returns:
        A filtered copy of the given DataFrame
    """

    return df[df[ppid_column] == INIT_PROCESS_ID]


def filter_user_processes(df: pd.DataFrame, uid_whitelist: Whitelist, uid_column: str = 'UID') -> pd.DataFrame:
    """Filter a DataFrame to only include whitelisted users

    Given a DataFrame with system process data, return a subset of the data
    containing processes owned by given user IDs.

    Args:
        df: DataFrame to filter
        uid_whitelist: List of user IDs to whitelist
        uid_column: Column name containing user ID (UID) values

    Returns:
        A filtered copy of the given DataFrame
    """

    whitelist_index = df[uid_column].apply(id_in_whitelist, whitelist=uid_whitelist)
    return df[whitelist_index]


def filter_env_defined(df: pd.DataFrame, var_names: list[str], pid_column: str = 'PID') -> pd.DataFrame:
    """Filter a DataFrame to only include processes with variable definitions

    Given a DataFrame with system process data, return a subset of the data
    containing processes where one or more of the given environmental variables are defined.

    Args:
        df: DataFrame to filter
        var_names: Variable names to check for
        pid_column: Column name containing process ID (PID) values

    Returns:
        A filtered copy of the given DataFrame
    """

    # grep -Eq '^DBUS_SESSION_BUS_ADDRESS=|^some_other_var=' /proc/44703/environ /proc/2235/environ;
    variable_regex = '|'.join(f'^{variable}=' for variable in var_names)
    proc_files = ' '.join(f'/proc/{proc_id}/environ' for proc_id in df[pid_column])
    cmd = f"grep -Eq '{variable_regex}' {proc_files}"

    # TODO: Filter dataframe

    return df


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

        # Identify orphaned processes and filter them by whitelist criteria
        process_df = await get_remote_processes(conn)
        process_df = filter_orphaned_processes(process_df, 'PPID')
        process_df = filter_user_processes(process_df, uid_whitelist, 'UID')

        for _, row in process_df.iterrows():
            logging.info(f'[{node}] Marking for termination {dict(row)}')

        if process_df.empty:
            logging.info(f'[{node}] no processes found')

        elif not debug:
            proc_id_str = ','.join(process_df.PGID.unique().astype(str))
            logging.info(f"[{node}] Sending termination signal for process groups {proc_id_str}")
            await conn.run(f"pkill --signal 9 --pgroup {proc_id_str}", check=True)
