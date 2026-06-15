from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_secret_sources_are_counted_not_rendered():
    text = Path("frontend/src/pages/RAGCenterPage.jsx").read_text(encoding="utf-8")
    assert "blocked_source_count" in text
    assert "Gesperrte Quellen" in text

