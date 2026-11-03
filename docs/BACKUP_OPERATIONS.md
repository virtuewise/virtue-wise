# Backup operations

VIRTUE WISE includes a local SQLite snapshot tool and a sample systemd timer. The application does **not** start its own scheduler: scheduled backups only occur after the operating-system timer is installed and configured.

## What the tool does

- Uses SQLite's online backup API to create a consistent database snapshot, including while the app is running.
- Verifies SQLite integrity and validates the stored VIRTUE WISE model before publishing the snapshot.
- Writes snapshots atomically and restricts backup files to owner read/write permissions where supported (0600).
- Retains the newest 30 snapshots by default.
- Verifies a selected snapshot before restore and preserves the current database as a pre-restore snapshot before replacing it.
- Does not encrypt backups. Protect the backup directory with OS permissions and an encrypted disk/volume; keep an additional copy on a separate protected device if the data matters.

## Configure paths and retention

Set these variables consistently for the application and the backup service:

```bash
VIRTUE_WISE_DB=/var/lib/virtue-wise/virtue-wise.sqlite3
VIRTUE_WISE_BACKUP_DIR=/var/backups/virtue-wise
VIRTUE_WISE_BACKUP_RETENTION_COUNT=30
```

The default backup directory is a `backups` folder beside the configured database. For better recovery, configure a dedicated directory on a different volume from the live database. Backups contain the complete project and should be treated as sensitive.

## Run a backup manually

From the repository root with the project environment activated:

```bash
python -m app.backup create
python -m app.backup verify /var/backups/virtue-wise/virtue-wise-YYYYMMDDTHHMMSSffffffZ.sqlite3
python -m app.backup prune --keep 30
```

The `create` command creates a snapshot, verifies it, and prunes older snapshots. It fails rather than creating an empty backup when the live database does not exist yet.

## Schedule daily backups with systemd

The sample files are in `deploy/systemd/`. They assume:

- the service account is named `virtuewise`;
- the application checkout is at `/opt/virtue-wise`;
- its virtual environment is at `/opt/virtue-wise/.venv`;
- the database and backup directories are `/var/lib/virtue-wise` and `/var/backups/virtue-wise`.

Adjust the service file's user, group, working directory, interpreter, and writable paths to match the host. Create the directories and environment file:

```bash
sudo install -d -o virtuewise -g virtuewise -m 0700 /var/lib/virtue-wise /var/backups/virtue-wise
sudo install -d -o root -g root -m 0755 /etc/virtue-wise
sudoedit /etc/virtue-wise/backup.env
```

Put the three environment variables shown above in `/etc/virtue-wise/backup.env`, then install and enable the timer:

```bash
sudo install -m 0644 deploy/systemd/virtue-wise-backup.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/virtue-wise-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now virtue-wise-backup.timer
systemctl list-timers virtue-wise-backup.timer
```

The timer runs daily at 02:15 local system time and catches up after downtime. Check the most recent run with:

```bash
sudo systemctl status virtue-wise-backup.timer
sudo journalctl -u virtue-wise-backup.service
```

Do not assume scheduling is active until the timer is enabled and a successful backup is visible. The app itself does not install or manage system services.

## Verify and restore

Verify a snapshot before relying on it:

```bash
python -m app.backup verify /path/to/virtue-wise-YYYYMMDDTHHMMSSffffffZ.sqlite3
```

To restore:

1. Stop the VIRTUE WISE application. Do not restore a database file while the app is running.
2. Verify the intended snapshot with the command above.
3. Run the restore command and inspect the printed pre-restore snapshot path:

```bash
python -m app.backup restore /path/to/verified-snapshot.sqlite3 --yes
```

4. Restart the application and verify the project title, goal, record counts, evidence links, review states, and scenarios.
5. Create a fresh backup after successful recovery.

Restore is staged and verified before replacing the live database. If a live database exists, the tool creates a pre-restore snapshot first. Keep the original backup unchanged until recovery has been checked.

## Recovery objectives and limitations

With the supplied daily timer installed and completing successfully, the intended recovery-point objective is up to 24 hours of changes. This is an operational target, not a guarantee; verify timer execution and backup files. Recovery time has not yet been measured, so no RTO is claimed. Periodically perform a restore drill on a disposable database and record its duration and result.

The backup files are not encrypted by VIRTUE WISE. Host compromise, disk loss, ransomware, or a user who can read the backup directory can expose or destroy them. Use OS-level encryption, restrictive ownership, and a separate protected copy. The systemd sample is an installation template and must be adapted and reviewed for the actual host.
