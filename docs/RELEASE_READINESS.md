# Release, compatibility, and recovery policy

**Status:** operating procedure for the local prototype, not a production-readiness claim. The security gate in [issue #7](https://github.com/virtuewise/virtue-wise/issues/7) must be satisfied before any network deployment.

## Compatibility contract

- The exported JSON model contains `schema_version`; the current supported version is **1**.
- The current application validates version 1 and rejects unsupported versions. There is no migration framework or compatibility promise between arbitrary revisions yet.
- Do not silently rewrite or discard fields during import. An import must validate fully before replacing the saved model.
- Any future schema change must include: a written reason grounded in a real workflow, an explicit versioning decision, representative old/new fixtures, migration and rollback tests if migration is introduced, and documentation of the supported upgrade path.
- Until a migration is implemented and tested, treat a new incompatible schema as a deliberate breaking change. Keep an untouched export from the prior version before upgrading.
- Do not promise API stability: the API and data format remain prototype interfaces.

## Backup procedure (current manual capability)

1. Use the application's **Export JSON** action to download `virtue-wise-model.json`.
2. Store the export in a user-controlled location separate from the working application/database directory. Protect it with the operating system's file permissions; exports contain the complete project content.
3. Use a dated filename and retain more than one generation when the data matters, for example `virtue-wise-model-YYYY-MM-DD.json`.
4. Before a risky edit, application update, or import, export the current model first.
5. Do not treat a successful download as a verified backup until the file exists, has a plausible non-zero size, and can be imported into a disposable test instance.

There is currently no automatic backup scheduler, retention policy, encrypted backup manager, or restore-point UI. These are limitations, not implied features.

## Recovery and restore procedure

1. Preserve a copy of the current export and do not overwrite the only known-good backup.
2. Start a clean instance with a separate `VIRTUE_WISE_DB` path for recovery testing.
3. Import the backup JSON. The current app supports schema version 1 only; unsupported or malformed files should be rejected without replacing the current model.
4. Verify the project title/goal, record counts, statement text and source fields, hypothesis evidence links, review states, and scenarios against the expected project.
5. If verification succeeds, preserve the original export and import the verified file into the intended instance. Export again after restoration.
6. If recovery fails, keep the original backup unchanged and investigate using a copy; do not experiment on the only backup.

The automated suite also exercises an export → delete → import restore cycle and verifies that project identity, statement IDs, evidence links, review status, and scenario content survive. This is a regression check, not a substitute for testing a downloaded backup in a disposable clean instance.

For database-level recovery, stop the application and preserve a copy of the database and any SQLite sidecar files before investigation. JSON export/import is the intended portable recovery route for the current prototype. No recovery-time or recovery-point objective is promised.

## Release checklist

- [ ] Confirm the intended release scope and review the changelog/release notes.
- [ ] Ensure all changes are in reviewed pull requests; no direct unreviewed release edits.
- [ ] Confirm CI passes on the final release commit, including all configured Python versions and documentation checks.
- [ ] Run the clean-checkout setup and automated test commands documented in the README.
- [ ] Validate import/export against `examples/demo-project.json` and a real version 1 export fixture.
- [ ] Review dependencies, workflow permissions, secrets exposure, and known vulnerabilities.
- [ ] Complete and record the manual workflow and accessibility checklist in [ACCEPTANCE.md](ACCEPTANCE.md) when a browser-testing session is available.
- [ ] Confirm backup and restore on a disposable database and record the result.
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

The project is **not ready for network deployment** while issue #7 is open. The manual usability/accessibility checks are also outstanding. This policy defines steps to follow; it does not claim that backups, migrations, automated recovery, security controls, or manual browser checks have already been implemented.
