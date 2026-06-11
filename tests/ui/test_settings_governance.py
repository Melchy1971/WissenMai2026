"""Settings: Governance-Sektion."""

def test_approval_expiry_range(page):
    page.goto('/settings')
    # 1–1440 Minuten
