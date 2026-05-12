from app.services import m5_retrieval_benchmark as benchmark


def test_retrieval_benchmark_meets_baseline_thresholds() -> None:
    report = benchmark.evaluate_queries()

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["search_precision_at_5"] >= 0.80
    assert report["summary"]["search_recall_at_5"] >= 0.85
    assert report["summary"]["chat_precision_at_5"] >= 0.75
    assert report["summary"]["citation_completeness"] >= 0.90
    assert report["summary"]["insufficient_context_accuracy"] >= 0.95
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
    result = benchmark.write_reports(output_dir=tmp_path)

    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "summary.md").exists()
    assert result["report"]["dataset_version"] == benchmark.DATASET_VERSION
    assert result["timestamped"].endswith(".json")
    assert result["summary"].endswith("summary.md")
