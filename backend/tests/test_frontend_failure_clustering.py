from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.m3a_truth


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "cluster_frontend_failures.py"
spec = importlib.util.spec_from_file_location("cluster_frontend_failures", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
cluster_frontend_failures = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cluster_frontend_failures
spec.loader.exec_module(cluster_frontend_failures)


def test_auth_failure_beats_selector_timeout_for_login_redirect() -> None:
    failure = {
        "name": "01 Login flow > redirects unauthenticated request to login page",
        "error": "expect(locator).toBeVisible failed Locator: getByRole('heading', { name: 'Anmeldung' }) Timeout 5000ms",
    }

    primary, scores, signals = cluster_frontend_failures.classify_failure(failure)

    assert primary == "Auth Failure"
    assert scores["Auth Failure"] > 0
    assert any(signal.startswith("Auth Failure") for signal in signals)


def test_api_failure_is_classified_from_network_error() -> None:
    failure = {
        "name": "backend unreachable > shows API_UNREACHABLE error",
        "error": "TypeError: Failed to fetch net::ERR_CONNECTION_REFUSED",
    }

    primary, _scores, _signals = cluster_frontend_failures.classify_failure(failure)

    assert primary == "API Failure"


def test_build_cluster_report_writes_informational_schema(tmp_path: Path) -> None:
    report = {
        "environment": "test",
        "failed_tests": [
            {
                "name": "03 Workspace loading > shows active workspace id",
                "error": "TimeoutError: page.waitForSelector Timeout waiting for locator('.shell')",
            }
        ],
    }
    test_results = tmp_path / "test-results"
    failure_dir = test_results / "workspace-failure"
    failure_dir.mkdir(parents=True)
    (failure_dir / "error-context.md").write_text(
        "Name: 03 Workspace loading > shows active workspace id\nwaiting for locator('.shell')",
        encoding="utf-8",
    )
    output = tmp_path / "frontend_failure_clusters.json"

    payload = cluster_frontend_failures.build_cluster_report(
        report,
        report_path=Path("reports/current/m3a_frontend_truth.json"),
        test_results_dir=test_results,
        output_path=output,
    )

    assert payload["report_schema_version"] == 1
    assert payload["generated_by"] == "gate_validator"
    assert payload["report_type"] == "informational"
    assert payload["status"] == "INFO"
    assert payload["clusters"]["Workspace Failure"]["count"] == 1
    assert payload["top_root_causes"][0]["cluster"] == "Workspace Failure"
