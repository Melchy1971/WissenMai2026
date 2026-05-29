import pytest
from backend.app.services.duplicate_detector import DuplicateDetector
from backend.app.models.data_quality import DataQualityFindingType

class DummySession:
    pass

def test_duplicate_detector_findings(monkeypatch):
    detector = DuplicateDetector(DummySession(), workspace_id="ws1")
    # Patch the internal methods to simulate duplicates
    monkeypatch.setattr(detector, "_find_duplicates_by_field", lambda field: {"docA": ["docB"]} if field == "content_hash" else {})
    monkeypatch.setattr(detector, "_find_duplicates_by_title_and_content", lambda: {"docC": ["docD"]})
    monkeypatch.setattr(detector, "_find_duplicate_versions", lambda: {"ver1": ["ver2"]})
    findings = detector.detect()
    assert any(f.title == "Duplicate by content_hash" and f.severity == "high" for f in findings)
    assert any(f.title == "Duplicate by title and content" and f.severity == "medium" for f in findings)
    assert any(f.title == "Duplicate Version" and f.severity == "low" for f in findings)
    assert all(f.remediation for f in findings)
    assert all(f.finding_type in [DataQualityFindingType.DUPLICATE_DOCUMENT, DataQualityFindingType.DUPLICATE_CONTENT] for f in findings)
