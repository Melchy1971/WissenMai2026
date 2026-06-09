from __future__ import annotations

from scripts.generate_m5a_performance_baseline import build_report


def test_m5a_performance_baseline_report_contract() -> None:
    report = build_report((20,))

    assert report["report_name"] == "m5a_performance_baseline"
    assert report["status"] == "PASS"
    assert report["blockers"] == []
    assert report["methodology"]["document_counts"] == [20]

    measurement = report["measurements"][0]
    assert measurement["documents"] == 20
    assert measurement["runtime_ms"] > 0
    assert measurement["memory"]["tracemalloc_peak_mb"] > 0
    assert measurement["findings"]["total"] > 0
    assert measurement["score_calculation"]["time_ms"] >= 0
    assert report["recommendations"]
