from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import text

from backend.tests import test_data_quality_runner as _runner_tests
from backend.tests.test_run_data_quality_report_v2 import *  # noqa: F401,F403


engine = _runner_tests.engine
session = _runner_tests.session
TestCalculateScore = _runner_tests.TestCalculateScore
TestDataQualityRunnerLifecycle = _runner_tests.TestDataQualityRunnerLifecycle


class TestSkeletonDetectors(_runner_tests.TestSkeletonDetectors):
    def test_invalid_lifecycle_finding_shape(self, session, engine):
        """Detector returns correctly shaped dicts when lifecycle drift exists."""
        wid = _runner_tests._workspace_id()
        _runner_tests._seed_workspace(session, wid)
        session.execute(text("PRAGMA ignore_check_constraints=ON"))
        session.execute(
            text(
                """
                INSERT INTO documents (
                    id, workspace_id, owner_user_id, title, source_type,
                    content_hash, import_status, lifecycle_status, created_at, updated_at
                )
                VALUES (
                    :id, :workspace_id, :owner_user_id, :title, :source_type,
                    :content_hash, :import_status, :lifecycle_status, :created_at, :updated_at
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "workspace_id": wid,
                "owner_user_id": "u1",
                "title": "doc",
                "source_type": "upload",
                "content_hash": "abc",
                "import_status": "parsed",
                "lifecycle_status": "INVALID",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        session.execute(text("PRAGMA ignore_check_constraints=OFF"))

        findings = _runner_tests.InvalidLifecycleDetector(session, wid).detect()

        assert findings
        for finding in findings:
            assert "finding_type" in finding
            assert "severity" in finding
            assert "title" in finding
            assert "description" in finding
            assert "remediation" in finding
            assert "remediation_applied" not in finding
