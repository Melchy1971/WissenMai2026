from backend.app.services.quality_score import calculate_quality_score, quality_score_category

def test_quality_score_full():
    score = calculate_quality_score(duplicates=0, metadata_issues=0, lifecycle_issues=0, source_status_issues=0, orphan_objects=0)
    assert score == 100
    assert quality_score_category(score) == "Excellent"

def test_quality_score_critical():
    score = calculate_quality_score(duplicates=10, metadata_issues=10, lifecycle_issues=10, source_status_issues=10, orphan_objects=10)
    assert score == 0
    assert quality_score_category(score) == "Critical"

def test_quality_score_boundaries():
    assert quality_score_category(20) == "Critical"
    assert quality_score_category(21) == "Poor"
    assert quality_score_category(40) == "Poor"
    assert quality_score_category(41) == "Fair"
    assert quality_score_category(60) == "Fair"
    assert quality_score_category(61) == "Good"
    assert quality_score_category(80) == "Good"
    assert quality_score_category(81) == "Excellent"
