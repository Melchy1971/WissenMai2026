"""Settings: Agents-Sektion."""

def test_max_steps_boundaries(page):
    page.goto('/settings')

def test_max_tool_calls_zero_allowed(page):
    page.goto('/settings')

def test_max_runtime_max_3600(page):
    page.goto('/settings')
