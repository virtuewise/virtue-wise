"""Small SQLite-backed store; no network service or telemetry is used."""

import os
import sqlite3
from pathlib import Path

from app.models import ProjectModel, now_utc

DEFAULT_DB_PATH = Path("data/virtue-wise.sqlite3")


def database_path() -> Path:
    """Resolve the database path, allowing tests and users to choose a location."""
    return Path(os.environ.get("VIRTUE_WISE_DB", str(DEFAULT_DB_PATH)))


def _connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS project_model "
        "(singleton INTEGER PRIMARY KEY CHECK (singleton = 1), payload TEXT NOT NULL)"
    )
    return connection


def load_model() -> ProjectModel:
    """Load the saved model or return an empty model on first run."""
    with _connect() as connection:
        row = connection.execute(
            "SELECT payload FROM project_model WHERE singleton = 1"
        ).fetchone()
    if row is None:
        return ProjectModel()
    return ProjectModel.model_validate_json(row[0])


def save_model(model: ProjectModel) -> ProjectModel:
    """Persist a validated model as a single atomic SQLite row."""
    model.updated_at = now_utc()
    payload = model.model_dump_json()
    with _connect() as connection:
        connection.execute(
            "INSERT INTO project_model(singleton, payload) VALUES (1, ?) "
            "ON CONFLICT(singleton) DO UPDATE SET payload = excluded.payload",
            (payload,),
        )
    return model


def delete_model() -> None:
    """Delete the local model while keeping the empty database ready for reuse."""
    with _connect() as connection:
        connection.execute("DELETE FROM project_model WHERE singleton = 1")
