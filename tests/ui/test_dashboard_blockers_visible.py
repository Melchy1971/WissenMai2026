from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_dashboard_renders_blockers_before_status_grid():
    text = Path("frontend/src/pages/DashboardPage.jsx").read_text(encoding="utf-8")

    blocker_index = text.index("dashboard-critical-blockers")
    privacy_index = text.index("dashboard-privacy-mode")
    status_index = text.index("dashboard-status-grid")

    assert blocker_index < privacy_index < status_index
    assert "open_blockers" in text
    assert "Blocker-Status UNKNOWN" in text


def test_dashboard_privacy_mode_is_prominent():
    text = Path("frontend/src/pages/DashboardPage.jsx").read_text(encoding="utf-8")

    assert "dashboard-privacy-mode" in text
    assert "dashboard-status-privacy_mode" in text
    assert "Privacy Mode" in text
