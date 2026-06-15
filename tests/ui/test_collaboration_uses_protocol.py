from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_collaboration_ui_sends_protocol():
    text = Path("frontend/src/pages/CollaborationPage.jsx").read_text(encoding="utf-8")
    assert "/api/v1/collaboration/runs" in text
    assert "protocol" in text
