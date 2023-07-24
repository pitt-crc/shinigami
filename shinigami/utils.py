"""Utilities for fetching system information and terminating processes."""

import logging
from shlex import split
from subprocess import Popen, PIPE
from typing import Union, Tuple, Collection

import asyncssh

from .settings import SETTINGS


def id_in_whitelist(id_value: int, blacklist: Collection[Union[int, Tuple[int, int]]]) -> bool:
    """Return whether an ID is in a list of ID values

    Args:
        id_value: The ID value to check
        blacklist: A collection of ID values and ID ranges

    Returns:
        Whether the ID is in the blacklist
    """

    for id_def in blacklist:
        if isinstance(id_def, int) and id_value == id_def:
            return True

        elif isinstance(id_def, tuple) and (id_def[0] <= id_value <= id_def[1]):
            return True

    return False


async def get_nodes(cluster: str) -> str:
    """Return a set of nodes included a given Slurm cluster

    Args:
        cluster: Name of the cluster to fetch nodes for

    Returns:
        A set of cluster names
    """

    sub_proc = Popen(split(f"sinfo -M {cluster} -N -o %N -h"), stdout=PIPE, stderr=PIPE)
    stdout, stderr = sub_proc.communicate()
    if stderr:
        raise RuntimeError(stderr)

    all_nodes = stdout.decode().strip().split('\n')
    for unique_node in set(all_nodes):
        if any(substring in unique_node for substring in SETTINGS.ignore_nodes):
            logging.info(f'Skipping node {unique_node} on cluster {cluster}')

        yield unique_node


async def terminate_errant_processes(cluster: str, node: str) -> None:
    """Terminate non-slurm processes on a given node

    Args:
        cluster: The name of the cluster
        node: The name of the node
    """

    async with asyncssh.connect(node) as conn:

        # Identify users running valid slurm jobs
        logging.info(f'Scanning for processes on node {node}')
        slurm_users = conn.run(f'squeue -h -M {cluster} -w {node} -o %u').strip().split('\n')

        # Create a list of process info [[pid, user, uid, cmd], ...]
        ps_output = conn.run('ps --no-heading -eo pid,user,uid,gid,cmd')
        proc_users = [line.split() for line in ps_output.strip().split()]

        # Identify which processes to kill
        pids_to_kill = []
        for pid, user, uid, gid, cmd in proc_users:
            if not (
                (user in slurm_users) or
                id_in_whitelist(int(uid), SETTINGS.uid_whitelist) or
                id_in_whitelist(int(gid), SETTINGS.gid_whitelist)
            ):
                logging.debug(f'Marking process for termination user={user}, uid={uid}, pid={pid}, cmd={cmd}')
                pids_to_kill.append(pid)

        if SETTINGS.debug:
            return

        proc_id_str = ' '.join(pids_to_kill)
        logging.info(f"Sending termination signal for processes {proc_id_str}")

        result = await conn.run(f"kill -9 {proc_id_str}")
        if result.stderr:
            logging.error(f'STDERR when killing processes: "{result.stderr}"')
