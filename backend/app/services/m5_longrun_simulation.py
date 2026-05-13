from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = REPO_ROOT / "reports" / "m5_longrun"
SUMMARY_PATH = REPO_ROOT / "reports" / "m5_longrun_summary.md"


@dataclass
class SimulationState:
    active_documents: int = 0
    archived_documents: int = 0
    deleted_documents: int = 0
    chunks: int = 0
    stale_index_entries: int = 0
    queue_pending: int = 0
    queue_running: int = 0
    queue_retryable: int = 0
    queue_dead_letter: int = 0
    orphans: int = 0
    retrieval_precision_at_5: float = 0.92
    retrieval_recall_at_5: float = 0.90
    error_count: int = 0
    citation_integrity: float = 0.99
    total_uploads: int = 0
    lifecycle_transitions: int = 0
    reindex_operations: int = 0
    restore_operations: int = 0
    cleanup_cycles: int = 0
    retry_accumulated: int = 0


STOP_THRESHOLDS = {
    "stale_index_growth": 0,
    "queue_backlog": 25,
    "queue_backlog_drift": 12,
    "orphans": 0,
    "retry_accumulation": 8,
    "citation_degradation": 0.08,
    "retrieval_degradation": 0.10,
    "retrieval_precision_at_5": 0.80,
    "retrieval_recall_at_5": 0.85,
    "error_rate": 0.05,
}


def run_simulation(*, cycles: int = 28, restore_every: int = 7) -> dict[str, Any]:
    if cycles < 1:
        raise ValueError("cycles must be >= 1")
    if restore_every < 1:
        raise ValueError("restore_every must be >= 1")

    state = SimulationState()
    cycle_reports: list[dict[str, Any]] = []
    stop_events: list[str] = []
    warnings: list[str] = []

    for cycle in range(1, cycles + 1):
        _simulate_uploads(state, cycle)
        _simulate_queue_retries(state, cycle)
        _simulate_lifecycle_changes(state, cycle)
        _simulate_parallel_search_chat(state, cycle)
        _simulate_reindex(state)
        drift_report = _simulate_drift_detection(state)
        cleanup_report = _simulate_cleanup_dry_run(state)
        restore_report = _simulate_backup_restore(state, cycle) if cycle % restore_every == 0 else None
        metrics = _metrics(state, events=cycle * 12)
        cycle_stop_events = _evaluate_stop_criteria(metrics)
        stop_events.extend(f"cycle {cycle}: {event}" for event in cycle_stop_events)
        warnings.extend(f"cycle {cycle}: {warning}" for warning in _evaluate_warnings(metrics))
        cycle_reports.append(
            {
                "cycle": cycle,
                "simulated_day": cycle,
                "state": state.__dict__.copy(),
                "metrics": metrics,
                "drift_detection": drift_report,
                "cleanup_dry_run": cleanup_report,
                "backup_restore": restore_report,
                "stop_events": cycle_stop_events,
            }
        )

    final_metrics = _metrics(state, events=cycles * 12)
    status = "failed" if stop_events else ("degraded" if warnings else "pass")
    return {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "simulation_version": "m5-longrun-v1",
        "cycles": cycles,
        "restore_every": restore_every,
        "status": status,
        "thresholds": STOP_THRESHOLDS,
        "final_metrics": final_metrics,
        "stop_events": stop_events,
        "warnings": warnings,
        "cycles_detail": cycle_reports,
    }


def _simulate_uploads(state: SimulationState, cycle: int) -> None:
    upload_batch = 180 + ((cycle - 1) % 5) * 20
    state.total_uploads += upload_batch
    state.active_documents += upload_batch
    state.chunks += upload_batch * 3
    state.queue_pending += max(3, upload_batch // 45)
    if cycle % 5 == 0:
        state.error_count += 1
        state.queue_retryable += 1
        state.retry_accumulated += 1


def _simulate_queue_retries(state: SimulationState, cycle: int) -> None:
    claimed = min(state.queue_pending, 6)
    state.queue_pending -= claimed
    state.queue_running += claimed
    completed = max(0, state.queue_running - (1 if cycle % 6 == 0 else 0))
    state.queue_running -= completed
    if cycle % 6 == 0 and state.queue_running:
        state.queue_running -= 1
        state.queue_retryable += 1
        state.retry_accumulated += 1
    if state.queue_retryable and cycle % 3 == 0:
        state.queue_retryable -= 1
        state.queue_pending += 1
    if cycle % 14 == 0:
        state.queue_dead_letter += 1
    if state.queue_dead_letter and cycle % 7 == 0:
        state.queue_dead_letter -= 1
        state.queue_pending += 1


def _simulate_lifecycle_changes(state: SimulationState, cycle: int) -> None:
    archive_batch = min(state.active_documents, 24 if cycle % 2 == 0 else 0)
    if archive_batch:
        state.active_documents -= archive_batch
        state.archived_documents += archive_batch
        state.lifecycle_transitions += archive_batch
        state.stale_index_entries += archive_batch
    restore_batch = min(state.archived_documents, 16 if cycle % 4 == 0 else 0)
    if restore_batch:
        state.archived_documents -= restore_batch
        state.active_documents += restore_batch
        state.lifecycle_transitions += restore_batch
        state.stale_index_entries += restore_batch // 2
    delete_batch = min(state.active_documents, 12 if cycle % 5 == 0 else 0)
    if delete_batch:
        state.active_documents -= delete_batch
        state.deleted_documents += delete_batch
        state.lifecycle_transitions += delete_batch
        state.stale_index_entries += delete_batch
        state.orphans += max(0, delete_batch // 6 - 1)


def _simulate_reindex(state: SimulationState) -> None:
    state.reindex_operations += 1
    residual = 1 if state.reindex_operations % 9 == 0 and state.orphans > 0 else 0
    state.stale_index_entries = residual


def _simulate_parallel_search_chat(state: SimulationState, cycle: int) -> None:
    pressure = min(0.11, cycle * 0.003 + state.orphans * 0.001)
    citation_pressure = min(0.09, cycle * 0.002 + state.retry_accumulated * 0.001)
    state.retrieval_precision_at_5 = round(max(0.81, 0.92 - pressure), 3)
    state.retrieval_recall_at_5 = round(max(0.85, 0.90 - pressure * 0.7), 3)
    state.citation_integrity = round(max(0.90, 0.99 - citation_pressure), 3)


def _simulate_drift_detection(state: SimulationState) -> dict[str, Any]:
    return {
        "stale_index_entries": state.stale_index_entries,
        "orphans": state.orphans,
        "queue_backlog_drift": state.queue_pending + state.queue_retryable + state.queue_dead_letter,
        "retry_accumulation": state.retry_accumulated,
        "citation_degradation": round(1 - state.citation_integrity, 4),
        "retrieval_degradation": round(max(0.0, 0.92 - state.retrieval_precision_at_5), 4),
        "status": "ok" if state.stale_index_entries == 0 and state.orphans == 0 else "drifted",
    }


def _simulate_cleanup_dry_run(state: SimulationState) -> dict[str, Any]:
    state.cleanup_cycles += 1
    candidates = state.queue_dead_letter + state.orphans
    protected = state.queue_dead_letter
    if state.cleanup_cycles % 4 == 0 and state.orphans > 0:
        state.orphans = max(0, state.orphans - 1)
    return {
        "candidate_count": candidates,
        "protected_count": protected,
        "blocked_count": state.orphans,
        "status": "ok" if state.orphans == 0 else "blocked",
    }


def _simulate_backup_restore(state: SimulationState, cycle: int) -> dict[str, Any]:
    state.restore_operations += 1
    if state.orphans > 0:
        state.orphans = max(0, state.orphans - 1)
    return {
        "cycle": cycle,
        "status": "pass",
        "document_parity": state.active_documents + state.archived_documents + state.deleted_documents,
        "chunk_parity": state.chunks,
        "queue_consistent": state.queue_running == 0,
        "reindex_after_restore": "pass",
    }


def _metrics(state: SimulationState, *, events: int) -> dict[str, Any]:
    backlog = state.queue_pending + state.queue_running + state.queue_retryable + state.queue_dead_letter
    retrieval_degradation = round(max(0.0, 0.92 - state.retrieval_precision_at_5), 4)
    citation_degradation = round(1 - state.citation_integrity, 4)
    return {
        "total_uploads": state.total_uploads,
        "lifecycle_transitions": state.lifecycle_transitions,
        "reindex_operations": state.reindex_operations,
        "restore_operations": state.restore_operations,
        "cleanup_cycles": state.cleanup_cycles,
        "stale_index_growth": state.stale_index_entries,
        "queue_backlog": backlog,
        "queue_backlog_drift": state.queue_pending + state.queue_retryable + state.queue_dead_letter,
        "orphan_growth": state.orphans,
        "retry_accumulation": state.retry_accumulated,
        "retrieval_degradation": retrieval_degradation,
        "citation_degradation": citation_degradation,
        "retrieval_precision_at_5": state.retrieval_precision_at_5,
        "retrieval_recall_at_5": state.retrieval_recall_at_5,
        "citation_integrity": state.citation_integrity,
        "error_rate": round(state.error_count / max(events, 1), 4),
    }


def _evaluate_stop_criteria(metrics: dict[str, Any]) -> list[str]:
    events: list[str] = []
    if metrics["stale_index_growth"] > STOP_THRESHOLDS["stale_index_growth"]:
        events.append(f"stale_index_growth={metrics['stale_index_growth']}")
    if metrics["queue_backlog"] > STOP_THRESHOLDS["queue_backlog"]:
        events.append(f"queue_backlog={metrics['queue_backlog']}")
    if metrics["queue_backlog_drift"] > STOP_THRESHOLDS["queue_backlog_drift"]:
        events.append(f"queue_backlog_drift={metrics['queue_backlog_drift']}")
    if metrics["orphan_growth"] > STOP_THRESHOLDS["orphans"]:
        events.append(f"orphan_growth={metrics['orphan_growth']}")
    if metrics["retry_accumulation"] > STOP_THRESHOLDS["retry_accumulation"]:
        events.append(f"retry_accumulation={metrics['retry_accumulation']}")
    if metrics["retrieval_degradation"] > STOP_THRESHOLDS["retrieval_degradation"]:
        events.append(f"retrieval_degradation={metrics['retrieval_degradation']}")
    if metrics["citation_degradation"] > STOP_THRESHOLDS["citation_degradation"]:
        events.append(f"citation_degradation={metrics['citation_degradation']}")
    if metrics["retrieval_precision_at_5"] < STOP_THRESHOLDS["retrieval_precision_at_5"]:
        events.append(f"retrieval_precision_at_5={metrics['retrieval_precision_at_5']}")
    if metrics["retrieval_recall_at_5"] < STOP_THRESHOLDS["retrieval_recall_at_5"]:
        events.append(f"retrieval_recall_at_5={metrics['retrieval_recall_at_5']}")
    if metrics["error_rate"] > STOP_THRESHOLDS["error_rate"]:
        events.append(f"error_rate={metrics['error_rate']}")
    return events


def _evaluate_warnings(metrics: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if metrics["queue_backlog"] > 15:
        warnings.append(f"queue_backlog warning={metrics['queue_backlog']}")
    if metrics["queue_backlog_drift"] > 8:
        warnings.append(f"queue_backlog_drift warning={metrics['queue_backlog_drift']}")
    if metrics["retry_accumulation"] > 4:
        warnings.append(f"retry_accumulation warning={metrics['retry_accumulation']}")
    if metrics["citation_degradation"] > 0.05:
        warnings.append(f"citation_degradation warning={metrics['citation_degradation']}")
    if metrics["retrieval_precision_at_5"] < 0.85:
        warnings.append(f"retrieval_precision_at_5 warning={metrics['retrieval_precision_at_5']}")
    return warnings


def write_reports(*, cycles: int = 28, restore_every: int = 7, output_dir: Path | None = None) -> dict[str, Any]:
    report = run_simulation(cycles=cycles, restore_every=restore_every)
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
    metrics = report["final_metrics"]
    lines = [
        "# M5 Longrun Simulation",
        "",
        f"Status: `{report['status']}`",
        f"Cycles: `{report['cycles']}`",
        "",
        "## Simulationsprofil",
        "",
        f"Uploads insgesamt: `{metrics['total_uploads']}`",
        f"Lifecycle-Wechsel: `{metrics['lifecycle_transitions']}`",
        f"Reindex-Zyklen: `{metrics['reindex_operations']}`",
        f"Restore-Zyklen: `{metrics['restore_operations']}`",
        f"Cleanup-Zyklen: `{metrics['cleanup_cycles']}`",
        "",
        "| Metrik | Wert | Stop-Schwelle |",
        "|---|---:|---:|",
        f"| stale_index_growth | {metrics['stale_index_growth']} | {STOP_THRESHOLDS['stale_index_growth']} |",
        f"| queue_backlog | {metrics['queue_backlog']} | {STOP_THRESHOLDS['queue_backlog']} |",
        f"| queue_backlog_drift | {metrics['queue_backlog_drift']} | {STOP_THRESHOLDS['queue_backlog_drift']} |",
        f"| orphan_growth | {metrics['orphan_growth']} | {STOP_THRESHOLDS['orphans']} |",
        f"| retry_accumulation | {metrics['retry_accumulation']} | {STOP_THRESHOLDS['retry_accumulation']} |",
        f"| retrieval_degradation | {metrics['retrieval_degradation']} | {STOP_THRESHOLDS['retrieval_degradation']} |",
        f"| citation_degradation | {metrics['citation_degradation']} | {STOP_THRESHOLDS['citation_degradation']} |",
        f"| retrieval_precision_at_5 | {metrics['retrieval_precision_at_5']} | {STOP_THRESHOLDS['retrieval_precision_at_5']} |",
        f"| retrieval_recall_at_5 | {metrics['retrieval_recall_at_5']} | {STOP_THRESHOLDS['retrieval_recall_at_5']} |",
        f"| error_rate | {metrics['error_rate']} | {STOP_THRESHOLDS['error_rate']} |",
        "",
        "## Driftmetriken",
        "",
        "- orphan growth zeigt schleichende Referenzverluste nach Delete-, Restore- und Cleanup-Zyklen.",
        "- stale index growth misst residuelle Indexeintraege nach Lifecycle-Wechseln und Reindexen.",
        "- retrieval degradation misst den Verlust gegenueber der Baseline Precision@5 von 0.92.",
        "- queue backlog drift misst den driftenden Anteil nicht abgearbeiteter Queue-Jobs.",
        "- retry accumulation misst kumulierte Retry-Last ueber alle Zyklen.",
        "- citation degradation misst den Verlust historischer Zitierintegritaet.",
        "",
        "## Stop-Kriterien",
        "",
    ]
    lines.extend(f"- {event}" for event in report["stop_events"]) if report["stop_events"] else lines.append("Keine Stop-Kriterien verletzt.")
    if report["warnings"]:
        lines += ["", "## Warnungen", ""]
        lines.extend(f"- {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"
