#!/usr/bin/env python
"""Kill errant Slurm processes on compute nodes"""

import re
from datetime import datetime
from shlex import split
from subprocess import Popen, PIPE
from typing import Tuple, Optional

# Log processes but don't terminate them
debug = True

# The clusters we want to check for dead processes
clusters = ("smp", "htc", "gpu", "mpi", "invest")

# Users that are never terminated
admin_users = ('leb140', 'djp81', 'nlc60', 'chx33', 'yak73', 'kimwong', 'sak236', 'jar7', 'twc17', 'fangping', 'gam134')

# Nodes to never terminate processes on as a tuple of regex expressions or `None`
ignore_nodes = (r'.*ppc-n.*', r'.*mems-n.*')

# Logging directory with no trailing slash
log_directory = '/zfs1/crc/logs/shinigamit'


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


def check_ignore_node(node_name: str, patterns: Optional[Tuple[str, ...]]) -> bool:
    """Determine if a node should be ignored
    
    If the ``patterns`` argument is empty or ``None``, the return value is
    always True.

    Args:
        node_name: The name of the node to check
        patterns: Regex patterns indicating node names to ignore

    Returns:
        A boolean indicating whether the node matches any ignore patterns
    """

    if not node_name or patterns is None:
        return True

    regex_pattern = r'|'.join(patterns)
    return bool(re.findall(regex_pattern, node_name))


def get_active_nodes():
    """Return a dictionary of nodes included in each cluster

    Returns:
        A dictionary mapping cluster names to a collection of node names
    """

    # Figure out which nodes are active
    nodelist = {}
    for cluster in clusters:
        nodelist[cluster] = []
        nodes = shell_command_to_list("sinfo -M {0} -t mix,alloc,idle -N -o %N -h".format(cluster))
        for node in nodes:
            node_name = node.strip()
            if node != '' and node_name not in nodelist[cluster]:
                nodelist[cluster].append(node_name)

    return nodelist


def terminate_errant_processes(cluster, node):
    """Terminate processes on a given node

    For the given node:
      - Check for users running jobs
      - Check for users running processes
      - Kill any processes by users without running jobs

    Args:
        cluster: The name of the cluster
        node: The name of the node
    """

    if check_ignore_node(node, ignore_nodes):
        return

        # Reset to_log/admin_log strings
    admin_log = ""

    # Are there running jobs on this node?
    slurm_jobs = shell_command_to_list("squeue -h -M {0} -w {1} -o %A".format(cluster, node))
    slurm_users = []
    if len(slurm_jobs):  # Running Jobs
        # Who is running the jobs?
        for job in slurm_jobs:
            user = shell_command_to_list("squeue -h -M {0} -w {1} -j {2} -o %u".format(cluster, node, job))[-1]
            slurm_users.append(user)

    # Are there running processes on this node?
    node_processes_raw = shell_command_to_list('ssh {0} "ps --no-heading -eo pid,user,uid,time,cmd"'.format(node))
    proc_users = []
    for line in node_processes_raw:
        sp = line.split()
        try:
            pid, user, uid, time, cmd = int(sp[0]), sp[1], int(sp[2]), sp[3], sp[4:]

        except IndexError:
            # Issue on the node, log it, move to the next
            with open("{0}/{1}.log".format(log_directory, node), 'a') as log:
                log.write("--> {0} <--\n".format(datetime.now()))
                log.write("shinigami error")

            continue

        if uid >= 15000:  # Probably need to add a whitelist here!
            if user not in proc_users:
                proc_users.append((user, time, cmd, pid))

    # slurm_users and proc_users contain non-root/service accounts
    # -> Are any users running processes, but not jobs?
    to_kill = {}
    for user, time, cmd, pid in proc_users:
        if (user in admin_users) and (user not in slurm_users):
            admin_log += "node: {0}, user: {1}, time: {2}, cmd: {3}, pid: {4}\n".format(node, user, time, cmd, pid)

        elif user not in slurm_users:
            if user not in to_kill.keys():
                to_kill[user] = [pid]

            else:
                to_kill[user].append(pid)

    # Log information (if necessary)
    if to_kill:
        with open("{0}/{1}.log".format(log_directory, node), 'a') as log:
            log.write("--> {0} <--\n".format(datetime.now()))
            for user, pids in to_kill.items():
                kill_str = ' '.join([str(x) for x in pids])
                if not debug:
                    shell_command_to_list("ssh {0} 'kill -9 {1}'".format(node, kill_str))
                log.write("User {0}, got `kill -9 {1}`".format(user, kill_str))

    if len(admin_log) != 0:
        with open("{0}/{1}-admin.log".format(log_directory, node), 'a') as log:
            log.write("--> {0} <--\n".format(datetime.now()))
            log.write("{0}".format(admin_log))


def main():
    """Iterate over all clusters/nodes and terminate errant processes"""

    nodelist = get_active_nodes()
    for cluster in nodelist.keys():
        for node in nodelist[cluster]:
            terminate_errant_processes(cluster, node)


if __name__ == '__main__':
    main()
