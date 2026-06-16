from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_dashboard_uses_unknown_not_fake_pass_fallbacks():
    text = Path("frontend/src/pages/DashboardPage.jsx").read_text(encoding="utf-8")

    assert "UNKNOWN" in text
    assert "?? 'PASS'" not in text
    assert '?? "PASS"' not in text
    assert "`dashboard-status-${field}`" in text
    assert "gui_gate" in text
    assert "security_gate" in text
    assert "governance_gate" in text


def test_dashboard_loads_primary_status_endpoint():
    text = Path("frontend/src/pages/DashboardPage.jsx").read_text(encoding="utf-8")
    status_client = Path("frontend/src/api/status.js").read_text(encoding="utf-8")

    assert "getSystemStatus" in text
    assert "requestJson('/api/v1/status'" in status_client
    assert "callApi('/api/v1/status'" not in status_client
