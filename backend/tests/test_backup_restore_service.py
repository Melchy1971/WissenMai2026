import json
from pathlib import Path
import sys

from app import cli
from app.services.backup_restore import BackupRestoreService
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
    data_dir = backup_dir / "data"
    config_dir = backup_dir / "config"
    backup_dir.mkdir()
    data_dir.mkdir()
    config_dir.mkdir()

    (data_dir / "documents.json").write_text("[]", encoding="utf-8")
    (backup_dir / "manifest.json").write_text(json.dumps({"created_at": "2026-05-11T00:00:00Z"}), encoding="utf-8")
    (backup_dir / "checksums.json").write_text(
        json.dumps(
            {
                "manifest.json": "wrong-hash",
                "data/documents.json": "wrong-hash",
            }
        ),
        encoding="utf-8",
    )

    service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
    result = service.validate_backup(input_dir=backup_dir)

    assert result["status"] == "invalid"
    assert result["mismatch_count"] == 2
    assert metrics_registry.snapshot()["backup_validated.failed"] == 1


def test_restore_backup_runs_validation_restore_and_reindex_sequence(tmp_path: Path, monkeypatch) -> None:
    service = BackupRestoreService(backup_root_dir=tmp_path / "backups")
    call_order: list[str] = []

    monkeypatch.setattr(service, "validate_backup", lambda **_kwargs: call_order.append("validate") or {"status": "ok"})
    monkeypatch.setattr(service, "_ensure_database_is_empty", lambda: call_order.append("empty-check"))
    monkeypatch.setattr(service, "_run_alembic_upgrade_head", lambda: call_order.append("alembic"))
    monkeypatch.setattr(service, "_restore_database_rows", lambda **_kwargs: call_order.append("restore-db"))
    monkeypatch.setattr(service, "_restore_original_files", lambda **_kwargs: call_order.append("restore-files") or 2)
    monkeypatch.setattr(service, "_rebuild_search_index", lambda **_kwargs: call_order.append("reindex") or {"status": "completed"})

    result = service.restore_backup(input_dir=tmp_path / "input-backup")

    assert call_order == ["validate", "empty-check", "alembic", "restore-db", "restore-files", "reindex"]
    assert result["status"] == "completed"
    assert result["restored_files"] == 2
    assert result["reindex_result"] == {"status": "completed"}


def test_cli_restore_prints_reindex_result(monkeypatch, capsys) -> None:
    class FakeBackupRestoreService:
        def restore_backup(self, *, input_dir):
            assert input_dir == "backup-dir"
            return {
                "status": "completed",
                "restored_files": 2,
                "reindex_result": {
                    "status": "completed",
                    "reindexed_chunk_count": 4,
                },
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