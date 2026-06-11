"""Settings: Provider-Sektion."""
import pytest

def test_provider_section_renders(page):
    page.goto('/settings')
    assert page.get_by_text('Provider').is_visible()

def test_provider_timeout_valid_range(page):
    page.goto('/settings')
    # Annahme: erstes number-Input ist timeout_seconds
    inp = page.locator('input[type="number"]').first
    inp.fill('60')
    page.get_by_role('button', name='Speichern').first.click()
    assert not page.get_by_text('1–300 s').is_visible()

def test_provider_timeout_invalid(page):
    page.goto('/settings')
    inp = page.locator('input[type="number"]').first
    inp.fill('9999')
    page.get_by_role('button', name='Speichern').first.click()
    assert page.get_by_text('1–300 s').is_visible()
