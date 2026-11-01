# Prototype architecture

## Current implementation

The prototype is a single-process FastAPI application serving a static HTML/CSS/JavaScript interface. Pydantic models define the versioned JSON boundary. SQLite stores one project model in a single row, which keeps the first iteration easy to inspect and back up.

- `app/models.py` defines the project, statements, hypotheses, and scenario records.
- `app/store.py` owns the small SQLite persistence boundary.
- `app/main.py` exposes the UI, health check, model API, review endpoint, export, and deletion.
- `app/static/` contains the browser interface.
- `tests/` exercises core API behavior and provenance rules.

## Data and trust boundaries

Statements represent user-provided inputs. Hypotheses are separate records with explicit uncertainty and review status. Hypotheses must reference existing statement IDs when evidence links are supplied. Accepting a hypothesis records a user review decision; it does not alter or promote the source statements.

The application does not call an external model, send telemetry, connect to user accounts, or perform external actions. The SQLite file is local to the server process by default at `data/virtue-wise.sqlite3`. Anyone with access to that machine and file may be able to read its contents; this is not an encrypted vault or multi-user security boundary.

## Run locally

Use Python 3.12 or newer:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. API documentation is available at `http://127.0.0.1:8000/docs`. Set `VIRTUE_WISE_DB` to an alternate SQLite file path if needed.

## Known limitations

- This is an early single-project prototype, not a multi-user application.
- Scenarios are represented in the schema but are not yet editable in the interface.
- JSON export is implemented; JSON import and schema migration tooling are not yet implemented.
- There is no authentication, encryption-at-rest layer, backup manager, or concurrency coordination for multiple application workers.
- The server should be bound to localhost for personal use. Do not expose it to an untrusted network.
