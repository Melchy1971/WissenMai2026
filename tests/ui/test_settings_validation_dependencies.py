from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_settings_validation_dependency_rules_exist():
    text = Path("frontend/src/lib/settingsValidation.ts").read_text(encoding="utf-8")
    for token in (
        "chunk_overlap",
        "source_required",
        "review_queue_required",
        "validation_pipeline_enabled",
        "arbitration_enabled",
        "rollback_enabled",
        "plugin_sandbox_enabled",
    ):
        assert token in text

