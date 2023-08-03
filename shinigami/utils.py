"""Utilities for fetching system information and terminating processes."""

import asyncio
import logging
from shlex import split
from subprocess import Popen, PIPE
from typing import Union, Tuple, Collection

import asyncssh


def id_in_whitelist(id_value: int, blacklist: Collection[Union[int, Tuple[int, int]]]) -> bool:
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

        elif isinstance(id_def, int) and id_value == id_def:
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
    cluster: str,
    node: str,
    ssh_limit: asyncio.Semaphore,
    uid_whitelist,
    gid_whitelist,
    timeout: int = 120,
    debug: bool = False
) -> None:
    """Terminate non-Slurm processes on a given node

    Args:
        cluster: The Slurm name of the cluster to terminate processes on
        node: The DNS resolvable name of the node to terminate processes on
        ssh_limit: Semaphore object used to limit concurrent SSH connections
        uid_whitelist: Do not terminate processes owned by the given UID
        gid_whitelist: Do not terminate processes owned by the given GID
        timeout: Maximum time in seconds to complete an outbound SSH connection
        debug: Log which process to terminate but do not terminate them
    """

    # Define SSH connection settings
    ssh_options = asyncssh.SSHClientConnectionOptions(
        connect_timeout=timeout)

    logging.debug(f'Waiting to connect to {node}')
    async with ssh_limit, asyncssh.connect(node, options=ssh_options) as conn:

        # Identify users running valid Slurm jobs
        logging.info(f'[{node}] Scanning for processes')
        slurm_users = conn.run(f'squeue -h -M {cluster} -w {node} -o %u').strip().split('\n')

        # Create a list of process info [[pid, user, uid, gid, cmd], ...]
        ps_output = conn.run('ps --no-heading -eo pid,user,uid,gid,cmd')
        proc_users = [line.split() for line in ps_output.strip().split()]

        # Identify which processes to kill
        pids_to_kill = []
        for pid, user, uid, gid, cmd in proc_users:
            if not (
                (user in slurm_users) or
                id_in_whitelist(int(uid), uid_whitelist) or
                id_in_whitelist(int(gid), gid_whitelist)
            ):
                logging.debug(f'[{node}] Marking process for termination user={user}, uid={uid}, pid={pid}, cmd={cmd}')
                pids_to_kill.append(pid)

        if debug:
            return

        proc_id_str = ' '.join(pids_to_kill)
        logging.info(f"[{node}] Sending termination signal for processes {proc_id_str}")

        result = await conn.run(f"kill -9 {proc_id_str}")
        if result.stderr:
            logging.error(f'[{node}] STDERR when killing processes: "{result.stderr}"')
