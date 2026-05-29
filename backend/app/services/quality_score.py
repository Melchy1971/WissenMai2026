def calculate_quality_score(duplicates, metadata_issues, lifecycle_issues, source_status_issues, orphan_objects):
    weights = {
        "duplicates": 0.25,
        "metadata": 0.15,
        "lifecycle": 0.25,
        "source": 0.20,
        "orphan": 0.15
    }
    penalty = (
        weights["duplicates"] * min(duplicates, 10) / 10 +
        weights["metadata"] * min(metadata_issues, 10) / 10 +
        weights["lifecycle"] * min(lifecycle_issues, 10) / 10 +
        weights["source"] * min(source_status_issues, 10) / 10 +
        weights["orphan"] * min(orphan_objects, 10) / 10
    )
    score = max(0, 100 - int(penalty * 100))
    return score

def quality_score_category(score: int) -> str:
    if score <= 20:
        return "Critical"
    elif score <= 40:
        return "Poor"
    elif score <= 60:
        return "Fair"
    elif score <= 80:
        return "Good"
    else:
        return "Excellent"
