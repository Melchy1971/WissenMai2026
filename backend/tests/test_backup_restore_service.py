import json
from pathlib import Path
import sys

from app import cli
from app.services.backup_restore import BackupRestoreError, BackupRestoreService
from app.observability.logging import metrics_registry
from app.services.original_file_store import OriginalFileStore


def test_original_file_store_persists_source_file(tmp_path: Path) -> None:
    store = OriginalFileStore(root_dir=tmp_path / "originals")

    metadata = store.store_source_file(
        workspace_id="workspace-1",
        document_id="document-1",
        content_hash="hash-1",
        filename="notes.txt",
        source_bytes=b"hello backup",
    )

    stored_path = store.resolve_relative_path(str(metadata["relative_path"]))
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"hello backup"
    assert metadata["filename"] == "notes.txt"
    assert metadata["byte_size"] == len(b"hello backup")


def test_backup_validate_reports_checksum_mismatch(tmp_path: Path) -> None:
    metrics_registry.reset()
    backup_dir = tmp_path / "backup"
    db_dir = backup_dir / "db"
    config_dir = backup_dir / "config"
    files_dir = backup_dir / "files"
    backup_dir.mkdir()
    db_dir.mkdir()
    config_dir.mkdir()
    files_dir.mkdir()

    (db_dir / "database.sql").write_text("CREATE TABLE test(id int);", encoding="utf-8")
    (db_dir / "pg_dump_version.txt").write_text("pg_dump (PostgreSQL) 16.3\n", encoding="utf-8")
    (config_dir / "app-config.json").write_text("{}", encoding="utf-8")
    (backup_dir / "manifest.json").write_text(
        json.dumps(
            {
                "backup_format_version": 1,
                "created_at": "2026-05-11T00:00:00Z",
                "database_dump_format": "postgresql-sql",
                "database_dump_path": "db/database.sql",
                "pg_dump_version": "pg_dump (PostgreSQL) 16.3",
                "pg_dump_version_path": "db/pg_dump_version.txt",
                "logical_components": ["documents"],
                "file_count": 0,
                "config_files": ["config/app-config.json"],
            }
        ),
        encoding="utf-8",
    )
    (backup_dir / "checksums.json").write_text(
        json.dumps(
            {
                "manifest.json": "wrong-hash",
                "db/database.sql": "wrong-hash",
            }
        ),
        encoding="utf-8",
    )

    service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
    result = service.validate_backup(input_dir=backup_dir)

    assert result["status"] == "invalid"
    assert result["mismatch_count"] == 2
    assert metrics_registry.snapshot()["backup_validated.failed"] == 1


def test_verify_backup_reports_structured_integrity_issues(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    db_dir = backup_dir / "db"
    config_dir = backup_dir / "config"
    files_dir = backup_dir / "files"
    backup_dir.mkdir()
    db_dir.mkdir()
    config_dir.mkdir()
    files_dir.mkdir()

    (db_dir / "database.sql").write_text("not a sql dump", encoding="utf-8")
    (db_dir / "pg_dump_version.txt").write_text("pg_dump (PostgreSQL) 16.3\n", encoding="utf-8")
    (config_dir / "app-config.json").write_text("{}", encoding="utf-8")
    (backup_dir / "manifest.json").write_text(
        json.dumps(
            {
                "backup_format_version": 1,
                "created_at": "2026-05-11T00:00:00Z",
                "database_dump_format": "postgresql-sql",
                "database_dump_path": "db/database.sql",
                "pg_dump_version": "pg_dump (PostgreSQL) 16.3",
                "pg_dump_version_path": "db/pg_dump_version.txt",
                "logical_components": ["documents"],
                "file_count": 1,
                "config_files": ["config/app-config.json"],
            }
        ),
        encoding="utf-8",
    )
    (backup_dir / "checksums.json").write_text(
        json.dumps(
            {
                "manifest.json": "bad-hash",
                "db/database.sql": "bad-hash",
                "config/app-config.json": "short",
            }
        ),
        encoding="utf-8",
    )

    service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
    result = service.verify_backup(input_dir=backup_dir)

    assert result["status"] == "invalid"
    assert result["integrity_report"]["checks"]["db_dump_readable"]["status"] == "invalid"
    assert result["integrity_report"]["checks"]["manifest_consistent"]["status"] == "invalid"
    assert result["integrity_report"]["checks"]["checksums_valid"]["status"] == "invalid"
    assert result["integrity_report"]["checks"]["restore_dry_run"]["status"] == "invalid"
    assert "database-dump-unreadable" in result["error_classes"]
    assert "manifest-file-count-mismatch" in result["error_classes"]
    assert "checksum-entry-invalid" in result["error_classes"]
    assert "restore-dry-run-failed" in result["error_classes"]


def test_restore_backup_runs_validation_restore_and_reindex_sequence(tmp_path: Path, monkeypatch) -> None:
    service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
    call_order: list[str] = []

    monkeypatch.setattr(service, "verify_backup", lambda **_kwargs: call_order.append("validate") or {"status": "ok"})
    monkeypatch.setattr(service, "_ensure_database_is_empty", lambda: call_order.append("empty-check"))
    monkeypatch.setattr(service, "_run_alembic_upgrade_head", lambda: call_order.append("alembic"))
    monkeypatch.setattr(service, "_restore_database_dump", lambda **_kwargs: call_order.append("restore-db"))
    monkeypatch.setattr(service, "_restore_original_files", lambda **_kwargs: call_order.append("restore-files") or 2)
    monkeypatch.setattr(service, "_validate_restored_config", lambda **_kwargs: call_order.append("config-check") or {"status": "ok"})
    monkeypatch.setattr(service, "_rebuild_search_index", lambda **_kwargs: call_order.append("reindex") or {"status": "completed"})
    monkeypatch.setattr(service, "_run_drift_check", lambda: call_order.append("drift-check") or {"status": "ok"})
    monkeypatch.setattr(service, "_run_postgres_truth_smoke_subset", lambda: call_order.append("truth-smoke") or {"status": "passed"})

    result = service.restore_backup(input_dir=tmp_path / "input-backup")

    assert call_order == ["validate", "empty-check", "alembic", "restore-db", "restore-files", "config-check", "reindex", "drift-check", "truth-smoke"]
    assert result["status"] == "completed"
    assert result["restored_files"] == 2
    assert result["config_check"] == {"status": "ok"}
    assert result["reindex_result"] == {"status": "completed"}
    assert result["drift_check"] == {"status": "ok"}
    assert result["truth_smoke"] == {"status": "passed"}


def test_create_backup_writes_pg_dump_structure_and_manifest(tmp_path: Path, monkeypatch) -> None:
    service = BackupRestoreService(backup_root_dir=tmp_path / "backups")

    monkeypatch.setattr(service, "_collect_database_metadata", lambda: {
        "workspace_count": 2,
        "document_count": 5,
        "logical_components": [
            "documents",
            "document_versions",
            "document_chunks",
            "chat_sessions",
            "chat_citations",
            "background_jobs",
        ],
    })
    monkeypatch.setattr(service, "_create_database_dump", lambda **_kwargs: {
        "database_dump_path": "db/database.sql",
        "pg_dump_version_path": "db/pg_dump_version.txt",
        "pg_dump_version": "pg_dump (PostgreSQL) 16.3",
        "database_dump_format": "postgresql-sql",
    })
    monkeypatch.setattr(service, "_copy_original_files", lambda **_kwargs: 3)
    monkeypatch.setattr(service, "_write_config_snapshot", lambda **_kwargs: ["config/app-config.json"])
    monkeypatch.setattr(service, "_get_app_version", lambda: "0.1.0")
    monkeypatch.setattr(service, "_get_alembic_revision", lambda: "20260508_0014")
    monkeypatch.setattr(service, "_write_checksums", lambda _backup_dir: None)

    backup_dir = tmp_path / "backup"
    summary = service.create_backup(output_dir=backup_dir)
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))

    assert (backup_dir / "db").exists()
    assert (backup_dir / "files").exists()
    assert (backup_dir / "config").exists()
    assert summary.database_dump_path.endswith("db\\database.sql")
    assert manifest["database_dump_path"] == "db/database.sql"
    assert manifest["pg_dump_version"] == "pg_dump (PostgreSQL) 16.3"
    assert manifest["workspace_count"] == 2
    assert manifest["document_count"] == 5
    assert manifest["alembic_revision"] == "20260508_0014"


def test_create_database_dump_requires_pg_dump(tmp_path: Path, monkeypatch) -> None:
    service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
    monkeypatch.setattr("app.services.backup_restore.shutil.which", lambda _name: None)

    try:
        service._create_database_dump(db_dir=tmp_path / "db")
    except BackupRestoreError as exc:
        assert "pg_dump" in str(exc)
    else:
        raise AssertionError("expected BackupRestoreError when pg_dump is missing")


def test_cli_restore_prints_reindex_result(monkeypatch, capsys) -> None:
    class FakeBackupRestoreService:
        def restore_backup(self, *, input_dir):
            assert input_dir == "backup-dir"
            return {
                "status": "completed",
                "restored_files": 2,
                "config_check": {"status": "ok"},
                "reindex_result": {
                    "status": "completed",
                    "reindexed_chunk_count": 4,
                },
                "drift_check": {"status": "ok", "drift_score": 100},
                "truth_smoke": {"status": "passed"},
            }

    monkeypatch.setattr(cli, "BackupRestoreService", lambda: FakeBackupRestoreService())
    monkeypatch.setattr(sys, "argv", ["app.cli", "backup", "restore", "--input", "backup-dir"])

    exit_code = cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "completed"
    assert payload["reindex_result"] == {
        "status": "completed",
        "reindexed_chunk_count": 4,
    }


def test_cli_verify_backup_prints_integrity_report(monkeypatch, capsys) -> None:
    class FakeBackupRestoreService:
        def verify_backup(self, *, input_dir):
            assert input_dir == "backup-dir"
            return {
                "status": "ok",
                "error_classes": [],
                "integrity_report": {
                    "checks": {
                        "db_dump_readable": {"status": "ok"},
                    },
                    "issue_count": 0,
                    "issues": [],
                },
            }

    monkeypatch.setattr(cli, "BackupRestoreService", lambda: FakeBackupRestoreService())
    monkeypatch.setattr(sys, "argv", ["app.cli", "backup", "verify-backup", "--input", "backup-dir"])

    exit_code = cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["integrity_report"]["issue_count"] == 0


def test_validate_restored_config_reports_mismatches(tmp_path: Path) -> None:
    service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app-config.json").write_text(
        json.dumps(
            {
                "app_env": "production",
                "default_workspace_id": "workspace-x",
                "default_user_id": "user-x",
                "max_upload_size_bytes": 1,
                "import_jobs_temp_dir": None,
                "original_file_store_dir": str(tmp_path / "elsewhere"),
            }
        ),
        encoding="utf-8",
    )

    result = service._validate_restored_config(config_dir=config_dir)

    assert result["status"] == "mismatch"
    assert "app_env" in result["mismatches"]