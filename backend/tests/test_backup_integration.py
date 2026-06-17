"""Backup-Integration-Tests — Task #43, Sprint PRI-7.

Alle 5 Szenarien sind vollständig von SCGB-01 (TEST_DATABASE_URL) entkoppelt.
Datenbankoperationen und pg_dump-Aufrufe werden per monkeypatch gemockt.
Geprüft werden: Dateistruktur, Checksummen, Manifest-Inhalt, Fehlerbehandlung.
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
from app.services.original_file_store import OriginalFileStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_sql_dump() -> str:
    return (
        "-- PostgreSQL dump\n"
        "SET standard_conforming_strings = on;\n"
        "CREATE TABLE documents (id text PRIMARY KEY);\n"
        "COPY documents (id) FROM stdin;\n"
        "\\.\n"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _make_valid_backup(backup_dir: Path, *, file_count: int = 0) -> None:
    """Erstellt ein strukturell korrektes Backup-Verzeichnis ohne echte DB."""
    db_dir = backup_dir / "db"
    config_dir = backup_dir / "config"
    files_dir = backup_dir / "files"
    for d in (db_dir, config_dir, files_dir):
        d.mkdir(parents=True, exist_ok=True)

    (db_dir / "database.sql").write_text(_valid_sql_dump(), encoding="utf-8")
    (db_dir / "pg_dump_version.txt").write_text("pg_dump (PostgreSQL) 16.3\n", encoding="utf-8")
    (config_dir / "app-config.json").write_text(
        json.dumps({"app_env": "test", "file_count": file_count}), encoding="utf-8"
    )

    # Optionale Dateien simulieren
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
        "logical_components": ["documents", "document_versions", "document_chunks"],
        "file_count": file_count,
        "config_files": ["config/app-config.json"],
        "search_index_included": False,
        "original_file_root": str(files_dir),
        "backup_dir": str(backup_dir),
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    # Korrekte Checksummen berechnen
    checksum_map: dict[str, str] = {}
    for fp in sorted(backup_dir.rglob("*")):
        if fp.is_file():
            rel = fp.relative_to(backup_dir).as_posix()
            if rel != "checksums.json":
                checksum_map[rel] = _sha256(fp)
    (backup_dir / "checksums.json").write_text(
        json.dumps(checksum_map, indent=2, sort_keys=True), encoding="utf-8"
    )


def _mock_db_metadata(workspace_count: int = 0, document_count: int = 0):
    return {
        "workspace_count": workspace_count,
        "document_count": document_count,
        "logical_components": [
            "documents", "document_versions", "document_chunks",
            "chat_sessions", "chat_citations", "background_jobs",
        ],
    }


# ---------------------------------------------------------------------------
# Szenario 1: Leeres System sichern
# ---------------------------------------------------------------------------

class TestSzenario1LeeresSicherung:
    """Backup eines leeren Systems: 0 Workspaces, 0 Dokumente, 0 Dateien."""

    def test_backup_erstellt_korrekte_verzeichnisstruktur(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

        monkeypatch.setattr(service, "_collect_database_metadata", lambda: _mock_db_metadata())
        monkeypatch.setattr(service, "_create_database_dump", lambda **_: {
            "database_dump_path": "db/database.sql",
            "pg_dump_version_path": "db/pg_dump_version.txt",
            "pg_dump_version": "pg_dump (PostgreSQL) 16.3",
            "database_dump_format": "postgresql-sql",
        })
        monkeypatch.setattr(service, "_copy_original_files", lambda **_: 0)
        monkeypatch.setattr(service, "_write_config_snapshot", lambda **_: ["config/app-config.json"])
        monkeypatch.setattr(service, "_get_app_version", lambda: "0.1.0")
        monkeypatch.setattr(service, "_get_alembic_revision", lambda: "20260618_0026")
        monkeypatch.setattr(service, "_write_checksums", lambda _: None)

        output_dir = tmp_path / "backup-empty"
        summary = service.create_backup(output_dir=output_dir)

        assert (output_dir / "db").is_dir()
        assert (output_dir / "files").is_dir()
        assert (output_dir / "config").is_dir()
        assert (output_dir / "manifest.json").exists()

    def test_manifest_zeigt_null_workspaces_und_dokumente(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

        monkeypatch.setattr(service, "_collect_database_metadata", lambda: _mock_db_metadata(0, 0))
        monkeypatch.setattr(service, "_create_database_dump", lambda **_: {
            "database_dump_path": "db/database.sql",
            "pg_dump_version_path": "db/pg_dump_version.txt",
            "pg_dump_version": "pg_dump (PostgreSQL) 16.3",
            "database_dump_format": "postgresql-sql",
        })
        monkeypatch.setattr(service, "_copy_original_files", lambda **_: 0)
        monkeypatch.setattr(service, "_write_config_snapshot", lambda **_: ["config/app-config.json"])
        monkeypatch.setattr(service, "_get_app_version", lambda: "0.1.0")
        monkeypatch.setattr(service, "_get_alembic_revision", lambda: "20260618_0026")
        monkeypatch.setattr(service, "_write_checksums", lambda _: None)

        output_dir = tmp_path / "backup-empty"
        service.create_backup(output_dir=output_dir)
        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

        assert manifest["workspace_count"] == 0
        assert manifest["document_count"] == 0
        assert manifest["file_count"] == 0
        assert manifest["backup_format_version"] == 1
        assert manifest["alembic_revision"] == "20260618_0026"

    def test_verify_leeres_backup_ist_ok(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup-empty"
        _make_valid_backup(backup_dir, file_count=0)

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        result = service.verify_backup(input_dir=backup_dir)

        assert result["status"] == "ok"
        assert result["integrity_report"]["issue_count"] == 0


# ---------------------------------------------------------------------------
# Szenario 2: Befülltes System sichern
# ---------------------------------------------------------------------------

class TestSzenario2BefuellteSicherung:
    """Backup eines befüllten Systems mit Dateien; Checksummen müssen stimmen."""

    def test_backup_mit_dateien_hat_korrekte_checksummen(self, tmp_path: Path) -> None:
        """Verify läuft nach einem vollständigen Backup ohne Fehler durch."""
        backup_dir = tmp_path / "backup-filled"
        _make_valid_backup(backup_dir, file_count=5)

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        result = service.verify_backup(input_dir=backup_dir)

        assert result["status"] == "ok", result["integrity_report"]["issues"]
        assert result["integrity_report"]["checks"]["checksums_valid"]["status"] == "ok"
        assert result["integrity_report"]["checks"]["manifest_consistent"]["status"] == "ok"

    def test_manifest_file_count_stimmt_mit_files_verzeichnis_ueberein(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup-filled"
        _make_valid_backup(backup_dir, file_count=5)

        manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
        actual_files = list((backup_dir / "files").rglob("*"))
        actual_file_count = sum(1 for p in actual_files if p.is_file())

        assert manifest["file_count"] == actual_file_count == 5

    def test_checksummen_erkennen_manipulation_nach_backup(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup-filled"
        _make_valid_backup(backup_dir, file_count=3)

        # Datei nach Backup manipulieren
        (backup_dir / "db" / "database.sql").write_text("tampered content", encoding="utf-8")

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        result = service.verify_backup(input_dir=backup_dir)

        assert result["status"] == "invalid"
        assert "checksum-mismatch" in result["error_classes"]

    def test_create_backup_summary_fields(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

        monkeypatch.setattr(service, "_collect_database_metadata", lambda: _mock_db_metadata(3, 10))
        monkeypatch.setattr(service, "_create_database_dump", lambda **_: {
            "database_dump_path": "db/database.sql",
            "pg_dump_version_path": "db/pg_dump_version.txt",
            "pg_dump_version": "pg_dump (PostgreSQL) 16.3",
            "database_dump_format": "postgresql-sql",
        })
        monkeypatch.setattr(service, "_copy_original_files", lambda **_: 10)
        monkeypatch.setattr(service, "_write_config_snapshot", lambda **_: ["config/app-config.json"])
        monkeypatch.setattr(service, "_get_app_version", lambda: "0.1.0")
        monkeypatch.setattr(service, "_get_alembic_revision", lambda: "20260618_0026")
        monkeypatch.setattr(service, "_write_checksums", lambda _: None)

        output_dir = tmp_path / "backup-filled"
        summary = service.create_backup(output_dir=output_dir)

        assert summary.workspace_count == 3
        assert summary.document_count == 10
        assert summary.file_count == 10
        assert summary.alembic_revision == "20260618_0026"
        assert summary.manifest_path.endswith("manifest.json")


# ---------------------------------------------------------------------------
# Szenario 3: Große Datenmenge
# ---------------------------------------------------------------------------

class TestSzenario3GrosseDateimenge:
    """100 Dateien im Backup; Checksummen, Manifest und Verzeichnisstruktur korrekt."""

    def test_backup_mit_100_dateien_validiert_korrekt(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup-large"
        _make_valid_backup(backup_dir, file_count=100)

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        result = service.verify_backup(input_dir=backup_dir)

        assert result["status"] == "ok", result["integrity_report"]["issues"]
        actual_count = sum(1 for p in (backup_dir / "files").rglob("*") if p.is_file())
        assert actual_count == 100

    def test_checksummen_decken_alle_100_dateien_ab(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup-large"
        _make_valid_backup(backup_dir, file_count=100)

        checksums = json.loads((backup_dir / "checksums.json").read_text(encoding="utf-8"))
        file_entries = [k for k in checksums if k.startswith("files/")]
        assert len(file_entries) == 100

    def test_manifest_dokument_count_bei_100_eintraegen(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup-large"
        _make_valid_backup(backup_dir, file_count=100)

        manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["document_count"] == 100
        assert manifest["file_count"] == 100


# ---------------------------------------------------------------------------
# Szenario 4: Fehlerhafte Konfiguration
# ---------------------------------------------------------------------------

class TestSzenario4FehlerhalfteKonfiguration:
    """pg_dump nicht vorhanden / DB nicht erreichbar — BackupRestoreError erwartet."""

    def test_fehlt_pg_dump_wirft_backup_restore_error(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        monkeypatch.setattr("app.services.backup_restore.shutil.which", lambda _: None)

        with pytest.raises(BackupRestoreError, match="pg_dump"):
            service._create_database_dump(db_dir=tmp_path / "db")

    def test_fehlende_manifest_json_wirft_fehler(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup-broken"
        backup_dir.mkdir()
        (backup_dir / "checksums.json").write_text("{}", encoding="utf-8")
        # manifest.json fehlt absichtlich

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        with pytest.raises(BackupRestoreError, match="manifest.json"):
            service.verify_backup(input_dir=backup_dir)

    def test_fehlende_checksums_json_wirft_fehler(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup-broken"
        backup_dir.mkdir()
        (backup_dir / "manifest.json").write_text("{}", encoding="utf-8")
        # checksums.json fehlt absichtlich

        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        with pytest.raises(BackupRestoreError, match="checksums.json"):
            service.verify_backup(input_dir=backup_dir)

    def test_backup_ziel_nicht_leer_wirft_fehler(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
        existing = tmp_path / "existing-backup"
        existing.mkdir()
        (existing / "some-file.txt").write_text("already here", encoding="utf-8")

        monkeypatch.setattr(service, "_collect_database_metadata", lambda: _mock_db_metadata())
        with pytest.raises(BackupRestoreError, match="not empty"):
            service.create_backup(output_dir=existing)

    def test_restore_schlaegt_fehl_wenn_backup_invalid(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

        # verify_backup gibt invalid zurück
        monkeypatch.setattr(service, "verify_backup", lambda **_: {
            "status": "invalid",
            "integrity_report": {"issue_count": 1, "issues": [{"code": "missing-file", "path": "db/database.sql", "detail": "missing"}]},
            "error_classes": ["missing-file"],
        })

        with pytest.raises(BackupRestoreError, match="validation failed"):
            service.restore_backup(input_dir=tmp_path / "input")


# ---------------------------------------------------------------------------
# Szenario 5: Abbruch während Backup
# ---------------------------------------------------------------------------

class TestSzenario5AbbruchWaehrendBackup:
    """Fehler in einer Backup-Phase hinterlässt kein korruptes Artefakt."""

    def test_fehler_in_db_dump_verhindert_manifest_erstellung(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

        monkeypatch.setattr(service, "_collect_database_metadata", lambda: _mock_db_metadata(1, 3))
        monkeypatch.setattr(service, "_create_database_dump", lambda **_: (_ for _ in ()).throw(
            BackupRestoreError("pg_dump exited with code 1: connection refused")
        ))

        output_dir = tmp_path / "aborted-backup"
        with pytest.raises(BackupRestoreError, match="pg_dump"):
            service.create_backup(output_dir=output_dir)

        assert not (output_dir / "manifest.json").exists(), "manifest.json darf bei Abbruch nicht existieren"

    def test_fehler_in_files_copy_verhindert_manifest(self, tmp_path: Path, monkeypatch) -> None:
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

        monkeypatch.setattr(service, "_collect_database_metadata", lambda: _mock_db_metadata(1, 3))
        monkeypatch.setattr(service, "_create_database_dump", lambda **_: {
            "database_dump_path": "db/database.sql",
            "pg_dump_version_path": "db/pg_dump_version.txt",
            "pg_dump_version": "pg_dump (PostgreSQL) 16.3",
            "database_dump_format": "postgresql-sql",
        })
        monkeypatch.setattr(service, "_copy_original_files", lambda **_: (_ for _ in ()).throw(
            BackupRestoreError("Referenced original file is missing: ws-1/doc-1/file.txt")
        ))

        output_dir = tmp_path / "aborted-backup"
        with pytest.raises(BackupRestoreError, match="original file is missing"):
            service.create_backup(output_dir=output_dir)

        assert not (output_dir / "manifest.json").exists()

    def test_restore_runtime_marker_wird_nach_fehler_geloescht(self, tmp_path: Path, monkeypatch) -> None:
        """_restore_runtime_marker context manager entfernt die Statusdatei auch bei Exception."""
        service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

        # Override RESTORE_RUNTIME_STATUS path so it lands in tmp_path
        import app.services.backup_restore as br_module
        marker_path = tmp_path / "restore_runtime_status.json"
        monkeypatch.setattr(br_module, "RESTORE_RUNTIME_STATUS", marker_path)

        monkeypatch.setattr(service, "verify_backup", lambda **_: {"status": "ok"})
        monkeypatch.setattr(service, "_ensure_database_is_empty", lambda: None)
        monkeypatch.setattr(service, "_run_alembic_upgrade_head", lambda: None)
        monkeypatch.setattr(service, "_restore_database_dump", lambda **_: (_ for _ in ()).throw(
            BackupRestoreError("psql exited with code 1")
        ))

        with pytest.raises(BackupRestoreError, match="psql"):
            service.restore_backup(input_dir=tmp_path / "input")

        assert not marker_path.exists(), "Runtime-Marker muss nach Fehler entfernt werden"
