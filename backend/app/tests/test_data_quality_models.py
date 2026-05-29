import pytest
from datetime import datetime
from backend.app.models.data_quality import (
    DataQualityRun, DataQualityFinding, DataQualityMetric, DataQualitySnapshot, DataQualityFindingType
)

def test_data_quality_finding_fields():
    finding = DataQualityFinding(
        run_id=1,
        workspace_id="ws1",
        finding_type=DataQualityFindingType.DUPLICATE_DOCUMENT,
        severity="high",
        document_id="doc1",
        version_id=None,
        chunk_id=None,
        source_status="active",
        title="Duplicate Document",
        description="Document doc1 is a duplicate.",
        remediation="Remove duplicate.",
        created_at=datetime.utcnow(),
    )
    assert finding.workspace_id == "ws1"
    assert finding.finding_type == DataQualityFindingType.DUPLICATE_DOCUMENT
    assert finding.severity == "high"
    assert finding.title == "Duplicate Document"
    assert finding.remediation == "Remove duplicate."

def test_data_quality_run_fields():
    run = DataQualityRun(
        workspace_id="ws1",
        started_at=datetime.utcnow(),
        finished_at=None,
        metrics={"total_documents": 100}
    )
    assert run.workspace_id == "ws1"
    assert "total_documents" in run.metrics

def test_data_quality_metric_fields():
    metric = DataQualityMetric(
        run_id=1,
        name="duplicate_documents",
        value=5,
        created_at=datetime.utcnow()
    )
    assert metric.name == "duplicate_documents"
    assert metric.value == 5

def test_data_quality_snapshot_fields():
    snapshot = DataQualitySnapshot(
        workspace_id="ws1",
        taken_at=datetime.utcnow(),
        metrics={"score": 0.98},
        findings={"count": 2}
    )
    assert snapshot.workspace_id == "ws1"
    assert snapshot.metrics["score"] == 0.98
