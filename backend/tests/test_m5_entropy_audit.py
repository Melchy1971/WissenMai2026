from app.services import m5_entropy_audit as entropy


def _longrun_report() -> dict:
    return {
        "generated_at": "2026-05-12T09:36:21Z",
        "cycles": 3,
        "restore_every": 3,
        "thresholds": {"queue_backlog": 25},
        "cycles_detail": [
            {
                "cycle": 1,
                "metrics": {"queue_backlog": 0, "orphan_growth": 0, "stale_index_growth": 0},
                "cleanup_dry_run": {"candidate_count": 0, "blocked_count": 0},
            },
            {
                "cycle": 2,
                "metrics": {"queue_backlog": 2, "orphan_growth": 0, "stale_index_growth": 0},
                "cleanup_dry_run": {"candidate_count": 1, "blocked_count": 0},
            },
            {
                "cycle": 3,
                "metrics": {"queue_backlog": 3, "orphan_growth": 0, "stale_index_growth": 0},
                "backup_restore": {"status": "pass"},
                "cleanup_dry_run": {"candidate_count": 0, "blocked_count": 0},
            },
        ],
    }


def _retrieval_report() -> dict:
    return {
        "generated_at": "2026-05-12T09:36:21Z",
        "summary": {
            "citation_completeness": 1.0,
            "lifecycle_exclusion_violations": 0,
        },
        "queries": [{"query_id": "GQ-002", "recall_at_5": 1.0}],
    }


def test_entropy_audit_builds_all_required_categories() -> None:
    report = entropy.run_audit(longrun_report=_longrun_report(), retrieval_report=_retrieval_report())

    assert report["audit_version"] == "m5-data-aging-entropy-v1"
    assert len(report["entropy_matrix"]) == 7
    assert {item["category"] for item in report["entropy_matrix"]} == {
        "stale Queue Jobs",
        "veraltete Backups",
        "orphan growth",
        "stale Indexeintraege",
        "historische Citation Drift",
        "duplicate growth",
        "Cleanup-Rueckstaende",
    }


def test_entropy_audit_flags_duplicate_cardinality_as_residual_risk() -> None:
    report = entropy.run_audit(longrun_report=_longrun_report(), retrieval_report=_retrieval_report())
    duplicate = next(item for item in report["entropy_matrix"] if item["category"] == "duplicate growth")

    assert duplicate["risk"] == "medium"
    assert duplicate["growth_over_time"]["production_duplicate_cardinality"] == "not_measured"
    assert any("duplicate cardinality" in measure for measure in report["prevention_measures"])


def test_entropy_audit_writes_versioned_reports(tmp_path) -> None:
    result = entropy.write_reports(output_dir=tmp_path)

    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "summary.md").exists()
    assert result["report"]["audit_version"] == "m5-data-aging-entropy-v1"
