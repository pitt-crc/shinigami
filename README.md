# Shinigami

Shinigami is a stand alone Python script for killing errant processes on Slurm based HPC compute nodes.
The script scans for and terminates any running processes not associated with a currently running Slurm job.
Processes associated with whitelisted users (root, administrations, service accounts, etc.) are ignored.

## Setup and Configuration

Start by placing a copy of the script on a machine with access to the HPC cluster you wish to administrate.
The script can be run from any location, but  `/usr/local/sbin/` is a sensible choice.
Once the file is placed, make sure it has the appropriate permissions:

```bash
chmod 750 shinigami.py
```

The script is configurable via global variables defined at the top of the file.
Set the following variables as appropriate:


Finally, set up a crontab entry to run the script as often as you see fit.
The example below runs the script every half hour:

```cron
0,30 * * * * /usr/local/sbin/shinigami.py
```

You may wish to configure the cron job to run under a dedicated service account.
When doing so, ensure the user is added to the admin list and satisfies the following criteria:
- Exists on all compute nodes
- Has appropriate permissions to terminate system processes on compute nodes
- Has established SSH keys to connecting to compute nodes
