#!/usr/bin/env python
'''
Written By:     Barry Moore II
Purpose:        Detect errant processes on compute nodes. Slurm doesn't clean up well after itself.
Name Origin:    Shinigami are gods or supernatural spirits which invite humans to death.
'''
from subprocess import Popen, PIPE
from shlex import split
from datetime import datetime


def run_command_to_list(command):
    sp = Popen(split(command), stdout=PIPE, stderr=PIPE)
    return sp.communicate()[0].strip().split('\n')


# Get the hostname
hostname = run_command_to_list("hostname -s")[0]

# Reset to_log/admin_log strings
to_log = ""
admin_log = ""

# Are there running jobs on this node?
slurm_jobs = run_command_to_list("squeue -h -w {0} -o %A".format(hostname))[1:]
slurm_users = []
if len(slurm_jobs): # Running Jobs
    # Who is running the jobs?
    for job in slurm_jobs:
        user = run_command_to_list("squeue -h -w {0} -j {1} -o %u".format(hostname, job))[-1]
        slurm_users.append(user)

# Are there running processes on this node?
node_processes_raw = run_command_to_list('ps --no-heading -eo pid,user,uid,time,cmd')
proc_users = []
for line in node_processes_raw:
    sp = line.split()
    try:
        pid, user, uid, time, cmd = int(sp[0]), sp[1], int(sp[2]), sp[3], sp[4:]
    except IndexError:
        # Issue on the node, log it, move to the next
        with open("/zfs1/crc/logs/shinigami/{0}.log".format(hostname), 'a') as log:
            log.write("--> {0} <--\n".format(datetime.now()))
            log.write("shinigami error")
        continue
    if uid >= 15000: # Probably need to add a whitelist here!
        if user not in proc_users:
            proc_users.append((user, time, cmd))

# slurm_users and proc_users contain non-root/service accounts                        
# -> Are any users running processes, but not jobs?
for user, time, cmd in proc_users:
    if (user in ['bmooreii', 'shs159', 'kimwong', 'sak236', 'jar7', 'twc17', 'fangping']) and (user not in slurm_users):
        admin_log += "node: {0}, user: {1}, time: {2}, cmd: {3}\n".format(hostname, user, time, cmd)
    elif user not in slurm_users:
        to_log += "node: {0}, user: {1}, time: {2}, cmd: {3}\n".format(hostname, user, time, cmd)

# Log information (if necessary)
if len(to_log) != 0:
    with open("/zfs1/crc/logs/shinigami/{0}.log".format(hostname), 'a') as log:
        log.write("--> {0} <--\n".format(datetime.now()))
        log.write("{0}".format(to_log))
if len(admin_log) != 0:
    with open("/zfs1/crc/logs/shinigami/{0}-admin.log".format(hostname), 'a') as log:
        log.write("--> {0} <--\n".format(datetime.now()))
        log.write("{0}".format(admin_log))

if len(to_log) != 0:
    exit(1)
else:
    exit(0)
