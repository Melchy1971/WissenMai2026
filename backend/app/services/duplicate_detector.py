from typing import List, Optional
from backend.app.models.data_quality import DataQualityFinding, DataQualityFindingType
from datetime import datetime

class DuplicateDetector:
    def __init__(self, db_session, workspace_id: str):
        self.db = db_session
        self.workspace_id = workspace_id

    def detect(self) -> List[DataQualityFinding]:
        findings = []
        now = datetime.utcnow()
        # 1. gleicher content_hash
        content_dupes = self._find_duplicates_by_field('content_hash')
        for doc_id, ids in content_dupes.items():
            findings.append(DataQualityFinding(
                run_id=None,  # to be set by caller
                workspace_id=self.workspace_id,
                finding_type=DataQualityFindingType.DUPLICATE_DOCUMENT,
                severity="high",
                document_id=doc_id,
                version_id=None,
                chunk_id=None,
                source_status=None,
                title="Duplicate by content_hash",
                description=f"Document {doc_id} shares content_hash with {ids}",
                remediation="Prüfen und Duplikate manuell bereinigen.",
                created_at=now
            ))
        # 2. gleicher normalized_text_hash
        text_dupes = self._find_duplicates_by_field('normalized_text_hash')
        for doc_id, ids in text_dupes.items():
            findings.append(DataQualityFinding(
                run_id=None,
                workspace_id=self.workspace_id,
                finding_type=DataQualityFindingType.DUPLICATE_CONTENT,
                severity="medium",
                document_id=doc_id,
                version_id=None,
                chunk_id=None,
                source_status=None,
                title="Duplicate by normalized_text_hash",
                description=f"Document {doc_id} shares normalized_text_hash with {ids}",
                remediation="Prüfen und ggf. konsolidieren.",
                created_at=now
            ))
        # 3. identischer Titel + Inhalt
        title_content_dupes = self._find_duplicates_by_title_and_content()
        for doc_id, ids in title_content_dupes.items():
            findings.append(DataQualityFinding(
                run_id=None,
                workspace_id=self.workspace_id,
                finding_type=DataQualityFindingType.DUPLICATE_DOCUMENT,
                severity="medium",
                document_id=doc_id,
                version_id=None,
                chunk_id=None,
                source_status=None,
                title="Duplicate by title and content",
                description=f"Document {doc_id} has identical title and content as {ids}",
                remediation="Prüfen und ggf. zusammenführen.",
                created_at=now
            ))
        # 4. identische Versionen
        version_dupes = self._find_duplicate_versions()
        for version_id, ids in version_dupes.items():
            findings.append(DataQualityFinding(
                run_id=None,
                workspace_id=self.workspace_id,
                finding_type=DataQualityFindingType.DUPLICATE_CONTENT,
                severity="low",
                document_id=None,
                version_id=version_id,
                chunk_id=None,
                source_status=None,
                title="Duplicate Version",
                description=f"Version {version_id} is identical to {ids}",
                remediation="Versionshistorie prüfen und bereinigen.",
                created_at=now
            ))
        return findings

    def _find_duplicates_by_field(self, field: str) -> dict:
        # Dummy: Replace with real DB query
        # Returns {main_id: [dupe_id1, dupe_id2, ...]}
        return {}

    def _find_duplicates_by_title_and_content(self) -> dict:
        # Dummy: Replace with real DB query
        return {}

    def _find_duplicate_versions(self) -> dict:
        # Dummy: Replace with real DB query
        return {}
