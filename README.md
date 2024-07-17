# Shinigami
[![](https://app.codacy.com/project/badge/Grade/d5325904cffc4936b24dd6be0d58a1ee)](https://app.codacy.com/gh/pitt-crc/shinigami/dashboard)
[![](https://app.codacy.com/project/badge/Coverage/d5325904cffc4936b24dd6be0d58a1ee)](https://app.codacy.com/gh/pitt-crc/shinigami/dashboard)

Shinigami is a stand alone Python application for killing errant processes on Slurm based compute nodes.
The application scans for and terminates any running processes not associated with a currently running Slurm job.
Processes associated with whitelisted users (root, administrators, service accounts, etc.) are ignored.

## Installation and Setup

The `shinigami` command line utility is installable via the pip (or pipx) package manager:

```bash
pipx install shinigami
```

To be of maximal use, it is recommended to run the utility every half hour.
However, you may find a different cadence more appropriate depending on your cluster size and use case.
Running the utility automatically is accomplished via a simple cron job:

```cron
0,30 * * * * shinigami
```

You may wish to configure the cron job to run under a dedicated service account.
When doing so, ensure the user is added to the admin list and satisfies the following criteria:

- Exists on all compute nodes
- Has appropriate permissions to terminate system processes on compute nodes
- Has established SSH keys for connecting to compute nodes
