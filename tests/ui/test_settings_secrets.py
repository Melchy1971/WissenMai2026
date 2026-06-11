"""Settings: Secret-Felder."""

def test_secret_field_shows_masked(page):
    page.goto('/settings')
    inputs = page.get_by_test_id('secret-input').all()
    for inp in inputs:
        text = inp.text_content()
        assert text in ('●●●●●●●●', '[nicht gesetzt]')

def test_secret_field_clears_after_update(page):
    # Nach Update-Aktion wird Eingabe geleert
    page.goto('/settings')
