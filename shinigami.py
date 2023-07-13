#!/usr/bin/env python
"""Kill errant Slurm processes on compute nodes"""

import logging
import logging.handlers
from shlex import split
from subprocess import Popen, PIPE

# Log processes but don't terminate them
debug = True

# The clusters we want to check for dead processes
clusters = ("smp", "htc", "gpu", "mpi", "invest")

# Users that are never terminated
admin_users = ('leb140', 'djp81', 'nlc60', 'chx33', 'yak73', 'kimwong', 'sak236', 'jar7', 'twc17', 'fangping', 'gam134')

# Ignore nodes with names containing the following text
ignore_nodes = ('ppc-n', 'mems-n')

# Configure logging
logger = logging.getLogger('shinigami')
syslog_handler = logging.handlers.SysLogHandler('/dev/log')
formatter = logging.Formatter('[%(name)s] %(levelname)s - %(message)s')
syslog_handler.setFormatter(formatter)
logger.addHandler(syslog_handler)


def shell_command_to_list(command):
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

    # Maintain backward compatibility between Python 2 and 3
    if isinstance(stdout, bytes):
        stdout = stdout.decode()

    return stdout.strip().split('\n')


def get_nodes(cluster):
    """Return a set of nodes included a given Slurm cluster

    Args:
        cluster: Name of the cluster to fetch nodes for

    Returns:
        A set of cluster names
    """

    nodes = shell_command_to_list("sinfo -M {0} -N -o %N -h".format(cluster))
    unique_nodes = set(nodes) - {''}
    return unique_nodes


def terminate_errant_processes(cluster, node):
    """Terminate processes on a given node

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
        if (user in admin_users) and (user not in slurm_users):
            logging.debug(f'Marking process for termination user={user}, uid={uid}, pid={pid}, cmd={cmd}')
            pids_to_kill.append(pid)

    if not debug:
        kill_str = ' '.join(pids_to_kill)
        logging.info("Sending termination signal")
        shell_command_to_list("ssh {0} 'kill -9 {1}'".format(node, kill_str))


def main():
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
