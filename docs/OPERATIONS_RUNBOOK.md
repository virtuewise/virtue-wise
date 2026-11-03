# Local operations and incident-response runbook

**Status:** operating guidance for the supported single-user, loopback-only prototype. This runbook does not authorize network deployment or sensitive-data use. Keep [security release gate #7](https://github.com/virtuewise/virtue-wise/issues/7) open until the actual target deployment has been independently reviewed and approved.

## 1. Data and handling

The SQLite database, JSON exports, and SQLite snapshots contain the complete project model: project text, statements, source labels and excerpts, hypotheses, review notes, scenarios, and assumptions. Treat every copy as sensitive, even though the current supported workflow requires fictional/non-sensitive data.

- Run the application under a dedicated operating-system account where practical.
- Restrict the database, export, and backup directories to that account.
- Do not place the database on a network filesystem or share it between hosts.
- Do not send project files to issue trackers, chat, logs, or public support channels.
- The application does not encrypt the database or backup files. Filesystem permissions are not protection against a compromised host or another process running as the same user.

## 2. Health and storage readiness

- `GET /health` is a liveness response. It confirms that the HTTP application process can answer; it does not inspect the database.
- `GET /ready` runs a SQLite quick integrity check and validates the persisted VIRTUE WISE model payload. It returns a generic HTTP 503 if storage is busy, unreadable, corrupt, or contains an invalid model. It does not expose database paths or stored project content and is marked `Cache-Control: no-store`.
- After startup, restore, or an unexpected storage error, check both endpoints. A healthy liveness response with a failed readiness response means the process is running but the project store should not be treated as available. Preserve the database and investigate before attempting repair.

These endpoints are operational signals, not authentication or network-deployment controls. Keep the application loopback-only.

## 2. Deletion and retention

Deleting the active model and deleting its recovery copies are separate operations.

### Delete the active model

1. Confirm the intended project and that deletion is deliberate.
2. If retention is required, create and verify a backup first using the procedure in [backup operations](BACKUP_OPERATIONS.md).
3. Use the application's delete-model action (API: `DELETE /api/model`).
4. Reload the workspace and confirm that the model is empty.

This removes the active model row. It does **not** remove SQLite snapshots, JSON exports, filesystem snapshots, or copies stored elsewhere.

### Purge managed local snapshots

Only when all managed local restore points must also be destroyed:

1. Stop scheduled backup activity for the application.
2. Confirm `VIRTUE_WISE_BACKUP_DIR` points to the intended directory.
3. Inspect that directory and identify any files that must be retained or investigated.
4. Run `python -m app.backup purge --yes` with the same environment configuration used by the application.
5. Verify that managed `virtue-wise-*.sqlite3` snapshots are gone.
6. Resume scheduling only if future backups are still wanted.

The purge command does not delete JSON exports, off-device copies, OS-level snapshots, or backups in other locations. Remove those through their respective storage systems and retention policies. Do not claim secure erasure from ordinary file deletion; SSD wear levelling, snapshots, and filesystem journaling can retain blocks.

## 3. Schema changes and migrations

The current model schema is version 1. There is no migration framework and no automatic compatibility guarantee.

Until a migration is implemented and tested:

- Reject unsupported schema versions; do not silently discard or rewrite unknown fields.
- Before an upgrade, create a verified SQLite snapshot and a JSON export.
- Read the release notes and identify whether the release changes the model schema or API behavior.
- Do not deploy an incompatible schema change to a database containing data that cannot be reconstructed.
- If a migration is introduced, require a reviewed migration plan, representative v1 and target-version fixtures, validation before and after migration, rollback testing against a copy, and an explicit supported upgrade path.
- Preserve the pre-migration backup unchanged until post-upgrade verification is complete.

For recovery, stop the application, verify the selected snapshot, restore it using [the documented restore procedure](BACKUP_OPERATIONS.md), restart the application, and verify project identity, record counts, evidence links, review states, and scenarios. Test restore procedures on a disposable copy before relying on them.

## 4. Patching and dependency maintenance

For each source update:

1. Review the change and its dependency updates; do not install unreviewed code into a data-bearing environment.
2. Read the release notes and compatibility notes before upgrading.
3. Back up the database and verify the snapshot.
4. Install from the reviewed source in a controlled environment using the documented Python version.
5. Run formatting, lint, unit, API, and browser acceptance checks available for that revision.
6. Test startup, read/write, import/export, and restore against a disposable database.
7. Keep the prior known-good code revision and verified backup available until the update is accepted.

The current dependency declarations use version ranges rather than a fully reproducible production lockfile. Dependency vulnerability scanning, patch ownership, and release cadence must be established for any future network deployment; ordinary CI is not a substitute for that review.

## 5. Incident response for the local prototype

If unexpected access, data disclosure, corruption, or suspicious modification is suspected:

1. **Contain:** stop the application and disable any scheduled job or process that could continue modifying the database. Do not expose the service to a network.
2. **Preserve:** avoid editing or deleting the affected database, exports, logs, or backups. Make access-restricted copies where safe and record timestamps and the affected code revision.
3. **Assess:** identify which data copies may be affected, whether the host or operating-system account may be compromised, and whether backups are trustworthy. Do not assume that a clean application restart resolves host compromise.
4. **Recover:** use a verified pre-incident backup only after preserving the affected state. Restore to a disposable location first and validate the recovered model.
5. **Patch and verify:** identify the cause, review the relevant code/dependencies/configuration, apply a reviewed fix, and rerun the relevant test and acceptance suites before resuming local use.
6. **Report:** disclose security vulnerabilities privately using the process in [SECURITY.md](../SECURITY.md). Do not publish secrets, personal data, project exports, or exploit details in public issues.

For a suspected compromised host, use the host's incident-response process and trusted recovery media; do not treat application-level restore as sufficient remediation.

## 6. Operational evidence to record

For every backup restore drill or operational change, record:

- Date, operator, application commit, Python version, and host/filesystem type.
- Database and backup locations (record paths, not secrets or project contents).
- Backup verification result and snapshot timestamp.
- Restore start/end time, outcome, and post-restore integrity checks.
- Any data loss window observed and measured recovery duration.
- Patch/release identifier, tests executed, failures, and rollback result.

No recovery-time objective is currently claimed. A recovery-point objective of up to 24 hours is only an intended target when the sample daily scheduler has been installed, monitored, and is succeeding.

## 7. Explicit boundary

This runbook is for local operations only. It does not implement authentication, authorization, session security, CSRF tokens, encryption at rest, ingress controls, global concurrency limits, host-level backup encryption, or independent security review. Those remain release blockers in issue #7. Do not use this document as a deployment approval.
