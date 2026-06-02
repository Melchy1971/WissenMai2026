"""Tests for M5a quality score calculation."""
from __future__ import annotations

import pytest

from app.services.quality_score import (
    calculate_quality_score,
    calculate_quality_score_from_counts,
    calculate_quality_score_from_findings,
    quality_score_category,
)


pytestmark = pytest.mark.m3a_truth


def _finding(finding_type: str) -> dict:
    return {"finding_type": finding_type, "severity": "error"}


def test_empty_findings_score_100_with_explanation():
    result = calculate_quality_score_from_findings([])

    assert result.score == 100.0
    assert result.score_explanation["total_penalty_points"] == 0.0
    assert result.score_explanation["category_weights_percent"] == {
        "duplicate": 25,
        "metadata": 15,
        "lifecycle": 25,
        "source_status": 20,
        "orphan": 15,
    }


def test_score_uses_required_category_weights():
    findings = [
        _finding("DUPLICATE_DOCUMENT"),
        _finding("MISSING_METADATA"),
        _finding("INVALID_LIFECYCLE"),
        _finding("INVALID_SOURCE_STATUS"),
        _finding("ORPHAN_CITATION"),
    ]

    result = calculate_quality_score_from_findings(findings)

    assert result.score == 90.0
    assert result.score_explanation["categories"]["duplicate"]["penalty_points"] == 2.5
    assert result.score_explanation["categories"]["metadata"]["penalty_points"] == 1.5
    assert result.score_explanation["categories"]["lifecycle"]["penalty_points"] == 2.5
    assert result.score_explanation["categories"]["source_status"]["penalty_points"] == 2.0
    assert result.score_explanation["categories"]["orphan"]["penalty_points"] == 1.5


def test_category_penalty_is_capped_after_ten_findings():
    findings = [_finding("INVALID_LIFECYCLE")] * 20

    result = calculate_quality_score_from_findings(findings)

    assert result.score == 75.0
    lifecycle = result.score_explanation["categories"]["lifecycle"]
    assert lifecycle["finding_count"] == 20
    assert lifecycle["capped_finding_count"] == 10
    assert lifecycle["penalty_points"] == 25.0


def test_legacy_type_key_is_supported():
    result = calculate_quality_score_from_findings([{"type": "DUPLICATE_CONTENT"}])

    assert result.score == 97.5


def test_unknown_finding_types_do_not_penalize_but_are_explained():
    result = calculate_quality_score_from_findings([_finding("UNKNOWN_TYPE")])

    assert result.score == 100.0
    assert result.score_explanation["unknown_finding_types"] == {"UNKNOWN_TYPE": 1}


def test_count_based_helper_remains_compatible():
    score = calculate_quality_score(
        duplicates=10,
        metadata_issues=10,
        lifecycle_issues=10,
        source_status_issues=10,
        orphan_objects=10,
    )

    assert score == 0.0


def test_count_result_includes_score_explanation():
    result = calculate_quality_score_from_counts({"duplicate": 2, "orphan": 1})

    assert result.score == 93.5
    assert result.score_explanation["categories"]["duplicate"]["finding_count"] == 2
    assert result.score_explanation["categories"]["orphan"]["finding_count"] == 1


def test_quality_score_category_boundaries():
    assert quality_score_category(20) == "Critical"
    assert quality_score_category(21) == "Poor"
    assert quality_score_category(40) == "Poor"
    assert quality_score_category(41) == "Fair"
    assert quality_score_category(60) == "Fair"
    assert quality_score_category(61) == "Good"
    assert quality_score_category(80) == "Good"
    assert quality_score_category(81) == "Excellent"
