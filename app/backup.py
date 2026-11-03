"""Local SQLite backup, verification, retention, and restore commands."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.models import ProjectModel
from app.store import database_path

BACKUP_PREFIX = "virtue-wise-"
DEFAULT_RETENTION_COUNT = 30


def backup_directory() -> Path:
    """Resolve the backup directory independently from the live database."""
    default = database_path().parent / "backups"
    return Path(os.environ.get("VIRTUE_WISE_BACKUP_DIR", str(default)))


def retention_count() -> int:
    """Return the configured snapshot count, rejecting unsafe values."""
    value = int(os.environ.get("VIRTUE_WISE_BACKUP_RETENTION_COUNT", DEFAULT_RETENTION_COUNT))
    if value < 1:
        raise ValueError("VIRTUE_WISE_BACKUP_RETENTION_COUNT must be at least 1.")
    return value


def _verify_database(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Backup file does not exist: {path}")
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = None
    try:
        connection = sqlite3.connect(uri, uri=True)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise ValueError(f"SQLite integrity check failed for {path}.")
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        if "project_model" not in tables:
            raise ValueError(f"Backup does not contain a project_model table: {path}")
        row = connection.execute("SELECT payload FROM project_model WHERE singleton = 1").fetchone()
        if row is not None:
            ProjectModel.model_validate_json(row[0])
    except (sqlite3.DatabaseError, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Backup is not a readable VIRTUE WISE database: {path}") from exc
    finally:
        if connection is not None:
            connection.close()


def verify_backup(path: str | Path) -> Path:
    """Check SQLite integrity and validate the saved VIRTUE WISE model."""
    resolved = Path(path).expanduser().resolve()
    _verify_database(resolved)
    return resolved


def prune_backups(
    keep: int = DEFAULT_RETENTION_COUNT, protect: tuple[Path, ...] = ()
) -> list[Path]:
    """Keep the newest configured number of managed backup snapshots."""
    if keep < 1:
        raise ValueError("Backup retention count must be at least 1.")
    directory = backup_directory()
    if not directory.exists():
        return []
    snapshots = sorted(
        directory.glob(f"{BACKUP_PREFIX}*.sqlite3"),
        key=lambda item: (item.stat().st_mtime_ns, item.name),
        reverse=True,
    )
    protected = {path.resolve() for path in protect}
    preserved = [path for path in snapshots if path.resolve() in protected]
    candidates = [path for path in snapshots if path.resolve() not in protected]
    removed = candidates[keep:]
    for path in removed:
        path.unlink()
    return removed


def create_backup(keep: int | None = None, protect: tuple[Path, ...] = ()) -> Path:
    """Create and verify an atomic SQLite snapshot, then prune older snapshots."""
    source_path = database_path()
    if not source_path.is_file():
        raise FileNotFoundError(f"Database does not exist yet; no backup created: {source_path}")
    count = retention_count() if keep is None else keep
    if count < 1:
        raise ValueError("Backup retention count must be at least 1.")

    directory = backup_directory()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = directory / f"{BACKUP_PREFIX}{stamp}.sqlite3"
    temporary = directory / f".{destination.name}.{uuid4().hex}.tmp"

    try:
        source = sqlite3.connect(source_path, timeout=10)
        try:
            target = sqlite3.connect(temporary)
            try:
                source.backup(target)
                target.commit()
            finally:
                target.close()
        finally:
            source.close()

        os.chmod(temporary, 0o600)
        _verify_database(temporary)
        os.replace(temporary, destination)
        os.chmod(destination, 0o600)
        prune_backups(count, protect=protect)
        return destination
    finally:
        if temporary.exists():
            temporary.unlink()


def restore_backup(path: str | Path) -> tuple[Path, Path | None]:
    """Restore a verified snapshot; first preserve the current database if present.

    Stop the application before calling this function. The restore is staged in
    the database directory and atomically replaces the live database file.
    """
    source_path = verify_backup(path)
    target_path = database_path()
    if source_path == target_path.resolve():
        raise ValueError("The live database cannot be used as its own restore source.")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    pre_restore = create_backup(protect=(source_path,)) if target_path.is_file() else None
    temporary = target_path.with_name(f".{target_path.name}.{uuid4().hex}.restore")
    try:
        source = sqlite3.connect(f"{source_path.as_uri()}?mode=ro", uri=True)
        try:
            target = sqlite3.connect(temporary)
            try:
                source.backup(target)
                target.commit()
            finally:
                target.close()
        finally:
            source.close()

        os.chmod(temporary, 0o600)
        _verify_database(temporary)
        os.replace(temporary, target_path)
        os.chmod(target_path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target_path, pre_restore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VIRTUE WISE local SQLite backup tools")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create and retain a verified backup")
    create.add_argument("--keep", type=int, default=None, help="number of snapshots to retain")
    verify = commands.add_parser("verify", help="verify a backup file")
    verify.add_argument("path", type=Path)
    prune = commands.add_parser("prune", help="remove snapshots beyond the retention count")
    prune.add_argument("--keep", type=int, default=None)
    restore = commands.add_parser("restore", help="restore a verified backup (stop the app first)")
    restore.add_argument("path", type=Path)
    restore.add_argument("--yes", action="store_true", help="confirm the destructive restore")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "create":
            path = create_backup(args.keep)
            print(f"Verified backup created: {path}")
        elif args.command == "verify":
            print(f"Backup verified: {verify_backup(args.path)}")
        elif args.command == "prune":
            removed = prune_backups(args.keep if args.keep is not None else retention_count())
            print(f"Removed {len(removed)} expired backup(s).")
        elif args.command == "restore":
            if not args.yes:
                raise ValueError("Restore requires --yes after stopping the application.")
            target, pre_restore = restore_backup(args.path)
            print(f"Restored database: {target}")
            if pre_restore is not None:
                print(f"Pre-restore database backup: {pre_restore}")
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"Backup operation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
