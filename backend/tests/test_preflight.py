"""
Tests für PreflightService (Task C).

Prüft:
  - Alle Checks einzeln (pass/fail/warn)
  - Fail-fast-Verhalten: run_or_raise() wirft bei fail + PREFLIGHT_FAIL_FAST=true
  - Fail-fast deaktiviert: keine Exception trotz Fehler
  - /health/preflight Endpunkt
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from app.services.preflight import PreflightService, PreflightResult, PreflightCheck


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────


def _result_with(checks: list[tuple[str, str]]) -> PreflightResult:
    return PreflightResult(
        checks=[PreflightCheck(id=cid, status=status) for cid, status in checks]  # type: ignore[arg-type]
    )


# ── PreflightResult ───────────────────────────────────────────────────────────


def test_result_passed_when_all_pass_or_warn() -> None:
    result = _result_with([("db", "pass"), ("schema", "warn")])
    assert result.passed is True


def test_result_fails_when_any_fail() -> None:
    result = _result_with([("db", "pass"), ("alembic", "fail")])
    assert result.passed is False


def test_failed_checks_filtered() -> None:
    result = _result_with([("a", "pass"), ("b", "fail"), ("c", "warn")])
    assert [c.id for c in result.failed_checks] == ["b"]


def test_warned_checks_filtered() -> None:
    result = _result_with([("a", "pass"), ("b", "fail"), ("c", "warn")])
    assert [c.id for c in result.warned_checks] == ["c"]


def test_summary_contains_all_statuses() -> None:
    result = _result_with([("db", "pass"), ("alembic", "fail"), ("seed", "warn")])
    summary = result.summary()
    assert "[OK]" in summary
    assert "[FAIL]" in summary
    assert "[WARN]" in summary


def test_as_dict_structure() -> None:
    result = _result_with([("db", "pass")])
    d = result.as_dict()
    assert d["passed"] is True
    assert isinstance(d["checks"], list)
    assert d["checks"][0]["id"] == "db"
    assert d["checks"][0]["status"] == "pass"


# ── PreflightService._check_database_url ─────────────────────────────────────


def test_check_database_url_fail_when_not_set() -> None:
    with patch("app.services.preflight.settings") as mock_settings:
        mock_settings.database_url = None
        mock_settings.app_env = "local"
        svc = PreflightService()
        ok = svc._check_database_url()
    assert ok is False
    assert svc._checks[0].status == "fail"


def test_check_database_url_pass_when_set() -> None:
    with patch("app.services.preflight.settings") as mock_settings:
        mock_settings.database_url = "postgresql+psycopg://u:p@localhost/db"
        mock_settings.app_env = "local"
        svc = PreflightService()
        ok = svc._check_database_url()
    assert ok is True
    assert svc._checks[0].status == "pass"


# ── PreflightService._check_db_reachable ─────────────────────────────────────


def test_check_db_reachable_pass() -> None:
    with patch("app.services.preflight.check_database_connection") as mock_check:
        mock_check.return_value = None
        svc = PreflightService()
        ok = svc._check_db_reachable()
    assert ok is True


def test_check_db_reachable_fail_on_exception() -> None:
    with patch("app.services.preflight.check_database_connection", side_effect=ConnectionError("refused")):
        svc = PreflightService()
        ok = svc._check_db_reachable()
    assert ok is False
    assert svc._checks[0].status == "fail"
    assert "refused" in (svc._checks[0].detail or "")


# ── Fail-fast-Modus ───────────────────────────────────────────────────────────


def test_run_or_raise_does_not_raise_when_passed() -> None:
    svc = PreflightService()
    svc._checks = [PreflightCheck(id="db", status="pass")]
    with patch.object(svc, "run", return_value=PreflightResult(checks=svc._checks)):
        result = svc.run_or_raise()
    assert result.passed is True


def test_run_or_raise_raises_in_fail_fast_mode() -> None:
    with patch.dict(os.environ, {"PREFLIGHT_FAIL_FAST": "true"}):
        with patch("app.services.preflight.settings") as mock_settings:
            mock_settings.app_env = "local"
            svc = PreflightService()
            with patch.object(svc, "run", return_value=_result_with([("db", "fail")])):
                with pytest.raises(RuntimeError, match="Preflight failed"):
                    svc.run_or_raise()


def test_run_or_raise_does_not_raise_in_warn_only_mode() -> None:
    with patch.dict(os.environ, {"PREFLIGHT_FAIL_FAST": "false"}):
        with patch("app.services.preflight.settings") as mock_settings:
            mock_settings.app_env = "local"
            svc = PreflightService()
            with patch.object(svc, "run", return_value=_result_with([("db", "fail")])):
                result = svc.run_or_raise()  # darf nicht werfen
    assert result.passed is False


def test_production_always_fail_fast() -> None:
    with patch("app.services.preflight.settings") as mock_settings:
        mock_settings.app_env = "production"
        svc = PreflightService()
        with patch.object(svc, "run", return_value=_result_with([("db", "fail")])):
            with pytest.raises(RuntimeError):
                svc.run_or_raise()


# ── /health/preflight Endpunkt ────────────────────────────────────────────────


def test_health_preflight_endpoint_pass(client) -> None:
    with patch("app.services.preflight.PreflightService.run") as mock_run:
        mock_run.return_value = _result_with([("db", "pass"), ("alembic", "pass")])
        response = client.get("/health/preflight")
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True


def test_health_preflight_endpoint_fail(client) -> None:
    with patch("app.services.preflight.PreflightService.run") as mock_run:
        mock_run.return_value = _result_with([("db", "fail")])
        response = client.get("/health/preflight")
    assert response.status_code == 503
