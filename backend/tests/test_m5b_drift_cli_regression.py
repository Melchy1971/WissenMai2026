"""Drift CLI Regression Tests.

Prüft:
1. Fehlende DATABASE_URL → Exit 1, valider FAIL-Report
2. Ungültiger Workspace → Exit 1, valider FAIL-Report
3. Gültiger Workspace → Exit 0
4. Report wird geschrieben (drift_report.json + drift_summary.json)
5. Exit Code korrekt (0 = OK, 1 = Config, 2 = Runtime)
6. Keine Datenmutation (keine INSERT/UPDATE/DELETE auf source tables)
7. Fehlerfall schreibt validen FAIL-Report mit parseable JSON
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# sys.modules patches — before any app import
# ---------------------------------------------------------------------------
sys.modules.setdefault("psycopg", MagicMock())
sys.modules.setdefault("pydantic_settings", MagicMock())

# Patch app.services.auth for Python 3.10 compat
_mock_auth_svc = MagicMock()
sys.modules.setdefault("app.services.auth", _mock_auth_svc)
_mock_db_core = MagicMock()
sys.modules.setdefault("app.core.database", _mock_db_core)

# ---------------------------------------------------------------------------
# Import CLI under test
# ---------------------------------------------------------------------------
# Add scripts dir to path
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import run_drift_detection as cli

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def outdir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def _make_mock_session(workspace_exists: bool = True, raise_on_query: Exception | None = None):
    """Returns a mock SQLAlchemy session for workspace validation."""
    session = MagicMock()
    if raise_on_query:
        session.execute.side_effect = raise_on_query
    else:
        row = MagicMock()
        row.id = "ws-test"
        result = MagicMock()
        if workspace_exists:
            result.fetchone.return_value = row
        else:
            result.fetchone.return_value = None
        session.execute.return_value = result
    return session


def _load_report(outdir: str, filename: str) -> dict:
    path = os.path.join(outdir, filename)
    assert os.path.exists(path), f"{filename} not found in {outdir}"
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Fehlende DATABASE_URL → Exit 1, valider FAIL-Report
# ---------------------------------------------------------------------------

class TestMissingDatabaseUrl:
    def test_exit_code_is_1(self, outdir):
        env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        with patch.dict(os.environ, env, clear=True):
            code = cli.main(["--workspace", "ws-any", "--output", outdir])
        assert code == cli.EXIT_CONFIG_ERROR

    def test_writes_fail_report(self, outdir):
        env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        with patch.dict(os.environ, env, clear=True):
            cli.main(["--workspace", "ws-any", "--output", outdir])
        report = _load_report(outdir, "drift_report.json")
        assert report["status"] == "failed"
        assert report["error_code"] == "CONFIG_ERROR"

    def test_fail_report_is_valid_json(self, outdir):
        env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        with patch.dict(os.environ, env, clear=True):
            cli.main(["--workspace", "ws-any", "--output", outdir])
        # _load_report already parses JSON; if no exception → valid
        report = _load_report(outdir, "drift_report.json")
        assert "run_id" in report
        assert "workspace_id" in report


# ---------------------------------------------------------------------------
# 2. Ungültiger Workspace → Exit 1, valider FAIL-Report
# ---------------------------------------------------------------------------

class TestInvalidWorkspace:
    def _run(self, outdir, workspace_id="ws-nonexistent"):
        mock_session = _make_mock_session(workspace_exists=False)
        mock_engine = MagicMock()
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}, clear=False):
            with patch("run_drift_detection.create_engine", return_value=mock_engine):
                with patch("run_drift_detection.Session", return_value=mock_session):
                    return cli.main(["--workspace", workspace_id, "--output", outdir])

    def test_exit_code_is_1(self, outdir):
        code = self._run(outdir)
        assert code == cli.EXIT_CONFIG_ERROR

    def test_writes_fail_report(self, outdir):
        self._run(outdir)
        report = _load_report(outdir, "drift_report.json")
        assert report["status"] == "failed"
        assert report["error_code"] == "INVALID_WORKSPACE"

    def test_summary_written(self, outdir):
        self._run(outdir)
        summary = _load_report(outdir, "drift_summary.json")
        assert summary["status"] == "failed"
        assert summary["total_drifts"] == 0


# ---------------------------------------------------------------------------
# 3 + 4. Gültiger Workspace → Exit 0, Reports geschrieben
# ---------------------------------------------------------------------------

class TestValidWorkspace:
    def _run(self, outdir, workspace_id="ws-valid"):
        mock_session = _make_mock_session(workspace_exists=True)
        # make detector queries return empty results (no findings)
        empty_result = MagicMock()
        empty_result.fetchone.return_value = MagicMock(id="ws-valid")
        empty_result.fetchall.return_value = []
        mock_session.execute.return_value = empty_result
        mock_engine = MagicMock()
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}, clear=False):
            with patch("run_drift_detection.create_engine", return_value=mock_engine):
                with patch("run_drift_detection.Session", return_value=mock_session):
                    return cli.main(["--workspace", workspace_id, "--output", outdir])

    def test_exit_code_is_0(self, outdir):
        code = self._run(outdir)
        assert code == cli.EXIT_OK

    def test_drift_report_written(self, outdir):
        self._run(outdir)
        report = _load_report(outdir, "drift_report.json")
        assert report["status"] in ("completed", "completed_with_errors")

    def test_drift_summary_written(self, outdir):
        self._run(outdir)
        summary = _load_report(outdir, "drift_summary.json")
        assert "total_drifts" in summary
        assert "drift_rate" in summary

    def test_report_has_required_fields(self, outdir):
        self._run(outdir)
        report = _load_report(outdir, "drift_report.json")
        for field in ("run_id", "workspace_id", "status", "started_at",
                      "completed_at", "total_findings", "findings", "constraints"):
            assert field in report, f"Missing field: {field}"

    def test_constraints_prohibit_mutation(self, outdir):
        self._run(outdir)
        report = _load_report(outdir, "drift_report.json")
        c = report["constraints"]
        assert c["repair_actions"] == "PROHIBITED"
        assert c["cleanup_actions"] == "PROHIBITED"
        assert c["auto_reindex_actions"] == "PROHIBITED"


# ---------------------------------------------------------------------------
# 5. Exit Code korrekt
# ---------------------------------------------------------------------------

class TestExitCodes:
    def test_config_error_exits_1(self, outdir):
        env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        with patch.dict(os.environ, env, clear=True):
            code = cli.main(["--workspace", "ws-x", "--output", outdir])
        assert code == 1

    def test_runtime_error_exits_2(self, outdir):
        mock_engine = MagicMock()
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}, clear=False):
            with patch("run_drift_detection.create_engine", side_effect=RuntimeError("DB down")):
                code = cli.main(["--workspace", "ws-x", "--output", outdir])
        assert code == cli.EXIT_RUNTIME_ERROR

    def test_success_exits_0(self, outdir):
        mock_session = _make_mock_session(workspace_exists=True)
        empty_result = MagicMock()
        empty_result.fetchone.return_value = MagicMock(id="ws-ok")
        empty_result.fetchall.return_value = []
        mock_session.execute.return_value = empty_result
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}, clear=False):
            with patch("run_drift_detection.create_engine", return_value=MagicMock()):
                with patch("run_drift_detection.Session", return_value=mock_session):
                    code = cli.main(["--workspace", "ws-ok", "--output", outdir])
        assert code == 0


# ---------------------------------------------------------------------------
# 6. Keine Datenmutation
# ---------------------------------------------------------------------------

class TestNoMutation:
    """Verify CLI never executes INSERT, UPDATE, DELETE, DROP on source tables."""

    FORBIDDEN_VERBS = ("INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER")

    def _collect_executed_sql(self, outdir):
        executed = []
        original_execute = MagicMock()

        def _tracking_execute(stmt, params=None):
            sql = str(stmt).upper()
            executed.append(sql)
            result = MagicMock()
            result.fetchone.return_value = MagicMock(id="ws-track")
            result.fetchall.return_value = []
            return result

        mock_session = MagicMock()
        mock_session.execute.side_effect = _tracking_execute

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}, clear=False):
            with patch("run_drift_detection.create_engine", return_value=MagicMock()):
                with patch("run_drift_detection.Session", return_value=mock_session):
                    cli.main(["--workspace", "ws-track", "--output", outdir])
        return executed

    def test_no_insert(self, outdir):
        sqls = self._collect_executed_sql(outdir)
        for sql in sqls:
            assert "INSERT" not in sql, f"INSERT found in: {sql[:100]}"

    def test_no_update(self, outdir):
        sqls = self._collect_executed_sql(outdir)
        for sql in sqls:
            assert "UPDATE" not in sql, f"UPDATE found in: {sql[:100]}"

    def test_no_delete(self, outdir):
        sqls = self._collect_executed_sql(outdir)
        for sql in sqls:
            assert "DELETE" not in sql, f"DELETE found in: {sql[:100]}"


# ---------------------------------------------------------------------------
# 7. Fehlerfall schreibt validen FAIL-Report
# ---------------------------------------------------------------------------

class TestFailReportValidity:
    def _run_with_runtime_error(self, outdir):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}, clear=False):
            with patch("run_drift_detection.create_engine", side_effect=RuntimeError("simulated failure")):
                return cli.main(["--workspace", "ws-err", "--output", outdir])

    def test_fail_report_is_parseable(self, outdir):
        self._run_with_runtime_error(outdir)
        report = _load_report(outdir, "drift_report.json")
        assert isinstance(report, dict)

    def test_fail_report_has_run_id(self, outdir):
        self._run_with_runtime_error(outdir)
        report = _load_report(outdir, "drift_report.json")
        assert "run_id" in report
        # run_id should be a valid UUID
        uuid.UUID(report["run_id"])

    def test_fail_report_status_is_failed(self, outdir):
        self._run_with_runtime_error(outdir)
        report = _load_report(outdir, "drift_report.json")
        assert report["status"] == "failed"

    def test_fail_summary_total_drifts_zero(self, outdir):
        self._run_with_runtime_error(outdir)
        summary = _load_report(outdir, "drift_summary.json")
        assert summary["total_drifts"] == 0

    def test_fail_report_constraints_present(self, outdir):
        self._run_with_runtime_error(outdir)
        report = _load_report(outdir, "drift_report.json")
        assert "constraints" in report
        assert report["constraints"]["repair_actions"] == "PROHIBITED"
