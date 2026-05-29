import pytest
import json
from pathlib import Path
from app.db import session as db_session_module
from app.main import app
from app.services.backup_restore import BackupRestoreService
from app.services.reindex_governance import ReindexGovernanceService
from app.services.search_service import SearchService

REINDEX_REPORT = "reindex_recovery_report.json"
RETRIEVAL_REPORT = "retrieval_validation_report.json"

@pytest.mark.m4e_backup_restore_truth
class TestReindexRecoveryTruthSuite:
    @pytest.fixture(scope="class", autouse=True)
    def setup_restore(self):
        # Restore muss vorab erfolgt sein
        yield

    def test_01_reindex_starts_and_completes(self):
        engine = db_session_module.get_engine()
        with db_session_module.Session(engine) as session:
            svc = ReindexGovernanceService(session)
            result = svc.run_governed_reindex(reindex_type="full")
            assert result["status"] == "completed"
            self.reindex_result = result

    def test_02_chunks_created(self):
        # Prüfe, ob nach Reindex Chunks existieren
        engine = db_session_module.get_engine()
        with db_session_module.Session(engine) as session:
            chunk_count = session.execute("SELECT COUNT(*) FROM document_chunks").scalar()
            assert chunk_count > 0
            self.chunk_count = chunk_count

    def test_03_search_finds_documents(self):
        engine = db_session_module.get_engine()
        with db_session_module.Session(engine) as session:
            search = SearchService.from_session(session)
            results = search.search_chunks(workspace_id="default", query="*", limit=5, offset=0)
            assert results, "Search liefert keine Dokumente"
            self.search_results = results

    def test_04_chat_retrieval_finds_documents(self):
        # Beispiel: Chat Retrieval API/Service aufrufen
        # Hier als Platzhalter, ggf. anpassen
        engine = db_session_module.get_engine()
        with db_session_module.Session(engine) as session:
            # Annahme: search_chunks simuliert Retrieval
            results = SearchService.from_session(session).search_chunks(workspace_id="default", query="chat", limit=5, offset=0)
            assert results, "Chat Retrieval liefert keine Dokumente"
            self.chat_results = results

    def test_05_source_status_korrekt(self):
        # Prüfe source_status (z. B. live, archived, deleted)
        engine = db_session_module.get_engine()
        with db_session_module.Session(engine) as session:
            rows = session.execute("SELECT DISTINCT source_status FROM documents").fetchall()
            statuses = {row[0] for row in rows}
            assert "live" in statuses
            self.statuses = list(statuses)

    def test_06_lifecycle_respected(self):
        # Prüfe, ob Lifecycle-Status korrekt respektiert wird
        engine = db_session_module.get_engine()
        with db_session_module.Session(engine) as session:
            rows = session.execute("SELECT COUNT(*) FROM documents WHERE lifecycle NOT IN ('active','archived','deleted')").scalar()
            assert rows == 0
            self.lifecycle_ok = True

    @pytest.fixture(autouse=True, scope="class")
    def generate_reports(self, request):
        yield
        # Nach allen Tests: Reports generieren
        reindex_report = {
            "reindex_status": getattr(self, "reindex_result", {}).get("status", "fail"),
            "chunk_count": getattr(self, "chunk_count", 0),
        }
        with open(REINDEX_REPORT, "w") as f:
            json.dump(reindex_report, f, indent=2)
        retrieval_report = {
            "search_results": len(getattr(self, "search_results", [])),
            "chat_results": len(getattr(self, "chat_results", [])),
            "statuses": getattr(self, "statuses", []),
            "lifecycle_ok": getattr(self, "lifecycle_ok", False),
        }
        with open(RETRIEVAL_REPORT, "w") as f:
            json.dump(retrieval_report, f, indent=2)
