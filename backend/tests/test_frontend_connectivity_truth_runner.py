from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.frontend_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_frontend_connectivity_truth.js"


def test_connectivity_truth_runner_contains_required_checks_and_no_mocking() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    for check_id in [
        "frontend_reaches_backend",
        "health_reachable",
        "auth_me_reachable",
        "login_possible",
        "workspace_bootstrap_successful",
        "document_list_loads",
        "no_api_unreachable_normalflow",
        "authorization_header_correct",
        "x_workspace_id_correct",
        "no_cors_error",
        "no_mixed_content_error",
        "no_dns_error",
        "no_timeout",
    ]:
        assert check_id in source

    assert "mock_responses: false" in source
    assert "page.route(" not in source
    assert "requestfailed" in source


def test_connectivity_truth_runner_is_valid_javascript() -> None:
    result = subprocess.run(
        ["node", "--check", str(SCRIPT_PATH)],
        cwd=SCRIPT_PATH.parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
