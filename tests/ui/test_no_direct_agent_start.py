from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_agent_ui_uses_orchestrator_endpoint():
    text = Path("frontend/src/pages/AgentsPage.jsx").read_text(encoding="utf-8")
    assert "/api/v1/orchestrator/goals" in text
    assert "/api/v1/agents/" not in text.replace("/api/v1/agents/executions", "")

