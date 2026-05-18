from __future__ import annotations

from contextlib import contextmanager
import json
import os
import subprocess
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from alembic import command
from alembic.config import Config
from psycopg import connect
from psycopg.rows import dict_row
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_database_url, get_sqlalchemy_database_url
from app.db.session import get_engine
from app.observability.logging import get_observability_context, log_event
from app.services.original_file_store import OriginalFileStore
from app.services.search_index_service import SearchIndexRebuildService

DATABASE_DUMP_FILENAME = "database.sql"
DATABASE_VERSION_FILENAME = "pg_dump_version.txt"
CONFIG_SNAPSHOT_FILENAME = "app-config.json"
DATABASE_LOGICAL_COMPONENTS = [
    "documents",
    "document_versions",
    "document_chunks",
    "chat_sessions",
    "chat_citations",
    "background_jobs",
]
RESTORE_SMOKE_TESTS = [
    "tests/postgres_truth/test_m4_truth_flows.py::test_lifecycle_and_workspace_isolation_are_truth_checked",
    "tests/postgres_truth/test_m4_truth_flows.py::test_search_chat_retrieval_and_reindex_use_real_postgresql_state",
    "tests/postgres_truth/test_m4c_lifecycle_retrieval_truth.py::test_m4c_historical_citations_reflect_live_source_status",
    "tests/postgres_truth/test_m4b_upload_queue_truth.py::test_m4b_retryable_job_is_claimed_after_backoff_expires",
]
REPO_ROOT = Path(__file__).resolve().parents[3]
RESTORE_RUNTIME_STATUS = REPO_ROOT / "reports" / "restore_runtime_status.json"


class BackupRestoreError(RuntimeError):
    pass


class BackupVerificationError(BackupRestoreError):
    pass


class BackupVerificationDryRunError(BackupVerificationError):
    pass


@dataclass(frozen=True)
class BackupSummary:
    backup_dir: str
    created_at: str
    manifest_path: str
    database_dump_path: str
    file_count: int
    config_files: list[str]
    workspace_count: int
    document_count: int
    alembic_revision: str | None


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

        db_dir = backup_dir / "db"
        files_dir = backup_dir / "files"
        config_dir = backup_dir / "config"
        db_dir.mkdir(exist_ok=True)
        files_dir.mkdir(exist_ok=True)
        config_dir.mkdir(exist_ok=True)

        db_metadata = self._collect_database_metadata()
        dump_info = self._create_database_dump(db_dir=db_dir)
        copied_files = self._copy_original_files(files_dir=files_dir)
        config_files = self._write_config_snapshot(config_dir=config_dir)
        manifest = self._build_manifest(
            backup_dir=backup_dir,
            db_metadata=db_metadata,
            dump_info=dump_info,
            file_count=copied_files,
            config_files=config_files,
        )
        self._write_json(backup_dir / "manifest.json", manifest)
        self._write_checksums(backup_dir)
        log_event("backup_created", status="completed")
        return BackupSummary(
            backup_dir=str(backup_dir),
            created_at=str(manifest["created_at"]),
            manifest_path=str(backup_dir / "manifest.json"),
            database_dump_path=str(db_dir / DATABASE_DUMP_FILENAME),
            file_count=copied_files,
            config_files=config_files,
            workspace_count=int(manifest["workspace_count"]),
            document_count=int(manifest["document_count"]),
            alembic_revision=manifest.get("alembic_revision"),
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

    def verify_backup(self, *, input_dir: str | Path) -> dict[str, Any]:
        backup_dir = Path(input_dir)
        manifest_path = backup_dir / "manifest.json"
        checksum_path = backup_dir / "checksums.json"
        if not manifest_path.exists():
            raise BackupRestoreError("manifest.json is missing")
        if not checksum_path.exists():
            raise BackupRestoreError("checksums.json is missing")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        checksums = json.loads(checksum_path.read_text(encoding="utf-8"))
        issues: list[dict[str, str]] = []
        checks = {
            "db_dump_readable": self._check_database_dump_readable(backup_dir=backup_dir, manifest=manifest, issues=issues),
            "required_files_present": self._check_required_files_present(backup_dir=backup_dir, manifest=manifest, issues=issues),
            "manifest_consistent": self._check_manifest_consistent(backup_dir=backup_dir, manifest=manifest, issues=issues),
            "checksums_valid": self._check_checksums(backup_dir=backup_dir, checksums=checksums, issues=issues),
            "upload_files_complete": self._check_upload_files_complete(backup_dir=backup_dir, issues=issues),
            "restore_dry_run": self._check_restore_dry_run(backup_dir=backup_dir, manifest=manifest, issues=issues),
        }
        error_classes = sorted({issue["code"] for issue in issues})
        result = {
            "status": "ok" if not issues else "invalid",
            "backup_dir": str(backup_dir),
            "checked_at": datetime.now(UTC).isoformat(),
            "integrity_report": {
                "checks": checks,
                "issue_count": len(issues),
                "issues": issues,
            },
            "error_classes": error_classes,
            "mismatch_count": len(issues),
            "mismatches": [f"{issue['code']}:{issue['path']}" for issue in issues],
            "manifest": manifest,
        }
        log_event("backup_validated", status="completed" if not issues else "failed")
        return result

    def restore_backup(self, *, input_dir: str | Path) -> dict[str, Any]:
        backup_dir = Path(input_dir)
        correlation_id = get_observability_context().correlation_id
        with self._restore_runtime_marker(correlation_id=correlation_id):
            log_event("backup_restore_started", status="started")
            validation = self.verify_backup(input_dir=backup_dir)
            if validation["status"] != "ok":
                raise BackupRestoreError("Backup validation failed before restore")

            self._ensure_database_is_empty()
            self._run_alembic_upgrade_head()
            self._restore_database_dump(db_dir=backup_dir / "db")
            restored_files = self._restore_original_files(files_dir=backup_dir / "files")
            config_check = self._validate_restored_config(config_dir=backup_dir / "config")
            reindex_result = self._rebuild_search_index()
            drift_check = self._run_drift_check()
            truth_smoke = self._run_postgres_truth_smoke_subset()
            result = {
                "status": "completed",
                "validation": validation,
                "restored_files": restored_files,
                "config_check": config_check,
                "reindex_result": reindex_result,
                "drift_check": drift_check,
                "truth_smoke": truth_smoke,
                "restored_at": datetime.now(UTC).isoformat(),
            }
            log_event("backup_restored", status="completed")
            return result

    def rebuild_search_index(self, *, workspace_id: str | None = None) -> dict[str, Any]:
        result = self._rebuild_search_index(workspace_id=workspace_id)
        log_event("backup_search_rebuild", status="completed")
        return result

    def _collect_database_metadata(self) -> dict[str, Any]:
        with connect(get_database_url(), row_factory=dict_row, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select count(*) as count from workspaces")
                workspace_count = int(cursor.fetchone()["count"])
                cursor.execute("select count(*) as count from documents")
                document_count = int(cursor.fetchone()["count"])
        return {
            "workspace_count": workspace_count,
            "document_count": document_count,
            "logical_components": list(DATABASE_LOGICAL_COMPONENTS),
        }

    def _create_database_dump(self, *, db_dir: Path) -> dict[str, str]:
        dump_path = db_dir / DATABASE_DUMP_FILENAME
        version_path = db_dir / DATABASE_VERSION_FILENAME
        command = [
            self._require_executable("pg_dump"),
            f"--file={dump_path}",
            "--format=plain",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            get_database_url(),
        ]
        self._run_process(command)
        version_output = self._run_process([self._require_executable("pg_dump"), "--version"], capture_output=True)
        version_path.write_text(version_output.strip() + "\n", encoding="utf-8")
        return {
            "database_dump_path": f"db/{DATABASE_DUMP_FILENAME}",
            "pg_dump_version_path": f"db/{DATABASE_VERSION_FILENAME}",
            "pg_dump_version": version_output.strip(),
            "database_dump_format": "postgresql-sql",
        }

    def _restore_database_dump(self, *, db_dir: Path) -> None:
        dump_path = db_dir / DATABASE_DUMP_FILENAME
        if not dump_path.exists():
            raise BackupRestoreError(f"Database dump is missing: {dump_path}")
        command = [
            self._require_executable("psql"),
            get_database_url(),
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            str(dump_path),
        ]
        self._run_process(command)

    def _copy_original_files(self, *, files_dir: Path) -> int:
        version_rows = self._load_document_version_rows()
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

    def _load_document_version_rows(self) -> list[dict[str, Any]]:
        with connect(get_database_url(), row_factory=dict_row, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select metadata from document_versions order by 1")
                return list(cursor.fetchall())

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
        file_name = CONFIG_SNAPSHOT_FILENAME
        self._write_json(config_dir / file_name, config_payload)
        return [f"config/{file_name}"]

    def _validate_restored_config(self, *, config_dir: Path) -> dict[str, Any]:
        snapshot_path = config_dir / CONFIG_SNAPSHOT_FILENAME
        if not snapshot_path.exists():
            raise BackupRestoreError(f"Config snapshot is missing: {snapshot_path}")

        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        current = {
            "app_env": settings.app_env,
            "default_workspace_id": settings.default_workspace_id,
            "default_user_id": settings.default_user_id,
            "max_upload_size_bytes": settings.max_upload_size_bytes,
            "import_jobs_temp_dir": settings.import_jobs_temp_dir,
            "original_file_store_dir": str(self._original_file_store.root_dir),
        }
        mismatches = {
            key: {
                "expected": snapshot.get(key),
                "actual": current.get(key),
            }
            for key in current
            if snapshot.get(key) != current.get(key)
        }
        return {
            "status": "ok" if not mismatches else "mismatch",
            "checked_keys": sorted(current.keys()),
            "mismatches": mismatches,
        }

    def _run_drift_check(self) -> dict[str, Any]:
        engine = get_engine()
        with Session(engine) as session:
            report = SearchIndexRebuildService.from_session(session).inspect_drift()
        if report.get("status") != "ok":
            raise BackupRestoreError(f"Restore drift check failed: status={report.get('status')}")
        return report

    def _run_postgres_truth_smoke_subset(self) -> dict[str, Any]:
        command = [
            self._python_executable(),
            "-m",
            "pytest",
            "-q",
            *RESTORE_SMOKE_TESTS,
        ]
        environment = os.environ.copy()
        environment["TEST_DATABASE_URL"] = get_sqlalchemy_database_url()
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).resolve().parents[2]),
                env=environment,
            )
        except subprocess.CalledProcessError as exc:
            output = ((exc.stdout or "") + "\n" + (exc.stderr or "")).strip()
            raise BackupRestoreError(f"postgres_truth smoke subset failed: {output}") from exc
        return {
            "status": "passed",
            "command": " ".join(command[2:]),
            "tests": list(RESTORE_SMOKE_TESTS),
            "output": (completed.stdout or "").strip(),
        }

    def _build_manifest(
        self,
        *,
        backup_dir: Path,
        db_metadata: dict[str, Any],
        dump_info: dict[str, str],
        file_count: int,
        config_files: list[str],
    ) -> dict[str, Any]:
        return {
            "backup_format_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "app_version": self._get_app_version(),
            "alembic_revision": self._get_alembic_revision(),
            "workspace_scope": "all",
            "database_dump_format": dump_info["database_dump_format"],
            "database_dump_path": dump_info["database_dump_path"],
            "pg_dump_version": dump_info["pg_dump_version"],
            "pg_dump_version_path": dump_info["pg_dump_version_path"],
            "workspace_count": db_metadata["workspace_count"],
            "document_count": db_metadata["document_count"],
            "logical_components": db_metadata["logical_components"],
            "file_count": file_count,
            "config_files": config_files,
            "search_index_included": False,
            "original_file_root": str(self._original_file_store.root_dir),
            "backup_dir": str(backup_dir),
        }

    def _check_database_dump_readable(self, *, backup_dir: Path, manifest: dict[str, Any], issues: list[dict[str, str]]) -> dict[str, Any]:
        dump_relative_path = manifest.get("database_dump_path")
        if not isinstance(dump_relative_path, str) or not dump_relative_path:
            issues.append(self._verification_issue("manifest-missing-field", "manifest.json", "database_dump_path missing in manifest"))
            return {"status": "invalid", "path": None}

        dump_path = backup_dir / dump_relative_path
        if not dump_path.exists():
            issues.append(self._verification_issue("missing-database-dump", dump_relative_path, "database dump file is missing"))
            return {"status": "invalid", "path": dump_relative_path}

        try:
            with dump_path.open("r", encoding="utf-8") as handle:
                preview = handle.read(4096)
        except OSError as exc:
            issues.append(self._verification_issue("database-dump-unreadable", dump_relative_path, str(exc)))
            return {"status": "invalid", "path": dump_relative_path}

        sql_markers = ("CREATE ", "INSERT ", "COPY ", "SET ", "ALTER ", "DROP ")
        if not preview or not any(marker in preview for marker in sql_markers):
            issues.append(self._verification_issue("database-dump-unreadable", dump_relative_path, "database dump does not look like a readable SQL dump"))
            return {"status": "invalid", "path": dump_relative_path}

        return {"status": "ok", "path": dump_relative_path}

    def _check_required_files_present(self, *, backup_dir: Path, manifest: dict[str, Any], issues: list[dict[str, str]]) -> dict[str, Any]:
        required_paths = [
            "manifest.json",
            "checksums.json",
            manifest.get("database_dump_path") or f"db/{DATABASE_DUMP_FILENAME}",
            manifest.get("pg_dump_version_path") or f"db/{DATABASE_VERSION_FILENAME}",
        ]
        required_paths.extend(path for path in manifest.get("config_files", []) if isinstance(path, str))

        missing_paths: list[str] = []
        for relative_path in required_paths:
            candidate = backup_dir / relative_path
            if not candidate.exists():
                missing_paths.append(relative_path)
                issues.append(self._verification_issue("missing-file", relative_path, "required backup artifact is missing"))

        return {"status": "ok" if not missing_paths else "invalid", "missing_paths": missing_paths}

    def _check_manifest_consistent(self, *, backup_dir: Path, manifest: dict[str, Any], issues: list[dict[str, str]]) -> dict[str, Any]:
        required_fields = [
            "backup_format_version",
            "created_at",
            "database_dump_format",
            "database_dump_path",
            "pg_dump_version",
            "pg_dump_version_path",
            "logical_components",
            "file_count",
            "config_files",
        ]
        missing_fields = [field for field in required_fields if manifest.get(field) in (None, "")]
        for field in missing_fields:
            issues.append(self._verification_issue("manifest-missing-field", "manifest.json", f"manifest field missing: {field}"))

        actual_file_count = sum(1 for file_path in (backup_dir / "files").rglob("*") if file_path.is_file()) if (backup_dir / "files").exists() else 0
        declared_file_count = manifest.get("file_count")
        if isinstance(declared_file_count, int) and declared_file_count != actual_file_count:
            issues.append(
                self._verification_issue(
                    "manifest-file-count-mismatch",
                    "manifest.json",
                    f"manifest file_count={declared_file_count} but files/ contains {actual_file_count} file(s)",
                )
            )

        dump_path = manifest.get("database_dump_path")
        if isinstance(dump_path, str) and not (backup_dir / dump_path).exists():
            issues.append(self._verification_issue("manifest-path-missing", dump_path, "manifest references a missing database dump"))

        config_files = [path for path in manifest.get("config_files", []) if isinstance(path, str)]
        for relative_path in config_files:
            if not (backup_dir / relative_path).exists():
                issues.append(self._verification_issue("manifest-path-missing", relative_path, "manifest references a missing config file"))

        return {
            "status": "ok" if not missing_fields and not any(issue["code"].startswith("manifest-") for issue in issues) else "invalid",
            "declared_file_count": declared_file_count,
            "actual_file_count": actual_file_count,
            "missing_fields": missing_fields,
        }

    def _check_checksums(self, *, backup_dir: Path, checksums: dict[str, str], issues: list[dict[str, str]]) -> dict[str, Any]:
        mismatches: list[str] = []
        missing_paths: list[str] = []
        invalid_entries: list[str] = []
        for relative_path, expected_hash in checksums.items():
            if not isinstance(expected_hash, str) or len(expected_hash) != 64:
                invalid_entries.append(relative_path)
                issues.append(self._verification_issue("checksum-entry-invalid", relative_path, "checksum entry must be a sha256 hex digest"))
                continue
            candidate = backup_dir / relative_path
            if not candidate.exists():
                missing_paths.append(relative_path)
                issues.append(self._verification_issue("missing-file", relative_path, "file referenced by checksum is missing"))
                continue
            actual_hash = self._hash_file(candidate)
            if actual_hash != expected_hash:
                mismatches.append(relative_path)
                issues.append(self._verification_issue("checksum-mismatch", relative_path, "checksum mismatch"))

        return {
            "status": "ok" if not mismatches and not missing_paths and not invalid_entries else "invalid",
            "mismatches": mismatches,
            "missing_paths": missing_paths,
            "invalid_entries": invalid_entries,
        }

    def _check_upload_files_complete(self, *, backup_dir: Path, issues: list[dict[str, str]]) -> dict[str, Any]:
        files_dir = backup_dir / "files"
        missing_uploads: list[str] = []
        if files_dir.exists():
            for file_path in files_dir.rglob("*"):
                if file_path.is_file():
                    continue
                # only files matter; empty directories are allowed
        else:
            missing_uploads.append("files/")
            issues.append(self._verification_issue("missing-upload-file", "files/", "upload files directory is missing"))

        return {"status": "ok" if not missing_uploads else "invalid", "missing_paths": missing_uploads}

    def _check_restore_dry_run(self, *, backup_dir: Path, manifest: dict[str, Any], issues: list[dict[str, str]]) -> dict[str, Any]:
        dump_relative_path = manifest.get("database_dump_path")
        dump_path = backup_dir / dump_relative_path if isinstance(dump_relative_path, str) else None
        try:
            probe = self._simulate_restore_probe(dump_path=dump_path)
        except (BackupVerificationDryRunError, BackupRestoreError) as exc:
            issues.append(self._verification_issue("restore-dry-run-failed", str(dump_relative_path or "db/"), str(exc)))
            return {"status": "invalid", "details": str(exc)}
        return {"status": "ok", "details": probe}

    def _simulate_restore_probe(self, *, dump_path: Path | None) -> str:
        if dump_path is None or not dump_path.exists():
            raise BackupVerificationDryRunError("restore probe requires an existing database dump")
        self._require_executable("psql")
        preview = dump_path.read_text(encoding="utf-8")
        if "CREATE TABLE" not in preview and "INSERT INTO" not in preview and "COPY " not in preview:
            raise BackupVerificationDryRunError("database dump does not contain recognizable restore statements")
        return "psql available and SQL restore statements detected"

    def _verification_issue(self, code: str, path: str, detail: str) -> dict[str, str]:
        return {"code": code, "path": path, "detail": detail}

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
                for table_name in [
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
                ]:
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

    def _get_alembic_revision(self) -> str | None:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        script_location = config.get_main_option("script_location") or "migrations"
        script_dir = Path(__file__).resolve().parents[2] / script_location
        versions_dir = script_dir / "versions"
        if not versions_dir.exists():
            return None
        revisions = sorted(path.stem for path in versions_dir.glob("*.py") if path.name != "__init__.py")
        return revisions[-1] if revisions else None

    def _get_app_version(self) -> str:
        try:
            return package_version("wissensbasis-backend")
        except PackageNotFoundError:
            return "0.1.0"

    def _hash_file(self, path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _require_executable(self, executable_name: str) -> str:
        resolved = shutil.which(executable_name)
        if not resolved:
            raise BackupRestoreError(f"Required executable not found: {executable_name}")
        return resolved

    def _run_process(self, command: list[str], *, capture_output: bool = False) -> str:
        environment = os.environ.copy()
        database_url = get_database_url()
        parsed = urlparse(database_url)
        if parsed.password:
            environment["PGPASSWORD"] = parsed.password
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=capture_output,
                text=True,
                env=environment,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else str(exc)
            raise BackupRestoreError(f"Command failed: {' '.join(command)} :: {stderr}") from exc
        return completed.stdout if capture_output else ""

    def _python_executable(self) -> str:
        return os.environ.get("PYTHON_EXECUTABLE") or os.sys.executable

    def _write_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")

    @contextmanager
    def _restore_runtime_marker(self, *, correlation_id: str | None):
        RESTORE_RUNTIME_STATUS.parent.mkdir(parents=True, exist_ok=True)
        RESTORE_RUNTIME_STATUS.write_text(
            json.dumps(
                {
                    "active": True,
                    "started_at": datetime.now(UTC).isoformat(),
                    "correlation_id": correlation_id,
                },
                ensure_ascii=True,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        try:
            yield
        finally:
            if RESTORE_RUNTIME_STATUS.exists():
                RESTORE_RUNTIME_STATUS.unlink()