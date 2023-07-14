#!/usr/bin/env python
"""Kill errant Slurm processes on compute nodes"""

import logging
import logging.handlers
from shlex import split
from subprocess import Popen, PIPE
from typing import Set, Union, Tuple

# Log processes but don't terminate them
debug = True

# The clusters we want to check for dead processes
clusters = ("smp", "htc", "gpu", "mpi", "invest")

# Users that are never terminated
WHITELIST = (
    154258,  # leb140
    155316,  # djp81
    157577,  # nlc60
    153718,  # chx33
    158335,  # yak73
    15083,  # kimwong
    152768,  # sak236
    15057,  # jar7
    152118,  # twc17
    152229,  # fangping
    157632,  # gam134
)

# Ignore nodes with names containing the following text
ignore_nodes = ('ppc-n', 'mems-n')

# Configure logging
logger = logging.getLogger('shinigami')
syslog_handler = logging.handlers.SysLogHandler('/dev/log')
formatter = logging.Formatter('[%(name)s] %(levelname)s - %(message)s')
syslog_handler.setFormatter(formatter)
logger.addHandler(syslog_handler)


def id_in_blacklist(id_value: int, blacklist: Tuple[Union[int, Tuple[int, int]]] = WHITELIST) -> bool:
    """Return whether an ID is in a black list of ID values

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

    nodes = shell_command_to_list(f"sinfo -M {cluster} -N -o %N -h")
    return set(nodes)


def terminate_errant_processes(cluster: str, node: str) -> None:
    """Terminate non-slurm processes on a given node

    Args:
        cluster: The name of the cluster
        node: The name of the node
    """

    logging.info(f'Scanning for processes on node {node}')

    # Identify users running valid slurm jobs
    slurm_users = shell_command_to_list(f'squeue -h -M {cluster} -w {node} -o %u')

    # Create a list of process info [[pid, user, uid, cmd], ...]
    node_processes_raw = shell_command_to_list(f'ssh {node} "ps --no-heading -eo pid,user,uid,cmd"')
    proc_users = [line.split() for line in node_processes_raw]

    # Identify which processes to kill
    pids_to_kill = []
    for pid, user, uid, cmd in proc_users:
        if (not id_in_blacklist(int(uid))) and (user not in slurm_users):
            logging.debug(f'Marking process for termination user={user}, uid={uid}, pid={pid}, cmd={cmd}')
            pids_to_kill.append(pid)

    if not debug:
        kill_str = ' '.join(pids_to_kill)
        logging.info("Sending termination signal")
        shell_command_to_list(f"ssh {node} 'kill -9 {kill_str}'")


def main() -> None:
    """Terminate errant processes on all clusters/nodes configured in application settings."""

    for cluster in clusters:
        logging.info(f'Starting scan for cluster {cluster}')

        for node in get_nodes(cluster):
            if any(substring in node for substring in ignore_nodes):
                logging.info(f'Skipping node {node} on cluster {cluster}')
                continue

            terminate_errant_processes(cluster, node)


if __name__ == '__main__':
    main()
