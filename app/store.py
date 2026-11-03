"""Small SQLite-backed store; no network service or telemetry is used."""

import hashlib
import os
import sqlite3
from collections.abc import Callable
from pathlib import Path

from app.models import ProjectModel, now_utc

DEFAULT_DB_PATH = Path("data/virtue-wise.sqlite3")
SQLITE_BUSY_TIMEOUT_SECONDS = 10


class StoreBusyError(RuntimeError):
    """Raised when another process holds SQLite's write lock too long."""


class StoreConflictError(RuntimeError):
    """Raised when a full-model replacement is based on a stale revision."""


def _raise_if_database_busy(error: sqlite3.OperationalError) -> None:
    message = str(error).lower()
    if "locked" in message or "busy" in message:
        raise StoreBusyError("The project database is busy. Retry the request.") from error


def database_path() -> Path:
    """Resolve the database path, allowing tests and users to choose a location."""
    return Path(os.environ.get("VIRTUE_WISE_DB", str(DEFAULT_DB_PATH)))


def _prepare_database_file(path: Path) -> None:
    """Create the database with private POSIX permissions and repair existing mode bits.

    Newly created parent directories use mode 0700 and the database file uses
    0600. Existing parent directories are not chmodded because callers may
    intentionally place a custom database in a shared directory; operators
    must ensure that directory and its backups are appropriately protected.
    Windows access control remains governed by inherited filesystem ACLs.
    """
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "posix":
        return

    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        if path.is_symlink() or not path.is_file():
            raise OSError(
                "The VIRTUE WISE database path must be a regular file, not a symlink."
            ) from None
        os.chmod(path, 0o600)
    else:
        os.close(descriptor)


def _connect() -> sqlite3.Connection:
    path = database_path()
    _prepare_database_file(path)
    connection = sqlite3.connect(path, timeout=SQLITE_BUSY_TIMEOUT_SECONDS)
    try:
        connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_SECONDS * 1000}")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS project_model "
            "(singleton INTEGER PRIMARY KEY CHECK (singleton = 1), payload TEXT NOT NULL)"
        )
        return connection
    except Exception:
        connection.close()
        raise


def load_model() -> ProjectModel:
    """Load the saved model or return an empty model on first run."""
    connection = _connect()
    try:
        row = connection.execute("SELECT payload FROM project_model WHERE singleton = 1").fetchone()
    finally:
        connection.close()
    if row is None:
        return ProjectModel()
    return ProjectModel.model_validate_json(row[0])


def check_database() -> None:
    """Check SQLite integrity and validate the persisted model without writing it."""
    connection = _connect()
    try:
        integrity = connection.execute("PRAGMA quick_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise sqlite3.DatabaseError("Project database integrity check failed.")
        row = connection.execute("SELECT payload FROM project_model WHERE singleton = 1").fetchone()
        if row is not None:
            ProjectModel.model_validate_json(row[0])
    finally:
        connection.close()


def _revision_for_payload(payload: str) -> str:
    """Return a deterministic strong revision token for one stored payload."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def revision_for_model(model: ProjectModel) -> str:
    """Return the strong revision token represented by a persisted model."""
    return _revision_for_payload(model.model_dump_json())


def load_model_with_revision() -> tuple[ProjectModel, str]:
    """Load the model and its compare-and-swap revision.

    The revision hashes the exact stored JSON payload rather than relying on
    wall-clock timestamp resolution, so distinct writes cannot collide merely
    because they occur within the same timestamp tick.
    """
    connection = _connect()
    try:
        row = connection.execute("SELECT payload FROM project_model WHERE singleton = 1").fetchone()
    finally:
        connection.close()
    if row is None:
        return ProjectModel(), "empty"
    payload = row[0]
    model = ProjectModel.model_validate_json(payload)
    return model, _revision_for_payload(payload)


def _write_model(connection: sqlite3.Connection, model: ProjectModel) -> None:
    """Write one validated project model inside the caller's transaction."""
    model.updated_at = now_utc()
    connection.execute(
        "INSERT INTO project_model(singleton, payload) VALUES (1, ?) "
        "ON CONFLICT(singleton) DO UPDATE SET payload = excluded.payload",
        (model.model_dump_json(),),
    )


def _run_write_transaction(connection: sqlite3.Connection, operation):
    """Run an operation in one bounded SQLite write transaction."""
    try:
        connection.execute("BEGIN IMMEDIATE")
        result = operation()
        connection.commit()
        return result
    except sqlite3.OperationalError as exc:
        connection.rollback()
        _raise_if_database_busy(exc)
        raise
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def save_model(model: ProjectModel) -> ProjectModel:
    """Atomically replace the saved model (used by explicit replace/import operations)."""
    validated = ProjectModel.model_validate(model.model_dump(mode="python"))
    connection = _connect()

    def write():
        _write_model(connection, validated)
        return validated

    return _run_write_transaction(connection, write)


def save_model_if_current(model: ProjectModel, expected_revision: str) -> ProjectModel:
    """Replace the model only if its current revision still matches the caller."""
    validated = ProjectModel.model_validate(model.model_dump(mode="python"))
    connection = _connect()

    def write():
        row = connection.execute("SELECT payload FROM project_model WHERE singleton = 1").fetchone()
        current_revision = "empty" if row is None else _revision_for_payload(row[0])
        if current_revision != expected_revision:
            raise StoreConflictError(
                "The project changed since it was loaded. Reload before replacing it."
            )
        _write_model(connection, validated)
        return validated

    return _run_write_transaction(connection, write)


def mutate_model(mutator: Callable[[ProjectModel], None]) -> ProjectModel:
    """Read, validate, mutate, and write under a cross-process SQLite write lock.

    BEGIN IMMEDIATE acquires SQLite's reserved write lock before reading the
    current model. Independent workers/processes therefore serialize their
    read-modify-write cycles instead of overwriting one another's updates.
    """
    connection = _connect()

    def update():
        row = connection.execute("SELECT payload FROM project_model WHERE singleton = 1").fetchone()
        model = ProjectModel() if row is None else ProjectModel.model_validate_json(row[0])
        mutator(model)
        validated = ProjectModel.model_validate(model.model_dump(mode="python"))
        _write_model(connection, validated)
        return validated

    return _run_write_transaction(connection, update)


def delete_model() -> None:
    """Delete the local model transactionally while keeping the database ready for reuse."""
    connection = _connect()

    def delete():
        connection.execute("DELETE FROM project_model WHERE singleton = 1")

    _run_write_transaction(connection, delete)
