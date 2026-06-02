"""M5a Data Quality score calculation.

The score is category based. Each category can consume its configured
percentage of the total score, capped after ten findings in that category.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


CATEGORY_WEIGHTS: dict[str, float] = {
    "duplicate": 0.25,
    "metadata": 0.15,
    "lifecycle": 0.25,
    "source_status": 0.20,
    "orphan": 0.15,
}

CATEGORY_LABELS: dict[str, str] = {
    "duplicate": "Duplicate",
    "metadata": "Metadata",
    "lifecycle": "Lifecycle",
    "source_status": "Source Status",
    "orphan": "Orphan Objects",
}

FINDING_TYPE_CATEGORIES: dict[str, str] = {
    "DUPLICATE_DOCUMENT": "duplicate",
    "DUPLICATE_CONTENT": "duplicate",
    "MISSING_METADATA": "metadata",
    "EMPTY_DOCUMENT": "metadata",
    "EMPTY_CHUNK": "metadata",
    "INVALID_LIFECYCLE": "lifecycle",
    "RETRIEVAL_RISK": "lifecycle",
    "INVALID_SOURCE_STATUS": "source_status",
    "ORPHAN_CHUNK": "orphan",
    "ORPHAN_VERSION": "orphan",
    "ORPHAN_CITATION": "orphan",
    "ORPHAN_FINDING": "orphan",
}

MAX_FINDINGS_PER_CATEGORY = 10


@dataclass(frozen=True)
class QualityScoreResult:
    score: float
    score_explanation: dict[str, Any]


def calculate_quality_score(
    duplicates: int = 0,
    metadata_issues: int = 0,
    lifecycle_issues: int = 0,
    source_status_issues: int = 0,
    orphan_objects: int = 0,
) -> float:
    """Backward-compatible count-based score helper."""
    result = calculate_quality_score_from_counts(
        {
            "duplicate": duplicates,
            "metadata": metadata_issues,
            "lifecycle": lifecycle_issues,
            "source_status": source_status_issues,
            "orphan": orphan_objects,
        }
    )
    return result.score


def calculate_quality_score_from_findings(findings: Sequence[Mapping[str, Any]]) -> QualityScoreResult:
    counts = {category: 0 for category in CATEGORY_WEIGHTS}
    unknown_finding_types: dict[str, int] = {}

    for finding in findings:
        finding_type = _finding_type(finding)
        category = FINDING_TYPE_CATEGORIES.get(finding_type)
        if category is None:
            unknown_finding_types[finding_type] = unknown_finding_types.get(finding_type, 0) + 1
            continue
        counts[category] += 1

    return calculate_quality_score_from_counts(counts, unknown_finding_types=unknown_finding_types)


def calculate_quality_score_from_counts(
    counts: Mapping[str, int],
    *,
    unknown_finding_types: Mapping[str, int] | None = None,
) -> QualityScoreResult:
    normalized_counts = {category: max(0, int(counts.get(category, 0))) for category in CATEGORY_WEIGHTS}
    category_explanations: dict[str, dict[str, float | int | str]] = {}
    total_penalty_points = 0.0

    for category, weight in CATEGORY_WEIGHTS.items():
        count = normalized_counts[category]
        capped_count = min(count, MAX_FINDINGS_PER_CATEGORY)
        category_penalty = round(weight * (capped_count / MAX_FINDINGS_PER_CATEGORY) * 100.0, 2)
        total_penalty_points += category_penalty
        category_explanations[category] = {
            "label": CATEGORY_LABELS[category],
            "weight_percent": int(weight * 100),
            "finding_count": count,
            "capped_finding_count": capped_count,
            "max_findings_for_full_penalty": MAX_FINDINGS_PER_CATEGORY,
            "penalty_points": category_penalty,
        }

    score = round(max(0.0, 100.0 - total_penalty_points), 2)
    return QualityScoreResult(
        score=score,
        score_explanation={
            "score": score,
            "formula": "100 - sum(category_weight_percent * min(category_findings, 10) / 10)",
            "category_weights_percent": {
                category: int(weight * 100) for category, weight in CATEGORY_WEIGHTS.items()
            },
            "categories": category_explanations,
            "total_penalty_points": round(total_penalty_points, 2),
            "unknown_finding_types": dict(unknown_finding_types or {}),
        },
    )


def quality_score_category(score: int | float) -> str:
    if score <= 20:
        return "Critical"
    if score <= 40:
        return "Poor"
    if score <= 60:
        return "Fair"
    if score <= 80:
        return "Good"
    return "Excellent"


def _finding_type(finding: Mapping[str, Any]) -> str:
    value = finding.get("finding_type", finding.get("type", ""))
    return str(value)
