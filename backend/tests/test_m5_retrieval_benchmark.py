from app.services import m5_retrieval_benchmark as benchmark


def test_retrieval_benchmark_meets_baseline_thresholds() -> None:
    report = benchmark.evaluate_queries()

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["search_precision_at_5"] >= 0.80
    assert report["summary"]["search_recall_at_5"] >= 0.85
    assert report["summary"]["chat_precision_at_5"] >= 0.75
    assert report["summary"]["citation_completeness"] >= 0.90
    assert report["summary"]["insufficient_context_accuracy"] >= 0.95
    assert report["summary"]["missing_context_rate"] <= 0.15
    assert report["summary"]["lifecycle_exclusion_violations"] == 0
    assert report["regressions"] == []


def test_retrieval_metric_helpers_handle_missing_relevant_chunks() -> None:
    results = [
        benchmark.RetrievalResult(chunk_id="chunk-a", document_id="doc-a"),
        benchmark.RetrievalResult(chunk_id="chunk-b", document_id="doc-b"),
    ]

    assert benchmark.precision_at_k(results, {"chunk-b"}, 1) == 0.0
    assert benchmark.recall_at_k(results, {"chunk-b"}, 1) == 0.0
    assert benchmark.reciprocal_rank(results, {"chunk-b"}) == 0.5


def test_retrieval_benchmark_writes_versioned_reports(tmp_path) -> None:
    result = benchmark.write_reports(output_dir=tmp_path, trigger="reindex")

    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "regression" / "latest.json").exists()
    assert (tmp_path / "regression" / "summary.md").exists()
    assert (tmp_path / "regression" / "baseline.json").exists()
    assert result["report"]["dataset_version"] == benchmark.DATASET_VERSION
    assert result["regression_report"]["trigger"] == "reindex"
    assert result["regression_report"]["status"] == "pass"
    assert result["timestamped"].endswith(".json")
    assert result["summary"].endswith("summary.md")


def test_retrieval_regression_detection_flags_baseline_drop() -> None:
    current = benchmark.evaluate_queries()
    baseline = {
        "summary": {
            **current["summary"],
            "search_precision_at_5": current["summary"]["search_precision_at_5"] + 0.10,
            "missing_context_rate": 0.0,
        }
    }

    report = benchmark.build_regression_report(trigger="cleanup", baseline=baseline)

    assert report["status"] == "failed"
    assert report["trigger"] == "cleanup"
    assert any("search_precision_at_5" in issue for issue in report["baseline_regressions"])
