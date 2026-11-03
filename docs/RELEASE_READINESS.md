# Release, compatibility, and recovery policy

**Status:** operating procedure for the local prototype, not a production-readiness claim. The security gate in [issue #7](https://github.com/virtuewise/virtue-wise/issues/7) must be satisfied before any network deployment.

## Compatibility contract

- The exported JSON model contains `schema_version`; the current supported version is **1**.
- The current application validates version 1 and rejects unsupported versions. There is no migration framework or compatibility promise between arbitrary revisions yet.
- Do not silently rewrite or discard fields during import. An import must validate fully before replacing the saved model.
- Any future schema change must include: a written reason grounded in a real workflow, an explicit versioning decision, representative old/new fixtures, migration and rollback tests if migration is introduced, and documentation of the supported upgrade path.
- Until a migration is implemented and tested, treat a new incompatible schema as a deliberate breaking change. Keep an untouched export from the prior version before upgrading.
- Do not promise API stability: the API and data format remain prototype interfaces.

## Backup procedure

Use `python -m app.backup create` to make a consistent SQLite snapshot, verify its integrity and model payload, and prune older snapshots. The default retention is 30 snapshots. Set `VIRTUE_WISE_BACKUP_DIR` to a directory on a separate volume and `VIRTUE_WISE_BACKUP_RETENTION_COUNT` to change the policy. See [backup operations](BACKUP_OPERATIONS.md) for configuration and the sample daily systemd timer.

The application does not start its own scheduler. Automated daily backups only occur after the operator installs and enables the supplied systemd timer (or configures an equivalent OS scheduler). Verify timer execution and run `python -m app.backup verify PATH` before relying on a snapshot. The tool restricts backup file permissions but does not encrypt backups; use OS-level disk encryption and a separate protected copy. After a project deletion, use `python -m app.backup purge --yes` only when all local restore points should also be destroyed; this does not remove off-device copies. Keep JSON export as a portable secondary recovery option.

## Recovery and restore procedure

1. Stop the application before replacing its SQLite database file.
2. Verify the selected snapshot with `python -m app.backup verify PATH`.
3. Restore it with `python -m app.backup restore PATH --yes`. If a live database exists, the tool first creates a pre-restore snapshot.
4. Restart the application and verify the project title/goal, record counts, statement text and source fields, hypothesis evidence links, review states, and scenarios.
5. Preserve the original snapshot and create a fresh backup after successful recovery.
6. If recovery fails, keep the original backup unchanged and investigate using a copy; do not experiment on the only backup.

The automated suite exercises both JSON export → delete → import recovery and SQLite snapshot → verify → restore recovery. These are regression checks, not substitutes for periodically restoring a scheduled backup on a disposable instance.

For database-level recovery, stop the application and use `python -m app.backup restore PATH --yes`; the tool verifies the source snapshot and creates a pre-restore backup before replacement. JSON export/import remains the portable recovery route. With the supplied daily scheduler installed and running successfully, the intended recovery-point objective is up to 24 hours; this is not guaranteed until the timer is monitored. Recovery time has not been measured, so no RTO is claimed.

## Release checklist

- [ ] Confirm the intended release scope and review the changelog/release notes.
- [ ] Ensure all changes are in reviewed pull requests; no direct unreviewed release edits.
- [ ] Confirm CI passes on the final release commit, including all configured Python versions and documentation checks.
- [ ] Run the clean-checkout setup and automated test commands documented in the README.
- [ ] Validate import/export against `examples/demo-project.json` and a real version 1 export fixture.
- [ ] Review dependencies, workflow permissions, secrets exposure, and known vulnerabilities.
- [ ] Complete and record the manual workflow and accessibility checklist in [ACCEPTANCE.md](ACCEPTANCE.md) when a browser-testing session is available.
- [ ] Install the daily backup scheduler, verify a successful recent snapshot, and complete a restore drill on a disposable database.
- [ ] Verify that documentation accurately states the deployment boundary and open security risks.
- [ ] For any network deployment, obtain explicit approval of security issue #7; ordinary CI passing is not sufficient.
- [ ] Tag the exact reviewed commit, publish concise release notes including schema/API compatibility, known limitations, backup instructions, and rollback steps.
- [ ] After release, verify the released artifact/commit and keep the previous known-good version and backup available.

## Concurrency contract (current prototype)

Record-level statement, hypothesis, review, and scenario mutations now run inside a SQLite `BEGIN IMMEDIATE` transaction. The transaction acquires the database write reservation before loading the current model, applies the mutation, validates the full model, and commits the single-row update; exceptions roll back. SQLite's busy timeout is 10 seconds. If a competing writer holds the lock beyond that limit, the API returns HTTP 503 with a retry message. The existing process-local lock remains as an additional guard within one server process.

The database transaction coordinates independent processes that share the same local SQLite file. It does not make SQLite suitable for a multi-host/network-filesystem deployment. Explicit full-model replacement (`PUT /api/model`) and import now require the strong ETag returned by `GET /api/model` in an `If-Match` header. The store compares the revision inside the same SQLite write transaction; missing preconditions return HTTP 428 and stale revisions return HTTP 412. The browser client tracks the current revision and supplies it for replacement/import. This protects against stale tabs and stale imports, but it does not make SQLite suitable for multi-host/network-filesystem deployment. Keep the database on a local filesystem, retain the documented local-only deployment boundary, and do not claim multi-host or distributed operation. Regression tests exercise concurrent independent SQLite connections and rollback on callback failure.

## Rollback

For the local prototype, rollback means stopping the app, preserving the current database and exports, checking out the last known-good code revision, and restoring a verified version 1 JSON export if the model was changed incompatibly. Test this procedure on copies before relying on it. Do not assume that downgrading code automatically downgrades or migrates stored data.

## Release decision

The project is **not ready for network deployment** while issue #7 is open. The manual usability/accessibility checks are also outstanding. Backup/verify/restore tooling and a sample scheduler are implemented, but the operator must install the scheduler, protect backups with host-level encryption, and complete a restore drill. Migrations, network security controls, and manual browser checks remain incomplete.
