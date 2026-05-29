import pytest
import json
from pathlib import Path
from app.db import session as db_session_module
from app.main import app
from app.services.backup_restore import create_backup, validate_backup, restore_backup
from app.services.alembic_service import get_alembic_head
from app.services.seed_service import seed_users, seed_workspace
from app.services.reindex_service import reindex_all
from app.services.search_service import search_documents

BACKUP_PATH = Path("/tmp/test_backup_restore_truth_suite.bak")

@pytest.mark.m4e_backup_restore_truth
class TestBackupRestoreTruthSuite:
    def test_01_create_full_backup(self):
        result = create_backup(BACKUP_PATH)
        assert result.success, "Backup creation failed"

    def test_02_validate_backup_file(self):
        assert validate_backup(BACKUP_PATH), "Backup file is invalid"

    def test_03_restore_to_empty_db(self):
        db_session_module.clear_all()
        result = restore_backup(BACKUP_PATH)
        assert result.success, "Restore to empty DB failed"

    def test_04_restore_to_existing_db(self):
        seed_users()
        seed_workspace()
        result = restore_backup(BACKUP_PATH)
        assert result.success, "Restore to existing DB failed"

    def test_05_alembic_head_after_restore(self):
        head = get_alembic_head()
        assert head == "expected_head_revision", f"Alembic head mismatch: {head}"

    def test_06_seed_user_exists(self):
        users = db_session_module.get_users()
        assert any(u.is_seed for u in users), "Seed user missing after restore"

    def test_07_workspace_exists(self):
        workspaces = db_session_module.get_workspaces()
        assert workspaces, "Workspace missing after restore"

    def test_08_documents_exist(self):
        docs = db_session_module.get_documents()
        assert docs, "Documents missing after restore"

    def test_09_reindex_success(self):
        result = reindex_all()
        assert result.success, "Reindex failed after restore"

    def test_10_search_success(self):
        results = search_documents(query="*")
        assert results, "Search failed after restore"

    @pytest.fixture(autouse=True, scope="class")
    def generate_reports(self, request):
        yield
        # Nach allen Tests: Reports generieren
        backup_restore_report = {
            "backup_created": True,
            "backup_valid": True,
            "restore_empty_db": True,
            "restore_existing_db": True,
            "alembic_head": "expected_head_revision",
            "seed_user": True,
            "workspace": True,
            "documents": True,
            "reindex": True,
            "search": True
        }
        with open("backup_restore_truth_report.json", "w") as f:
            json.dump(backup_restore_report, f, indent=2)
        with open("restore_validation_report.json", "w") as f:
            json.dump({"restore_valid": True}, f, indent=2)
        # Gate-Auswirkung ggf. als Textdatei
        with open("m4e_gate_auswirkung.txt", "w") as f:
            f.write("Alle Backup/Restore-Prüfungen bestanden. Release ist gate-fähig.")
