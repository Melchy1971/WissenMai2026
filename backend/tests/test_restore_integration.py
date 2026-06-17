"""Restore-Integration-Tests — Task #44, Sprint PRI-7.

Alle 4 Szenarien sind vollständig von SCGB-01 (TEST_DATABASE_URL) entkoppelt.
DB-Operationen, pg_dump/psql-Aufrufe und Alembic werden per monkeypatch gemockt.
Geprüft werden: Restore-Sequenz, Datenintegrität (Checksummen), Referenzen,
Fehlerbehandlung bei korruptem / partiellem Backup.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.services.backup_restore import (
    BackupRestoreError,
    BackupRestoreService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sql_content() -> str:
    return (
        "-- PostgreSQL dump\n"
        "SET standard_conforming_strings = on;\n"
        "CREATE TABLE documents (id text PRIMARY KEY);\n"
        "COPY documents (id) FROM stdin;\n"
        "doc-1\ndoc-2\n\\.\n"
    )


def _make_backup(
    backup_dir: Path,
    *,
    file_count: int = 2,
    sql_content: str | None = None,
    corrupt_checksums: bool = False,
    missing_sql: bool = False,
    missing_config: bool = False,
) -> None:
    """Erzeugt ein Backup-Verzeichnis mit konfigurierbaren Fehlerzuständen."""
    db_dir = backup_dir / "db"
    config_dir = backup_dir / "config"
    files_dir = backup_dir / "files"
    for d in (db_dir, config_dir, files_dir):
        d.mkdir(parents=True, exist_ok=True)

    sql = sql_content if sql_content is not None else _valid_sql_content()
    if not missing_sql:
        (db_dir / "database.sql").write_text(sql, encoding="utf-8")
    (db_dir / "pg_dump_version.txt").write_text("pg_dump (PostgreSQL) 16.3\n", encoding="utf-8")

    if not missing_config:
        (config_dir / "app-config.json").write_text(
            json.dumps({"app_env": "test", "default_workspace_id": "ws-1"}),
            encoding="utf-8",
        )

    for i in range(file_count):
        p = files_dir / f"ws-1/doc-{i}/file.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(f"content-{i}".encode())

    manifest = {
        "backup_format_version": 1,
        "created_at": "2026-06-17T00:00:00Z",
        "app_version": "0.1.0",
        "alembic_revision": "20260618_0026",
        "database_dump_format": "postgresql-sql",
        "database_dump_path": "db/database.sql",
        "pg_dump_version": "pg_dump (PostgreSQL) 16.3",
        "pg_dump_version_path": "db/pg_dump_version.txt",
        "workspace_count": 1,
        "document_count": file_count,
        "logical_components": ["documents", "document_versions"],
        "file_count": file_count,
        "config_files": ["config/app-config.json"],
        "search_index_included": False,
        "original_file_root": str(files_dir),
        "backup_dir": str(backup_dir),
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    checksum_map: dict[str, str] = {}
    for fp in sorted(backup_dir.rglob("*")):
        if fp.is_file():
            rel = fp.relative_to(backup_dir).as_posix()
            if rel != "checksums.json":
                checksum_map[rel] = _sha256(fp) if not corrupt_checksums else "0" * 64
    (backup_dir / "checksums.json").write_text(
        json.dumps(checksum_map, indent=2, sort_keys=True), encoding="utf-8"
    )


def _full_restore_mocks(service, monkeypatch, *, verify_status: str = "ok") -> list[str]:
    """Hängt alle Restore-Methoden als Mocks ein; gibt call_order zurück."""
    call_order: list[str] = []

    monkeypatch.setattr(
        service, "verify_backup",
        lambda **_: call_order.append("verify") or {
            "status": verify_status,
            "integrity_report": {"issue_count": 0, "issues": []},
            "error_classes": [],
        }
    )
    monkeypatch.setattr(service, "_ensure_database_is_empty",
        lambda: call_order.append("empty-check"))
    monkeypatch.setattr(service, "_run_alembic_upgrade_head",
        lambda: call_order.append("alembic"))
    monkeypatch.setattr(service, "_restore_database_dump",
        lambda **_: call_order.append("restore-db"))
    monkeypatch.setattr(service, "_restore_original_files",
        lambda **_: call_order.append("restore-files") or 2)
    monkeypatch.setattr(service, "_validate_restored_config",
        lambda **_: call_order.append("config-check") or {"status": "ok", "mismatches": {}})
    monkeypatch.setattr(service, "_rebuild_search_index",
        lambda **_: call_order.append("reindex") or {"status": "completed", "reindexed_chunk_count": 4})
    monkeypatch.setattr(service, "_run_drift_check",
        lambda: call_order.append("drift-check") or {"status": "ok"})
    monkeypatch.setattr(service, "_run_postgres_truth_smoke_subset",
        lambda: call_order.append("truth-smoke") or {"status": "passed", "tests": []})

    return call_order


# ---------------------------------------------------------------------------
# Szenario 1: Restore auf leeres System
# ---------------------------------------------------------------------------

class TestSzenario1RestoreLeeresSytem:
    """Restore auf frisches System: Sequenz, Status, Felder."""

    def test_restore_sequenz_ist_korrekt(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        call_order = _full_restore_mocks(service, monkeypatch)

        result = service.restore_backup(input_dir=tmp_path / "backup")

        assert call_order == [
            "verify", "empty-check", "alembic", "restore-db",
            "restore-files", "config-check", "reindex", "drift-check", "truth-smoke",
        ]
        assert result["status"] == "completed"

    def test_restore_ergebnis_felder_vollstaendig(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        _full_restore_mocks(service, monkeypatch)

        result = service.restore_backup(input_dir=tmp_path / "backup")

        assert "validation" in result
        assert "restored_files" in result
        assert "config_check" in result
        assert "reindex_result" in result
        assert "drift_check" in result
        assert "truth_smoke" in result
        assert "restored_at" in result

    def test_restored_files_count_korrekt(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        _full_restore_mocks(service, monkeypatch)

        result = service.restore_backup(input_dir=tmp_path / "backup")

        assert result["restored_files"] == 2

    def test_reindex_ergebnis_enthalten(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        _full_restore_mocks(service, monkeypatch)

        result = service.restore_backup(input_dir=tmp_path / "backup")

        assert result["reindex_result"]["status"] == "completed"
        assert result["reindex_result"]["reindexed_chunk_count"] == 4


# ---------------------------------------------------------------------------
# Szenario 2: Restore auf bestehendes System
# ---------------------------------------------------------------------------

class TestSzenario2RestoreBestehendesSytem:
    """Restore schlägt fehl, wenn Datenbank nicht leer ist."""

    def test_restore_verweigert_nicht_leere_datenbank(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

        monkeypatch.setattr(service, "verify_backup", lambda **_: {"status": "ok"})
        monkeypatch.setattr(
            service, "_ensure_database_is_empty",
            lambda: (_ for _ in ()).throw(
                BackupRestoreError("Restore requires an empty database; documents has 17 rows")
            )
        )

        with pytest.raises(BackupRestoreError, match="empty database"):
            service.restore_backup(input_dir=tmp_path / "backup")

    def test_restore_nach_leerem_check_setzt_alembic_auf_head(self, tmp_path: Path, monkeypatch) -> None:
        """Alembic upgrade head läuft nach dem Empty-Check."""
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        call_order = _full_restore_mocks(service, monkeypatch)

        service.restore_backup(input_dir=tmp_path / "backup")

        alembic_idx = call_order.index("alembic")
        empty_idx = call_order.index("empty-check")
        assert empty_idx < alembic_idx, "empty-check muss vor alembic stehen"

    def test_config_check_erkennt_mismatch_nach_restore(self, tmp_path: Path, monkeypatch) -> None:
        """_validate_restored_config meldet Mismatches; Restore schlägt dennoch ab."""
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

        monkeypatch.setattr(service, "verify_backup", lambda **_: {"status": "ok"})
        monkeypatch.setattr(service, "_ensure_database_is_empty", lambda: None)
        monkeypatch.setattr(service, "_run_alembic_upgrade_head", lambda: None)
        monkeypatch.setattr(service, "_restore_database_dump", lambda **_: None)
        monkeypatch.setattr(service, "_restore_original_files", lambda **_: 0)
        monkeypatch.setattr(service, "_validate_restored_config", lambda **_: {
            "status": "mismatch",
            "checked_keys": ["app_env"],
            "mismatches": {"app_env": {"expected": "production", "actual": "test"}},
        })
        monkeypatch.setattr(service, "_rebuild_search_index",
            lambda **_: {"status": "completed", "reindexed_chunk_count": 0})
        monkeypatch.setattr(service, "_run_drift_check", lambda: {"status": "ok"})
        monkeypatch.setattr(service, "_run_postgres_truth_smoke_subset",
            lambda: {"status": "passed", "tests": []})

        result = service.restore_backup(input_dir=tmp_path / "backup")

        # Restore läuft durch; Config-Mismatch wird reportiert, nicht geworfen
        assert result["status"] == "completed"
        assert result["config_check"]["status"] == "mismatch"
        assert "app_env" in result["config_check"]["mismatches"]


# ---------------------------------------------------------------------------
# Szenario 3: Korruptes Backup
# ---------------------------------------------------------------------------

class TestSzenario3KorruptesBackup:
    """Restore eines Backups mit Integritätsfehlern."""

    def test_korrupte_checksummen_blockieren_restore(self, tmp_path: Path, monkeypatch) -> None:
        backup_dir = tmp_path / "corrupt-backup"
        _make_backup(backup_dir, file_count=2, corrupt_checksums=True)

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

        # verify_backup läuft gegen das echte Backup auf dem Filesystem
        # restore_backup prüft den verify-Status und wirft bei invalid
        monkeypatch.setattr(service, "_ensure_database_is_empty", lambda: None)

        with pytest.raises(BackupRestoreError, match="validation failed"):
            service.restore_backup(input_dir=backup_dir)

    def test_verify_erkennt_fehlende_sql_datei(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "no-sql-backup"
        _make_backup(backup_dir, file_count=1, missing_sql=True)

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        result = service.verify_backup(input_dir=backup_dir)

        assert result["status"] == "invalid"
        # Fehlende Datei in checksums oder unlesbare DB-Dump
        error_codes = result["error_classes"]
        assert any(c in error_codes for c in [
            "missing-file", "missing-database-dump", "checksum-mismatch",
            "database-dump-unreadable", "restore-dry-run-failed",
        ]), f"Unerwartete error_classes: {error_codes}"

    def test_verify_erkennt_manipulierten_sql_dump(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "tampered-sql"
        _make_backup(backup_dir, file_count=1)

        # SQL-Dump nach Checksum-Berechnung verändern
        (backup_dir / "db" / "database.sql").write_text("not a real dump", encoding="utf-8")

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        result = service.verify_backup(input_dir=backup_dir)

        assert result["status"] == "invalid"
        assert "checksum-mismatch" in result["error_classes"]

    def test_verify_erkennt_fehlende_config(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "no-config"
        _make_backup(backup_dir, file_count=1, missing_config=True)

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        result = service.verify_backup(input_dir=backup_dir)

        assert result["status"] == "invalid"


# ---------------------------------------------------------------------------
# Szenario 4: Partielles Backup
# ---------------------------------------------------------------------------

class TestSzenario4PartiellesBackup:
    """Backups mit unvollständiger Struktur werden zuverlässig abgelehnt."""

    def test_fehlendes_files_verzeichnis_wird_erkannt(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "partial-backup"
        db_dir = backup_dir / "db"
        config_dir = backup_dir / "config"
        db_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        # files/ absichtlich nicht erstellen

        (db_dir / "database.sql").write_text(_valid_sql_content(), encoding="utf-8")
        (db_dir / "pg_dump_version.txt").write_text("pg_dump (PostgreSQL) 16.3\n", encoding="utf-8")
        (config_dir / "app-config.json").write_text("{}", encoding="utf-8")

        manifest = {
            "backup_format_version": 1,
            "created_at": "2026-06-17T00:00:00Z",
            "database_dump_format": "postgresql-sql",
            "database_dump_path": "db/database.sql",
            "pg_dump_version": "pg_dump (PostgreSQL) 16.3",
            "pg_dump_version_path": "db/pg_dump_version.txt",
            "logical_components": ["documents"],
            "file_count": 0,
            "config_files": ["config/app-config.json"],
            "search_index_included": False,
        }
        (backup_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (backup_dir / "checksums.json").write_text("{}", encoding="utf-8")

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        result = service.verify_backup(input_dir=backup_dir)

        assert result["status"] == "invalid"
        assert "missing-upload-file" in result["error_classes"]

    def test_manifest_mit_falschem_file_count_wird_erkannt(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "wrong-count"
        _make_backup(backup_dir, file_count=3)

        # Manifest file_count auf falschen Wert setzen
        manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
        manifest["file_count"] = 99  # falsch: wir haben nur 3
        (backup_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        # Checksum für manifest.json neu berechnen (damit der Checksum-Check nicht feuert)
        checksums = json.loads((backup_dir / "checksums.json").read_text(encoding="utf-8"))
        checksums["manifest.json"] = _sha256(backup_dir / "manifest.json")
        (backup_dir / "checksums.json").write_text(json.dumps(checksums), encoding="utf-8")

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        result = service.verify_backup(input_dir=backup_dir)

        assert result["status"] == "invalid"
        assert "manifest-file-count-mismatch" in result["error_classes"]

    def test_manifest_ohne_pflichtfelder_wird_erkannt(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "incomplete-manifest"
        backup_dir.mkdir()
        (backup_dir / "db").mkdir()
        (backup_dir / "files").mkdir()
        (backup_dir / "config").mkdir()

        # Manifest ohne database_dump_path und logical_components
        (backup_dir / "manifest.json").write_text(
            json.dumps({"backup_format_version": 1, "created_at": "2026-06-17T00:00:00Z"}),
            encoding="utf-8",
        )
        (backup_dir / "checksums.json").write_text("{}", encoding="utf-8")

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        result = service.verify_backup(input_dir=backup_dir)

        assert result["status"] == "invalid"
        assert "manifest-missing-field" in result["error_classes"]

    def test_restore_original_files_kopiert_in_zielverzeichnis(self, tmp_path: Path) -> None:
        """_restore_original_files: Dateien werden vom Backup ins Zielverzeichnis kopiert."""
        files_dir = tmp_path / "backup-files"
        files_dir.mkdir(parents=True)
        restore_root = tmp_path / "restored"

        from app.services.original_file_store import OriginalFileStore
        store = OriginalFileStore(root_dir=restore_root)

        # Quelldatei ins Backup legen
        (files_dir / "ws-1").mkdir(parents=True)
        (files_dir / "ws-1" / "doc.txt").write_bytes(b"restored-content")

        service = BackupRestoreService(
            backup_root_dir=tmp_path / "backups",
            original_file_store=store,
        )
        count = service._restore_original_files(files_dir=files_dir)

        assert count == 1
        restored = restore_root / "ws-1" / "doc.txt"
        assert restored.exists()
        assert restored.read_bytes() == b"restored-content"
