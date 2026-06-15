from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_center_pages_render_empty_state():
    for path in ("frontend/src/pages/SimpleListPage.jsx", "frontend/src/pages/AgentsPage.jsx", "frontend/src/pages/CollaborationPage.jsx"):
        text = Path(path).read_text(encoding="utf-8")
        assert "EmptyState" in text

