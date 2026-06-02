from backend.app.services.quality_score import (
    calculate_quality_score,
    calculate_quality_score_from_findings,
    quality_score_category,
)
import pytest


pytestmark = pytest.mark.m3a_truth


def test_quality_score_full():
    score = calculate_quality_score(
        duplicates=0,
        metadata_issues=0,
        lifecycle_issues=0,
        source_status_issues=0,
        orphan_objects=0,
    )
    assert score == 100.0
    assert quality_score_category(score) == "Excellent"


def test_quality_score_critical():
    score = calculate_quality_score(
        duplicates=10,
        metadata_issues=10,
        lifecycle_issues=10,
        source_status_issues=10,
        orphan_objects=10,
    )
    assert score == 0.0
    assert quality_score_category(score) == "Critical"


def test_quality_score_explanation():
    result = calculate_quality_score_from_findings(
        [
            {"finding_type": "DUPLICATE_DOCUMENT"},
            {"finding_type": "INVALID_SOURCE_STATUS"},
        ]
    )
    assert result.score == 95.5
    assert result.score_explanation["categories"]["duplicate"]["finding_count"] == 1
    assert result.score_explanation["categories"]["source_status"]["finding_count"] == 1


def test_quality_score_boundaries():
    assert quality_score_category(20) == "Critical"
    assert quality_score_category(21) == "Poor"
    assert quality_score_category(40) == "Poor"
    assert quality_score_category(41) == "Fair"
    assert quality_score_category(60) == "Fair"
    assert quality_score_category(61) == "Good"
    assert quality_score_category(80) == "Good"
    assert quality_score_category(81) == "Excellent"
