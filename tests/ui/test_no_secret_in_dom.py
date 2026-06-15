from pathlib import Path

import pytest

pytestmark = pytest.mark.unit_fast


def test_secret_label_does_not_expose_api_key_name():
    text = Path("frontend/src/pages/SettingsPage.jsx").read_text(encoding="utf-8")
    assert ">api_key<" not in text
    assert "console.log" not in text

