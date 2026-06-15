from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_governance_ui_shows_risk_and_consequence():
    text = Path("frontend/src/pages/GovernancePage.jsx").read_text(encoding="utf-8")
    assert "RiskBadge" in text
    assert "Folge:" in text
    assert "/api/v1/governance/privacy-mode" in text

