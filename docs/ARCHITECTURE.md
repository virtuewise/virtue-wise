# Prototype architecture

## Current implementation

VIRTUE WISE is a local FastAPI application serving a static HTML/CSS/JavaScript interface. Pydantic v2 validates API payloads and the versioned JSON model. SQLite stores one project model in a single row. Record-level read-modify-write operations use SQLite write transactions, so independent processes sharing the same local database serialize their mutations.

- `app/models.py` defines project, statement, hypothesis, and scenario records and validates IDs and evidence references.
- `app/store.py` owns SQLite persistence.
- `app/backup.py` creates, verifies, prunes, and restores local SQLite snapshots; `deploy/systemd/` contains a sample daily backup timer.
- `app/main.py` exposes the interface, health endpoint, model API, record editing, hypothesis review, scenario operations, JSON import/export, and deletion; it also applies browser-origin checks and a loopback Host allowlist.
  All `/api/` responses use `Cache-Control: no-store` because they may contain complete project content; this is not an authentication or authorization control.
- `app/static/` contains the browser interface and interaction logic.
- `tests/` exercises API behavior, provenance rules, scenario operations, import validation, and the documented demo fixture.
- `examples/demo-project.json` provides a fictional model for local exploration and acceptance testing.
- `docs/ACCEPTANCE.md` defines a manual workflow and accessibility checklist; those manual checks remain to be performed.

## Implemented workflows

- Create and edit the project title and goal.
- Add, edit, and delete sourced statements. A statement linked to a hypothesis cannot be deleted until the evidence link is removed.
- Create and edit hypotheses, link evidence statements, set qualitative uncertainty, and record an explicit accept/revise/reject review.
- Create, edit, delete, and compare named scenarios using visible assumptions and expected outcomes. Comparisons are descriptive, not scored predictions.
- Export the model as JSON and import a JSON file after schema and cross-reference validation.
- Delete the saved model.

## Data and trust boundaries

Statements represent user-provided inputs. Hypotheses remain separate records with explicit uncertainty and review status. Review decisions do not promote hypotheses into verified facts or alter source statements. Editing a linked statement or materially changing a hypothesis resets that hypothesis to proposed and clears its prior review note, so an earlier decision is not silently carried over to changed content. Imported models must use the supported schema version, unique record IDs, and valid evidence references.

The application does not call an external model, send telemetry, connect to user accounts, or perform external actions. The SQLite file is local to the server process by default at `data/virtue-wise.sqlite3`. Anyone with access to that machine and file may be able to read its contents; this is not an encrypted vault or multi-user security boundary. On POSIX systems, a newly created database directory uses mode `0700`, and the live SQLite file is created/repaired to mode `0600`. Existing custom parent directories are not changed; operators must ensure those directories and any exports/backups are private. Windows relies on filesystem ACLs. This is defense in depth, not encryption or protection from the same OS account.

## Run locally

Use Python 3.12 or newer:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. API documentation is available at <http://127.0.0.1:8000/docs>. Set `VIRTUE_WISE_DB` to an alternate SQLite file path if needed.

## Known limitations

- This is a single-project prototype intended for local, trusted use, not a multi-user application.
- Scenarios are qualitative; the application does not estimate probabilities, causal effects, or future outcomes.
- JSON import supports the current schema version only; there is no migration tooling.
- There is no authentication, session management, authorization, encryption-at-rest layer, or session-bound CSRF token. A local backup CLI and sample systemd timer are provided, but the operator must install the timer; the app does not schedule backups itself and does not encrypt backup files. Basic Origin/Referer, Fetch Metadata, and Host checks are defense in depth only; missing browser origin metadata is allowed for non-browser API clients. See [the authentication design](AUTHENTICATION_DESIGN.md).
- Record-level statement, hypothesis, review, and scenario mutations acquire a SQLite `BEGIN IMMEDIATE` write transaction before reading the model, validate the resulting model, and commit or roll back as one unit. SQLite waits up to 10 seconds for a competing writer; an exhausted lock wait returns HTTP 503. A process-local request lock remains as an additional same-process guard. Full-model replacement/import use the model's `updated_at` as a strong ETag and require `If-Match`; missing preconditions return HTTP 428 and stale revisions return HTTP 412. Use one local database file on a local filesystem; multi-host/network-filesystem operation is unsupported. See [release and recovery](RELEASE_READINESS.md).
- JSON imports are limited to 2 MB of file data, with a 2.1 MB application-level request-body guard that counts incoming ASGI chunks even when Content-Length is absent. Oversized requests are rejected before multipart parsing. UTF-8, duplicate object keys, non-standard numeric constants, and schema failures are rejected before persistence. Request-validation errors omit submitted values. The app applies a 30-second import body-read timeout and a two-request per-process import semaphore (one-second slot wait), in addition to the byte limit. These are process-local application controls, not global ingress limits; server/reverse-proxy body, connection, and timeout controls remain required. See [import security notes](IMPORT_SECURITY.md).
- Editing uses native HTML dialog forms with associated labels, required-field validation, save/cancel controls, and visible save-error feedback. Manual keyboard and screen-reader verification remains outstanding.
- The server should be bound to localhost. Do not expose it to an untrusted network or enter sensitive data.
