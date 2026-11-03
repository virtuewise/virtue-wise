# Backup operations

VIRTUE WISE includes a local SQLite snapshot tool and a sample systemd timer. The application does **not** start its own scheduler: scheduled backups only occur after the operating-system timer is installed and configured.

## What the tool does

- Uses SQLite's online backup API to create a consistent database snapshot, including while the app is running.
- Verifies SQLite integrity and validates the stored VIRTUE WISE model before publishing the snapshot.
- Flushes the completed staging database before atomic publication and, on POSIX, flushes the containing directory after the rename so the published directory entry is committed as far as the host filesystem supports.
- Creates new backup directories with POSIX mode `0700` and pre-creates backup/restore staging files with mode `0600` before SQLite writes to them; published snapshots are also restricted to owner read/write permissions where supported.
- Does not change permissions on an existing custom backup directory. Ensure custom directories are private; Windows relies on inherited filesystem ACLs.
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

The default backup directory is a `backups` folder beside the configured database. For better recovery, configure a dedicated directory on a different volume from the live database. Backups contain the complete project and should be treated as sensitive. The tool creates a new backup directory with POSIX mode `0700` and staging/snapshot files with `0600`; existing custom directories are not changed and must be protected by the operator. Windows uses host filesystem ACLs.

## Run a backup manually

From the repository root with the project environment activated:

```bash
python -m app.backup create
python -m app.backup verify /var/backups/virtue-wise/virtue-wise-YYYYMMDDTHHMMSSffffffZ.sqlite3
python -m app.backup prune --keep 30
```

The `create` command creates a snapshot, verifies it, and prunes older snapshots. It fails rather than creating an empty backup when the live database does not exist yet.

## Check backup freshness for monitoring

Run the health check after enabling the daily timer and from an external/local monitoring mechanism:

```bash
python -m app.backup check --max-age-hours 26
```

The command selects the newest managed snapshot by filesystem modification time, rejects a missing or over-age snapshot, and verifies the selected SQLite database and VIRTUE WISE model payload. It exits with status 0 only when the newest snapshot is both fresh and valid; missing, stale, future-dated, or corrupt newest snapshots return a non-zero status. A corrupt newest snapshot is not hidden by falling back to an older valid one. The default freshness window is 26 hours to allow for the daily timer's randomized delay and ordinary scheduling variance; set a stricter or looser threshold to match the actual schedule and recovery-point objective.

The sample timer does not send alerts. Configure the host's monitoring/alerting system to run this command and notify an operator on a non-zero exit. A successful check proves only that the newest local snapshot currently exists, is within the configured age, and passes validation; it does not prove off-device replication, encryption, host integrity, or a successful restore. Continue periodic restore drills.

After deleting project data, remove all managed local snapshots with `python -m app.backup purge --yes`. This is irreversible and deletes only `virtue-wise-*.sqlite3` files in the configured backup directory; it does not delete JSON exports, off-device copies, or backups on other hosts. Use it only after confirming no restore point is still needed.

## Schedule daily backups with systemd

The sample files are in `deploy/systemd/`. They assume:

- the service account is named `virtuewise`;
- the application checkout is at `/opt/virtue-wise`;
- its virtual environment is at `/opt/virtue-wise/.venv`;
- the database and backup directories are `/var/lib/virtue-wise` and `/var/backups/virtue-wise`.

Adjust the service file's user, group, working directory, interpreter, and writable paths to match the host. The sample oneshot unit is deliberately isolated: it has no network namespace access, no device access, no Linux capabilities, a read-only system view, and write access only to the database and backup directories. Keep `PrivateNetwork=true` and `RestrictAddressFamilies=AF_UNIX` for this file-only backup task; do not add network access unless a separately reviewed backup transport design requires it. The unit uses modern systemd sandbox directives, so validate compatibility on the target host with `systemd-analyze verify` before enabling it. Create the directories and environment file:

```bash
sudo install -d -o virtuewise -g virtuewise -m 0700 /var/lib/virtue-wise /var/backups/virtue-wise
sudo install -d -o root -g root -m 0755 /etc/virtue-wise
sudoedit /etc/virtue-wise/backup.env
```

Put the three environment variables shown above in `/etc/virtue-wise/backup.env`, then install and enable the timer:

```bash
sudo install -m 0644 deploy/systemd/virtue-wise-backup.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/virtue-wise-backup.timer /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/virtue-wise-backup.service /etc/systemd/system/virtue-wise-backup.timer
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

## Schedule backups on Windows Task Scheduler

For a Windows-first local installation, use Windows Task Scheduler under the same Windows account that owns the project data. The application does not install tasks automatically.

1. Confirm the project has been run at least once and the database exists at `<repository>\\data\\virtue-wise.sqlite3`. Create the backup directory if desired. The default is `<repository>\\data\\backups`.
2. Open **Task Scheduler** and choose **Create Task** (not Basic Task).
3. On **General**, name it `VIRTUE WISE Daily Backup`, select the Windows account used for local development, and choose **Run only when user is logged on**. Do not select elevated privileges unless the chosen data paths genuinely require them.
4. On **Triggers**, create a daily trigger at a suitable time (for example, 02:15).
5. On **Actions**, choose **Start a program**:
   - Program/script: `<repository>\\.venv\\Scripts\\python.exe`
   - Add arguments: `-m app.backup create`
   - Start in: `<repository>` (the directory containing `app\\` and `pyproject.toml`)
6. On **Settings**, enable **Run task as soon as possible after a scheduled start is missed**, and set **If the task is already running** to **Do not start a new instance**. Consider a reasonable execution time limit, such as 30 minutes.
7. Save the task, right-click it, choose **Run**, and confirm a new verified snapshot appears in the configured backup directory. Inspect **Last Run Result** and **History** after the first run.

The task inherits the selected Windows account's filesystem permissions. Ensure the database, JSON exports, and backup directory ACLs grant access only to the intended account and administrators. Avoid shared/network drives and do not run the task as a broadly privileged service account. If custom paths are required, set `VIRTUE_WISE_DB`, `VIRTUE_WISE_BACKUP_DIR`, and `VIRTUE_WISE_BACKUP_RETENTION_COUNT` consistently for the scheduled task's account before relying on it; verify the effective paths by inspecting the resulting snapshot location.

To check the latest recovery point, create a second Task Scheduler task named `VIRTUE WISE Backup Health Check` with a daily trigger later than the backup (for example, 03:00), the same account and **Start in** directory, and this action:

- Program/script: `<repository>\\.venv\\Scripts\\python.exe`
- Add arguments: `-m app.backup check --max-age-hours 26`
- Start in: `<repository>`

Review its **Last Run Result** and **History**. A non-zero result indicates that the newest managed backup is missing, stale, future-dated, or corrupt. Task Scheduler history is not a notification service; configure a separate alert if unattended failure notification is required. The health check verifies only the newest local snapshot and does not replace a restore drill or protected off-device copy.

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

Restore is staged and verified before replacing the live database. The staging database is flushed before replacement and the containing directory is flushed on POSIX after the atomic rename. If a live database exists, the tool creates a pre-restore snapshot first. Keep the original backup unchanged until recovery has been checked. Directory-entry durability depends on the host filesystem and storage device honoring flush requests; this is not a substitute for a restore drill or a separate protected backup copy.

## Recovery objectives and limitations

With the supplied daily timer installed and completing successfully, the intended recovery-point objective is up to 24 hours of changes. This is an operational target, not a guarantee; verify timer execution and backup files. Recovery time has not yet been measured, so no RTO is claimed. Periodically perform a restore drill on a disposable database and record its duration and result.

The backup files are not encrypted by VIRTUE WISE. Host compromise, disk loss, ransomware, or a user who can read the backup directory can expose or destroy them. Use OS-level encryption, restrictive ownership, and a separate protected copy. The systemd sample is an installation template and must be adapted and reviewed for the actual host.
