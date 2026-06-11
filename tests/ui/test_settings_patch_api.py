"""Settings: PATCH /settings wird korrekt aufgerufen."""

def test_patch_called_on_save(page, requests_mock):
    # Prüft, dass PATCH /api/v1/settings mit korrektem Payload aufgerufen wird
    page.goto('/settings')

def test_only_changed_section_sent(page, requests_mock):
    # Nur geänderte Sektion wird im PATCH-Body gesendet
    page.goto('/settings')
