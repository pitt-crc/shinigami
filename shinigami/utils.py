"""Utilities for fetching system information and terminating processes."""

import logging
from shlex import split
from subprocess import Popen, PIPE
from typing import Set, Union, Tuple, Collection

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


def shell_command_to_list(command: str) -> list:
    """Run a shell command and return STDOUT as a list

    Args:
        command: The command to run

    Returns:
        A list of lines written to STDOUT by the command

    Raises:
        RuntimeError: If the command writes to STDERR
        FileNotFoundError: If the command cannot be found
    """

    logging.debug(f'Executing command: {command}')
    sub_proc = Popen(split(command), stdout=PIPE, stderr=PIPE)
    stdout, stderr = sub_proc.communicate()
    if stderr:
        raise RuntimeError(stderr)

    return stdout.decode().strip().split('\n')


def get_nodes(cluster: str) -> Set[str]:
    """Return a set of nodes included a given Slurm cluster

    Args:
        cluster: Name of the cluster to fetch nodes for

    Returns:
        A set of cluster names
    """

    return set(shell_command_to_list(f"sinfo -M {cluster} -N -o %N -h"))


def terminate_errant_processes(cluster: str, node: str) -> None:
    """Terminate non-slurm processes on a given node

    Args:
        cluster: The name of the cluster
        node: The name of the node
    """

    # Identify users running valid slurm jobs
    logging.info(f'Scanning for processes on node {node}')
    slurm_users = shell_command_to_list(f'squeue -h -M {cluster} -w {node} -o %u')

    # Create a list of process info [[pid, user, uid, cmd], ...]
    node_processes_raw = shell_command_to_list(f'ssh {node} "ps --no-heading -eo pid,user,uid,gid,cmd"')
    proc_users = [line.split() for line in node_processes_raw]

    # Identify which processes to kill
    pids_to_kill = []
    for pid, user, uid, gid, cmd in proc_users:
        if not (
            (user in slurm_users) or
            id_in_whitelist(int(uid), SETTINGS.uid_whitelist) or
            id_in_whitelist(int(gid), SETTINGS.gid_whitelist)
        ):
            logging.info(f'Marking process for termination user={user}, uid={uid}, pid={pid}, cmd={cmd}')
            pids_to_kill.append(pid)

    if not SETTINGS.debug:
        kill_str = ' '.join(pids_to_kill)
        logging.info("Sending termination signal")
        shell_command_to_list(f"ssh {node} 'kill -9 {kill_str}'")
