"""Settings: Dirty-State-Indikator."""

def test_dirty_indicator_appears_on_change(page):
    page.goto('/settings')
    # Wert ändern → Dirty-Indikator sichtbar

def test_dirty_indicator_disappears_after_save(page):
    page.goto('/settings')
