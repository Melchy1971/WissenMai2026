from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_rag_ui_blocks_answers_without_sources():
    text = Path("frontend/src/pages/RAGCenterPage.jsx").read_text(encoding="utf-8")
    assert "rag-answer-blocked" in text
    assert "source-list" in text

