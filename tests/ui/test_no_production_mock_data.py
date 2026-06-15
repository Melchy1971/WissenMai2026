from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_no_removed_rag_or_agent_examples_in_production():
    root = Path("backend/app/api/v1")
    text = "\n".join((root / name).read_text(encoding="utf-8") for name in ("rag_gui.py", "agents_gui.py"))
    forbidden = ("Onboarding Guide", "Classified Report", "ag-planner", "ag-researcher")
    for value in forbidden:
        assert value not in text

