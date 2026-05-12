from app.services import m5_longrun_simulation as longrun


def test_longrun_simulation_passes_default_weekly_model() -> None:
    report = longrun.run_simulation(cycles=7, restore_every=7)

    assert report["status"] == "pass"
    assert report["stop_events"] == []
    assert report["final_metrics"]["stale_index_growth"] == 0
    assert report["final_metrics"]["orphan_growth"] == 0
    assert report["final_metrics"]["retrieval_precision_at_5"] >= 0.80


def test_longrun_stop_criteria_detect_backlog_regression() -> None:
    events = longrun._evaluate_stop_criteria(
        {
            "stale_index_growth": 0,
            "queue_backlog": 26,
            "orphan_growth": 0,
            "retrieval_precision_at_5": 0.84,
            "retrieval_recall_at_5": 0.88,
            "error_rate": 0.01,
        }
    )

    assert "queue_backlog=26" in events


def test_longrun_writes_versioned_reports(tmp_path) -> None:
    result = longrun.write_reports(cycles=3, restore_every=3, output_dir=tmp_path)

    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "summary.md").exists()
    assert result["report"]["simulation_version"] == "m5-longrun-v1"
    assert result["timestamped"].endswith(".json")
    assert result["summary"].endswith("summary.md")
