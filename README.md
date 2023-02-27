# Shinigami

Shinigami is a stand alone Python application for killing errant processes on Slurm based compute nodes.
The application scans for and terminates any running processes not associated with a currently running Slurm job.
Processes associated with whitelisted users (root, administrators, service accounts, etc.) are ignored.

## Setup and Configuration

Start by copying `shinigami.py` onto a machine with access to the HPC cluster you wish to administrate.
The script can be run from any location, but a sensible choice like `/usr/local/sbin/` is recommended.
Once the file is placed, make sure it has the appropriate permissions:

```bash
chmod 750 shinigami.py
```

The script is configurable via global variables defined at the top of the file.
Set the following variables as appropriate:

| Variable        | Description                                               |
|-----------------|-----------------------------------------------------------|
| `clusters`      | A list of Slurm cluster names to scan processes on.       |
| `admin_users`   | A list of usernames to ignore when terminating processes. |
| `log_directory` | The directory to write log files to.                      | 

Finally, set up a crontab entry to run the script as often as you see fit.
The example below runs the script every half hour:

```cron
0,30 * * * * /usr/local/sbin/shinigami.py
```

You may wish to configure the cron job to run under a dedicated service account.
When doing so, ensure the user is added to the admin list and satisfies the following criteria:

- Exists on all compute nodes
- Has appropriate permissions to terminate system processes on compute nodes
- Has established SSH keys for connecting to compute nodes
