"""Tests for verified SQLite backups and safe restore behavior."""

import os
import sqlite3
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app import backup, store
from app.models import ProjectModel


def configure_paths(tmp_path, monkeypatch):
    database = tmp_path / "data" / "virtue-wise.sqlite3"
    backups = tmp_path / "separate-backups"
    monkeypatch.setenv("VIRTUE_WISE_DB", str(database))
    monkeypatch.setenv("VIRTUE_WISE_BACKUP_DIR", str(backups))
    return database, backups


def test_systemd_backup_service_uses_a_restricted_sandbox():
    unit_path = (
        Path(__file__).resolve().parents[1] / "deploy" / "systemd" / "virtue-wise-backup.service"
    )
    unit = unit_path.read_text(encoding="utf-8")

    required = [
        "NoNewPrivileges=true",
        "PrivateDevices=true",
        "PrivateNetwork=true",
        "ProtectHome=true",
        "ProtectSystem=strict",
        "ProtectKernelTunables=true",
        "ProtectKernelModules=true",
        "ProtectControlGroups=true",
        "RestrictAddressFamilies=AF_UNIX",
        "RestrictNamespaces=true",
        "RestrictSUIDSGID=true",
        "CapabilityBoundingSet=",
        "AmbientCapabilities=",
        "ReadWritePaths=/var/lib/virtue-wise /var/backups/virtue-wise",
    ]
    for directive in required:
        assert directive in unit

    assert "ReadWritePaths=/" not in unit.splitlines()
    assert "PrivateNetwork=false" not in unit


def test_create_and_verify_backup(tmp_path, monkeypatch):
    database, backups = configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Verified project"))

    snapshot = backup.create_backup()

    assert snapshot.parent == backups
    assert snapshot.exists()
    assert snapshot.stat().st_mode & 0o777 == 0o600
    assert backup.verify_backup(snapshot) == snapshot.resolve()
    with sqlite3.connect(database) as live, sqlite3.connect(snapshot) as saved:
        assert live.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert saved.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_backup_flushes_staging_file_before_publish_and_directory_after(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Durable publication"))
    events = []
    real_fsync = backup.os.fsync
    real_replace = backup.os.replace

    def record_fsync(descriptor):
        mode = os.fstat(descriptor).st_mode
        events.append("directory-fsync" if stat.S_ISDIR(mode) else "file-fsync")
        return real_fsync(descriptor)

    def record_replace(source, destination):
        events.append("replace")
        return real_replace(source, destination)

    monkeypatch.setattr(backup.os, "fsync", record_fsync)
    monkeypatch.setattr(backup.os, "replace", record_replace)

    snapshot = backup.create_backup()

    assert backup.verify_backup(snapshot)
    assert events[0] == "file-fsync"
    assert events[1] == "replace"
    if os.name == "posix":
        assert events[2] == "directory-fsync"
    else:
        assert events == ["file-fsync", "replace"]


def test_backup_health_check_accepts_a_fresh_verified_snapshot(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Fresh backup"))
    snapshot = backup.create_backup()
    now = datetime.fromtimestamp(snapshot.stat().st_mtime, UTC) + timedelta(hours=1)

    assert backup.check_latest_backup(max_age_hours=26, now=now) == snapshot.resolve()


def test_backup_health_check_rejects_a_stale_snapshot(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Stale backup"))
    snapshot = backup.create_backup()
    now = datetime.now(UTC)
    stale_timestamp = (now - timedelta(hours=27)).timestamp()
    os.utime(snapshot, (stale_timestamp, stale_timestamp))

    with pytest.raises(ValueError, match="stale"):
        backup.check_latest_backup(max_age_hours=26, now=now)


def test_backup_health_check_rejects_a_corrupt_newest_snapshot(tmp_path, monkeypatch):
    _, backups = configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Older valid backup"))
    backup.create_backup()
    corrupt = backups / "virtue-wise-99999999T999999999999Z.sqlite3"
    corrupt.write_bytes(b"not a SQLite database")
    now = datetime.now(UTC) + timedelta(seconds=2)
    modified = (now - timedelta(seconds=1)).timestamp()
    os.utime(corrupt, (modified, modified))

    with pytest.raises(ValueError, match="not a readable"):
        backup.check_latest_backup(max_age_hours=26, now=now)


def test_backup_health_check_rejects_missing_future_and_invalid_clock(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError, match="No managed"):
        backup.check_latest_backup()

    store.save_model(ProjectModel(title="Future backup"))
    snapshot = backup.create_backup()
    future = datetime.fromtimestamp(snapshot.stat().st_mtime, UTC) - timedelta(minutes=1)
    with pytest.raises(ValueError, match="future"):
        backup.check_latest_backup(now=future)
    with pytest.raises(ValueError, match="timezone-aware"):
        backup.check_latest_backup(now=datetime.now())
    with pytest.raises(ValueError, match="finite number"):
        backup.check_latest_backup(max_age_hours=float("inf"))


def test_backup_health_check_cli_returns_success_for_a_fresh_snapshot(
    tmp_path, monkeypatch, capsys
):
    configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Monitored backup"))
    backup.create_backup()
    monkeypatch.setattr(sys, "argv", ["app.backup", "check", "--max-age-hours", "26"])

    assert backup.main() == 0
    assert "fresh and verified" in capsys.readouterr().out


def test_backup_retention_keeps_newest_snapshots(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Project"))

    first = backup.create_backup(keep=3)
    second = backup.create_backup(keep=3)
    third = backup.create_backup(keep=2)

    snapshots = sorted(backup.backup_directory().glob("virtue-wise-*.sqlite3"))
    assert first not in snapshots
    assert second in snapshots
    assert third in snapshots
    assert len(snapshots) == 2


def test_restore_preserves_pre_restore_database_and_validates_content(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Known good project"))
    snapshot = backup.create_backup()

    store.save_model(ProjectModel(title="Changed project"))
    target, pre_restore = backup.restore_backup(snapshot)

    assert target == store.database_path()
    assert store.load_model().title == "Known good project"
    assert pre_restore is not None
    assert backup.verify_backup(pre_restore)
    with sqlite3.connect(pre_restore) as connection:
        payload = connection.execute(
            "SELECT payload FROM project_model WHERE singleton = 1"
        ).fetchone()[0]
    assert ProjectModel.model_validate_json(payload).title == "Changed project"


def test_restore_protects_selected_snapshot_from_retention_pruning(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    monkeypatch.setenv("VIRTUE_WISE_BACKUP_RETENTION_COUNT", "1")
    store.save_model(ProjectModel(title="Restore source"))
    snapshot = backup.create_backup()

    store.save_model(ProjectModel(title="Current live model"))
    _, pre_restore = backup.restore_backup(snapshot)

    assert backup.verify_backup(snapshot)
    assert pre_restore is not None
    assert backup.verify_backup(pre_restore)
    assert store.load_model().title == "Restore source"


def test_invalid_restore_does_not_change_live_database(tmp_path, monkeypatch):
    database, _ = configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Keep this project"))
    invalid = tmp_path / "invalid.sqlite3"
    invalid.write_bytes(b"not a sqlite database")

    with pytest.raises(ValueError):
        backup.restore_backup(invalid)

    assert store.load_model().title == "Keep this project"
    assert database.exists()


def test_backup_requires_existing_database(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError):
        backup.create_backup()


def test_purge_removes_only_managed_snapshots(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Project with backups"))
    snapshot = backup.create_backup()
    unrelated = backup.backup_directory() / "manual-export.sqlite3"
    unrelated.write_bytes(b"keep this file")

    removed = backup.purge_backups()

    assert removed == [snapshot]
    assert not snapshot.exists()
    assert unrelated.exists()


def test_purge_cli_requires_confirmation(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Project with backup"))
    snapshot = backup.create_backup()
    monkeypatch.setattr(sys, "argv", ["app.backup", "purge"])

    assert backup.main() == 1
    assert snapshot.exists()


def test_purge_cli_deletes_managed_snapshots_after_confirmation(tmp_path, monkeypatch):
    configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Project with backup"))
    snapshot = backup.create_backup()
    monkeypatch.setattr(sys, "argv", ["app.backup", "purge", "--yes"])

    assert backup.main() == 0
    assert not snapshot.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits are not portable to Windows ACLs")
def test_new_backup_directory_is_private(tmp_path, monkeypatch):
    _, backups = configure_paths(tmp_path, monkeypatch)
    store.save_model(ProjectModel(title="Private backup directory"))

    backup.create_backup()

    assert stat.S_IMODE(backups.stat().st_mode) == 0o700


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits are not portable to Windows ACLs")
def test_sqlite_staging_file_is_private_and_created_exclusively(tmp_path):
    staging = tmp_path / "staging.sqlite3"

    backup._create_private_sqlite_file(staging)

    assert stat.S_IMODE(staging.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        backup._create_private_sqlite_file(staging)
