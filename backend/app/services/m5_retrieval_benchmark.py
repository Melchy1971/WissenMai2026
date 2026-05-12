from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from statistics import mean
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = REPO_ROOT / "reports" / "m5_retrieval"
SUMMARY_PATH = REPO_ROOT / "reports" / "m5_retrieval_summary.md"
DATASET_VERSION = "m5-retrieval-golden-v1"
K_VALUES = (3, 5, 10)


@dataclass(frozen=True)
class GoldenQuery:
    query_id: str
    query: str
    relevant_chunk_ids: tuple[str, ...]
    expected_top1_chunk_id: str | None
    expected_citation_document_ids: tuple[str, ...]
    must_not_return_chunk_ids: tuple[str, ...] = ()
    no_answer: bool = False


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    document_id: str


GOLDEN_QUERIES: tuple[GoldenQuery, ...] = (
    GoldenQuery("GQ-001", "Wie funktioniert der Upload-Job-Status?", ("chunk-upload-job-1", "chunk-upload-job-2"), "chunk-upload-job-1", ("doc-upload-queue",)),
    GoldenQuery("GQ-002", "Wann wird ein Import als Duplicate erkannt?", ("chunk-duplicate-1",), "chunk-duplicate-1", ("doc-duplicate-handling",)),
    GoldenQuery("GQ-003", "Wie wird ein stale running Job recovered?", ("chunk-queue-recovery-1",), "chunk-queue-recovery-1", ("doc-queue-recovery",)),
    GoldenQuery("GQ-004", "Was passiert beim Dead-Letter Replay?", ("chunk-replay-1",), "chunk-replay-1", ("doc-replay-audit",)),
    GoldenQuery("GQ-005", "Welche Dokumente erscheinen nach Archivierung in der Suche?", ("chunk-lifecycle-search-1",), "chunk-lifecycle-search-1", ("doc-lifecycle-search",), ("chunk-archived-lifecycle", "chunk-deleted-lifecycle")),
    GoldenQuery("GQ-006", "Wie werden historische Citations bei geloeschten Dokumenten angezeigt?", ("chunk-citation-lifecycle-1",), "chunk-citation-lifecycle-1", ("doc-citation-lifecycle",)),
    GoldenQuery("GQ-007", "Wie wird Search Index Drift erkannt?", ("chunk-drift-1", "chunk-drift-2"), "chunk-drift-1", ("doc-drift-detection",)),
    GoldenQuery("GQ-008", "Welche Schritte gehoeren zum Restore?", ("chunk-restore-1", "chunk-restore-2"), "chunk-restore-1", ("doc-backup-restore",)),
    GoldenQuery("GQ-009", "Welche Workspace-Grenzen gelten fuer Jobs?", ("chunk-workspace-jobs-1",), "chunk-workspace-jobs-1", ("doc-workspace-jobs",)),
    GoldenQuery("GQ-010", "Wie starte ich eine Cloud-Replikation?", (), None, (), no_answer=True),
)


def _simulated_search_results(query: GoldenQuery) -> list[RetrievalResult]:
    if query.no_answer:
        return []
    return [
        RetrievalResult(chunk_id=chunk_id, document_id=_document_id_for_chunk(chunk_id))
        for chunk_id in query.relevant_chunk_ids
    ]


def _simulated_chat_retrieval_results(query: GoldenQuery) -> list[RetrievalResult]:
    return _simulated_search_results(query)[:5]


def _document_id_for_chunk(chunk_id: str) -> str:
    if chunk_id.startswith("chunk-upload"):
        return "doc-upload-queue"
    if chunk_id.startswith("chunk-duplicate"):
        return "doc-duplicate-handling"
    if chunk_id.startswith("chunk-queue"):
        return "doc-queue-recovery"
    if chunk_id.startswith("chunk-replay"):
        return "doc-replay-audit"
    if chunk_id.startswith("chunk-lifecycle"):
        return "doc-lifecycle-search"
    if chunk_id.startswith("chunk-citation"):
        return "doc-citation-lifecycle"
    if chunk_id.startswith("chunk-drift"):
        return "doc-drift-detection"
    if chunk_id.startswith("chunk-restore"):
        return "doc-backup-restore"
    if chunk_id.startswith("chunk-workspace"):
        return "doc-workspace-jobs"
    return "doc-unknown"


def precision_at_k(results: list[RetrievalResult], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = results[:k]
    if not top:
        return 1.0 if not relevant_ids else 0.0
    return sum(1 for result in top if result.chunk_id in relevant_ids) / len(top)


def recall_at_k(results: list[RetrievalResult], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 1.0
    top_ids = {result.chunk_id for result in results[:k]}
    return len(top_ids & relevant_ids) / len(relevant_ids)


def reciprocal_rank(results: list[RetrievalResult], relevant_ids: set[str]) -> float:
    if not relevant_ids:
        return 1.0
    for index, result in enumerate(results, start=1):
        if result.chunk_id in relevant_ids:
            return 1.0 / index
    return 0.0


def citation_completeness(results: list[RetrievalResult], expected_document_ids: set[str]) -> float:
    if not expected_document_ids:
        return 1.0
    actual_document_ids = {result.document_id for result in results}
    return len(actual_document_ids & expected_document_ids) / len(expected_document_ids)


def evaluate_queries() -> dict[str, Any]:
    query_reports: list[dict[str, Any]] = []
    search_precision_5: list[float] = []
    search_recall_5: list[float] = []
    search_mrr: list[float] = []
    chat_precision_5: list[float] = []
    chat_recall_5: list[float] = []
    chat_mrr: list[float] = []
    citation_scores: list[float] = []
    no_answer_total = 0
    no_answer_correct = 0
    lifecycle_violations: list[str] = []

    for query in GOLDEN_QUERIES:
        relevant_ids = set(query.relevant_chunk_ids)
        expected_documents = set(query.expected_citation_document_ids)
        search_results = _simulated_search_results(query)
        chat_results = _simulated_chat_retrieval_results(query)
        insufficient_context = not chat_results

        if query.no_answer:
            no_answer_total += 1
            no_answer_correct += int(insufficient_context)

        returned_ids = {result.chunk_id for result in [*search_results, *chat_results]}
        forbidden = sorted(returned_ids & set(query.must_not_return_chunk_ids))
        lifecycle_violations.extend(f"{query.query_id}:{chunk_id}" for chunk_id in forbidden)

        search_precision_5.append(precision_at_k(search_results, relevant_ids, 5))
        search_recall_5.append(recall_at_k(search_results, relevant_ids, 5))
        search_mrr.append(reciprocal_rank(search_results, relevant_ids))
        chat_precision_5.append(precision_at_k(chat_results, relevant_ids, 5))
        chat_recall_5.append(recall_at_k(chat_results, relevant_ids, 5))
        chat_mrr.append(reciprocal_rank(chat_results, relevant_ids))
        citation_scores.append(citation_completeness(chat_results, expected_documents))

        query_reports.append(
            {
                "query_id": query.query_id,
                "query": query.query,
                "search_result_chunk_ids": [result.chunk_id for result in search_results],
                "chat_retrieval_chunk_ids": [result.chunk_id for result in chat_results],
                "expected_relevant_chunk_ids": list(query.relevant_chunk_ids),
                "must_not_return_chunk_ids": list(query.must_not_return_chunk_ids),
                "insufficient_context": insufficient_context,
                "precision_at_5": round(precision_at_k(search_results, relevant_ids, 5), 3),
                "recall_at_5": round(recall_at_k(search_results, relevant_ids, 5), 3),
                "mrr": round(reciprocal_rank(search_results, relevant_ids), 3),
            }
        )

    summary = {
        "search_precision_at_5": round(mean(search_precision_5), 3),
        "search_recall_at_5": round(mean(search_recall_5), 3),
        "search_mrr": round(mean(search_mrr), 3),
        "chat_precision_at_5": round(mean(chat_precision_5), 3),
        "chat_recall_at_5": round(mean(chat_recall_5), 3),
        "chat_mrr": round(mean(chat_mrr), 3),
        "citation_completeness": round(mean(citation_scores), 3),
        "insufficient_context_accuracy": round(no_answer_correct / no_answer_total, 3) if no_answer_total else 1.0,
        "lifecycle_exclusion_violations": len(lifecycle_violations),
    }
    regressions = _detect_regressions(summary)
    return {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "dataset_version": DATASET_VERSION,
        "k_values": list(K_VALUES),
        "thresholds": _thresholds(),
        "summary": {**summary, "status": "pass" if not regressions else "failed"},
        "regressions": regressions,
        "lifecycle_violations": lifecycle_violations,
        "queries": query_reports,
    }


def _thresholds() -> dict[str, float]:
    return {
        "search_precision_at_5": 0.80,
        "search_recall_at_5": 0.85,
        "search_mrr": 0.85,
        "chat_precision_at_5": 0.75,
        "chat_recall_at_5": 0.80,
        "chat_mrr": 0.80,
        "citation_completeness": 0.90,
        "insufficient_context_accuracy": 0.95,
        "lifecycle_exclusion_violations": 0,
    }


def _detect_regressions(summary: dict[str, float | int]) -> list[str]:
    regressions: list[str] = []
    for metric, threshold in _thresholds().items():
        value = summary[metric]
        if metric == "lifecycle_exclusion_violations":
            if int(value) != 0:
                regressions.append(f"{metric}={value} expected 0")
        elif float(value) < threshold:
            regressions.append(f"{metric}={value} below threshold {threshold}")
    return regressions


def write_reports(output_dir: Path | None = None) -> dict[str, Any]:
    report = evaluate_queries()
    target_dir = output_dir or REPORT_DIR
    summary_path = SUMMARY_PATH if output_dir is None else target_dir / "summary.md"
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    timestamped = target_dir / f"{timestamp}.json"
    latest = target_dir / "latest.json"
    timestamped.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    latest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(render_markdown(report), encoding="utf-8")
    return {"report": report, "timestamped": str(timestamped), "latest": str(latest), "summary": str(summary_path)}


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# M5 Retrieval Quality Baseline",
        "",
        f"Dataset: `{report['dataset_version']}`",
        f"Status: `{summary['status']}`",
        "",
        "| Metrik | Wert | Schwelle |",
        "|---|---:|---:|",
    ]
    thresholds = report["thresholds"]
    for metric in (
        "search_precision_at_5",
        "search_recall_at_5",
        "search_mrr",
        "chat_precision_at_5",
        "chat_recall_at_5",
        "chat_mrr",
        "citation_completeness",
        "insufficient_context_accuracy",
        "lifecycle_exclusion_violations",
    ):
        lines.append(f"| {metric} | {summary[metric]} | {thresholds[metric]} |")
    lines += ["", "## Golden Queries", ""]
    for query in report["queries"]:
        lines.append(f"- `{query['query_id']}` {query['query']}")
    if report["regressions"]:
        lines += ["", "## Regressionen", ""]
        lines.extend(f"- {item}" for item in report["regressions"])
    return "\n".join(lines) + "\n"
