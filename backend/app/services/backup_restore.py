from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Json
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_database_url, get_sqlalchemy_database_url
from app.db.session import get_engine
from app.observability.logging import log_event
from app.services.original_file_store import OriginalFileStore
from app.services.search_index_service import SearchIndexRebuildService


TABLE_ORDER = [
    "workspaces",
    "users",
    "workspace_memberships",
    "auth_sessions",
    "documents",
    "document_versions",
    "document_chunks",
    "chat_sessions",
    "chat_messages",
    "chat_citations",
    "background_jobs",
]
JSON_COLUMNS = {
    "document_versions": {"metadata"},
    "document_chunks": {"heading_path", "metadata"},
    "chat_messages": {"metadata"},
    "chat_citations": {"source_anchor"},
    "background_jobs": {"payload", "result"},
}


class BackupRestoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackupSummary:
    backup_dir: str
    created_at: str
    table_counts: dict[str, int]
    file_count: int
    config_files: list[str]
    migration_heads: list[str]


class BackupRestoreService:
    def __init__(
        self,
        *,
        backup_root_dir: str | Path | None = None,
        original_file_store: OriginalFileStore | None = None,
    ) -> None:
        configured_root = backup_root_dir or settings.backup_restore_root_dir
        if configured_root is None:
            configured_root = Path.cwd() / "backups"
        self._backup_root_dir = Path(configured_root)
        self._original_file_store = original_file_store or OriginalFileStore()

    def create_backup(self, *, output_dir: str | Path | None = None) -> BackupSummary:
        backup_dir = Path(output_dir) if output_dir else self._default_backup_dir()
        if backup_dir.exists() and any(backup_dir.iterdir()):
            raise BackupRestoreError(f"Backup target {backup_dir} is not empty")
        backup_dir.mkdir(parents=True, exist_ok=True)

        data_dir = backup_dir / "data"
        files_dir = backup_dir / "files"
        config_dir = backup_dir / "config"
        data_dir.mkdir(exist_ok=True)
        files_dir.mkdir(exist_ok=True)
        config_dir.mkdir(exist_ok=True)

        table_counts = self._export_database_rows(data_dir=data_dir)
        copied_files = self._copy_original_files(files_dir=files_dir, data_dir=data_dir)
        config_files = self._write_config_snapshot(config_dir=config_dir)
        manifest = self._build_manifest(
            backup_dir=backup_dir,
            table_counts=table_counts,
            file_count=copied_files,
            config_files=config_files,
        )
        self._write_json(backup_dir / "manifest.json", manifest)
        self._write_checksums(backup_dir)
        log_event("backup_created", status="completed")
        return BackupSummary(
            backup_dir=str(backup_dir),
            created_at=str(manifest["created_at"]),
            table_counts=table_counts,
            file_count=copied_files,
            config_files=config_files,
            migration_heads=list(manifest["migration_heads"]),
        )

    def validate_backup(self, *, input_dir: str | Path) -> dict[str, Any]:
        backup_dir = Path(input_dir)
        manifest_path = backup_dir / "manifest.json"
        checksum_path = backup_dir / "checksums.json"
        if not manifest_path.exists():
            raise BackupRestoreError("manifest.json is missing")
        if not checksum_path.exists():
            raise BackupRestoreError("checksums.json is missing")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        checksums = json.loads(checksum_path.read_text(encoding="utf-8"))
        mismatches: list[str] = []
        for relative_path, expected_hash in checksums.items():
            candidate = backup_dir / relative_path
            if not candidate.exists():
                mismatches.append(f"missing:{relative_path}")
                continue
            actual_hash = self._hash_file(candidate)
            if actual_hash != expected_hash:
                mismatches.append(f"checksum:{relative_path}")

        result = {
            "status": "ok" if not mismatches else "invalid",
            "backup_dir": str(backup_dir),
            "checked_at": datetime.now(UTC).isoformat(),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
            "manifest": manifest,
        }
        log_event("backup_validated", status="completed" if not mismatches else "failed")
        return result

    def restore_backup(self, *, input_dir: str | Path) -> dict[str, Any]:
        backup_dir = Path(input_dir)
        log_event("backup_restore_started", status="started")
        validation = self.validate_backup(input_dir=backup_dir)
        if validation["status"] != "ok":
            raise BackupRestoreError("Backup validation failed before restore")

        self._ensure_database_is_empty()
        self._run_alembic_upgrade_head()
        self._restore_database_rows(data_dir=backup_dir / "data")
        restored_files = self._restore_original_files(files_dir=backup_dir / "files")
        reindex_result = self._rebuild_search_index()
        result = {
            "status": "completed",
            "restored_files": restored_files,
            "reindex_result": reindex_result,
            "restored_at": datetime.now(UTC).isoformat(),
        }
        log_event("backup_restored", status="completed")
        return result

    def rebuild_search_index(self, *, workspace_id: str | None = None) -> dict[str, Any]:
        result = self._rebuild_search_index(workspace_id=workspace_id)
        log_event("backup_search_rebuild", status="completed")
        return result

    def _export_database_rows(self, *, data_dir: Path) -> dict[str, int]:
        counts: dict[str, int] = {}
        with connect(get_database_url(), row_factory=dict_row, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                for table_name in TABLE_ORDER:
                    cursor.execute(f"select * from {table_name} order by 1")
                    rows = cursor.fetchall()
                    counts[table_name] = len(rows)
                    self._write_json(data_dir / f"{table_name}.json", rows)
        return counts

    def _restore_database_rows(self, *, data_dir: Path) -> None:
        with connect(get_database_url(), connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                for table_name in TABLE_ORDER:
                    rows = json.loads((data_dir / f"{table_name}.json").read_text(encoding="utf-8"))
                    if not rows:
                        continue
                    columns = list(rows[0].keys())
                    placeholders = ", ".join(["%s"] * len(columns))
                    column_sql = ", ".join(columns)
                    sql = f"insert into {table_name} ({column_sql}) values ({placeholders})"
                    values = [tuple(self._normalize_insert_value(table_name, column, row[column]) for column in columns) for row in rows]
                    cursor.executemany(sql, values)
            connection.commit()

    def _copy_original_files(self, *, files_dir: Path, data_dir: Path) -> int:
        version_rows = json.loads((data_dir / "document_versions.json").read_text(encoding="utf-8"))
        copied = 0
        for row in version_rows:
            metadata = row.get("metadata") or {}
            original = metadata.get("backup_original") if isinstance(metadata, dict) else None
            if not isinstance(original, dict):
                continue
            relative_path = original.get("relative_path")
            if not isinstance(relative_path, str) or not relative_path:
                continue
            source = self._original_file_store.resolve_relative_path(relative_path)
            if not source.exists():
                raise BackupRestoreError(f"Referenced original file is missing: {relative_path}")
            target = files_dir / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
        return copied

    def _restore_original_files(self, *, files_dir: Path) -> int:
        restored = 0
        for file_path in files_dir.rglob("*"):
            if not file_path.is_file():
                continue
            relative_path = file_path.relative_to(files_dir)
            target = self._original_file_store.resolve_relative_path(relative_path.as_posix())
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target)
            restored += 1
        return restored

    def _write_config_snapshot(self, *, config_dir: Path) -> list[str]:
        config_payload = {
            "app_env": settings.app_env,
            "default_workspace_id": settings.default_workspace_id,
            "default_user_id": settings.default_user_id,
            "max_upload_size_bytes": settings.max_upload_size_bytes,
            "import_jobs_temp_dir": settings.import_jobs_temp_dir,
            "original_file_store_dir": str(self._original_file_store.root_dir),
        }
        file_name = "app-config.json"
        self._write_json(config_dir / file_name, config_payload)
        return [f"config/{file_name}"]

    def _build_manifest(
        self,
        *,
        backup_dir: Path,
        table_counts: dict[str, int],
        file_count: int,
        config_files: list[str],
    ) -> dict[str, Any]:
        return {
            "backup_format_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "app_version": "0.1.0",
            "migration_heads": self._get_alembic_heads(),
            "workspace_scope": "all",
            "database_dump_format": "table-json",
            "database_files": [f"data/{table_name}.json" for table_name in TABLE_ORDER],
            "table_counts": table_counts,
            "file_count": file_count,
            "config_files": config_files,
            "search_index_included": False,
            "original_file_root": str(self._original_file_store.root_dir),
            "backup_dir": str(backup_dir),
        }

    def _write_checksums(self, backup_dir: Path) -> None:
        checksum_map: dict[str, str] = {}
        for file_path in sorted(backup_dir.rglob("*")):
            if not file_path.is_file():
                continue
            relative_path = file_path.relative_to(backup_dir).as_posix()
            if relative_path == "checksums.json":
                continue
            checksum_map[relative_path] = self._hash_file(file_path)
        self._write_json(backup_dir / "checksums.json", checksum_map)

    def _ensure_database_is_empty(self) -> None:
        with connect(get_database_url(), row_factory=dict_row, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                for table_name in TABLE_ORDER:
                    cursor.execute(f"select count(*) as count from {table_name}")
                    count = int(cursor.fetchone()["count"])
                    if count:
                        raise BackupRestoreError(f"Restore requires an empty database; {table_name} has {count} rows")

    def _run_alembic_upgrade_head(self) -> None:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", get_sqlalchemy_database_url())
        command.upgrade(config, "head")

    def _rebuild_search_index(self, *, workspace_id: str | None = None) -> dict[str, Any]:
        engine = get_engine()
        with Session(engine) as session:
            return SearchIndexRebuildService.from_session(session).rebuild_search_index(workspace_id=workspace_id)

    def _default_backup_dir(self) -> Path:
        timestamp = datetime.now(UTC).strftime("backup-%Y-%m-%dT%H-%M-%SZ")
        return self._backup_root_dir / timestamp

    def _get_alembic_heads(self) -> list[str]:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        script_location = config.get_main_option("script_location") or "migrations"
        script_dir = Path(__file__).resolve().parents[2] / script_location
        versions_dir = script_dir / "versions"
        if not versions_dir.exists():
            return []
        return sorted(path.stem for path in versions_dir.glob("*.py") if path.name != "__init__.py")[-1:]

    def _normalize_insert_value(self, table_name: str, column_name: str, value: Any) -> Any:
        if value is None:
            return None
        if column_name in JSON_COLUMNS.get(table_name, set()):
            return Json(value)
        return value

    def _hash_file(self, path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _write_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")