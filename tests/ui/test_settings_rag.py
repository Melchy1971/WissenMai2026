"""Settings: RAG-Sektion."""

def test_chunk_size_boundaries(page):
    page.goto('/settings')
    # Validierung: chunk_size < 100 soll Fehler zeigen

def test_chunk_overlap_less_than_chunk_size(page):
    page.goto('/settings')
    # overlap >= chunk_size → Fehler 'Overlap < chunk_size'

def test_min_score_range(page):
    page.goto('/settings')
    # min_score 0.0–1.0
