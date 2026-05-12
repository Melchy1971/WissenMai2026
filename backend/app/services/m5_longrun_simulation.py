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


STOP_THRESHOLDS = {
    "stale_index_growth": 0,
    "queue_backlog": 25,
    "orphans": 0,
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
    state.active_documents += 3
    state.chunks += 9
    state.queue_pending += 3
    if cycle % 5 == 0:
        state.error_count += 1
        state.queue_retryable += 1


def _simulate_queue_retries(state: SimulationState, cycle: int) -> None:
    claimed = min(state.queue_pending, 3)
    state.queue_pending -= claimed
    state.queue_running += claimed
    completed = max(0, state.queue_running - (1 if cycle % 6 == 0 else 0))
    state.queue_running -= completed
    if cycle % 6 == 0 and state.queue_running:
        state.queue_running -= 1
        state.queue_retryable += 1
    if state.queue_retryable and cycle % 3 == 0:
        state.queue_retryable -= 1
        state.queue_pending += 1
    if cycle % 14 == 0:
        state.queue_dead_letter += 1
    if state.queue_dead_letter and cycle % 7 == 0:
        state.queue_dead_letter -= 1
        state.queue_pending += 1


def _simulate_lifecycle_changes(state: SimulationState, cycle: int) -> None:
    if cycle % 2 == 0 and state.active_documents:
        state.active_documents -= 1
        state.archived_documents += 1
        state.stale_index_entries += 3
    if cycle % 4 == 0 and state.archived_documents:
        state.archived_documents -= 1
        state.active_documents += 1
        state.stale_index_entries += 3
    if cycle % 5 == 0 and state.active_documents:
        state.active_documents -= 1
        state.deleted_documents += 1
        state.stale_index_entries += 3


def _simulate_reindex(state: SimulationState) -> None:
    state.stale_index_entries = 0


def _simulate_parallel_search_chat(state: SimulationState, cycle: int) -> None:
    pressure = min(0.08, cycle * 0.001)
    state.retrieval_precision_at_5 = round(max(0.84, 0.92 - pressure), 3)
    state.retrieval_recall_at_5 = round(max(0.87, 0.90 - pressure / 2), 3)


def _simulate_drift_detection(state: SimulationState) -> dict[str, Any]:
    return {
        "stale_index_entries": state.stale_index_entries,
        "orphans": state.orphans,
        "status": "ok" if state.stale_index_entries == 0 and state.orphans == 0 else "drifted",
    }


def _simulate_cleanup_dry_run(state: SimulationState) -> dict[str, Any]:
    candidates = state.queue_dead_letter + state.orphans
    protected = state.queue_dead_letter
    return {
        "candidate_count": candidates,
        "protected_count": protected,
        "blocked_count": state.orphans,
        "status": "ok" if state.orphans == 0 else "blocked",
    }


def _simulate_backup_restore(state: SimulationState, cycle: int) -> dict[str, Any]:
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
    return {
        "stale_index_growth": state.stale_index_entries,
        "queue_backlog": backlog,
        "orphan_growth": state.orphans,
        "retrieval_precision_at_5": state.retrieval_precision_at_5,
        "retrieval_recall_at_5": state.retrieval_recall_at_5,
        "error_rate": round(state.error_count / max(events, 1), 4),
    }


def _evaluate_stop_criteria(metrics: dict[str, Any]) -> list[str]:
    events: list[str] = []
    if metrics["stale_index_growth"] > STOP_THRESHOLDS["stale_index_growth"]:
        events.append(f"stale_index_growth={metrics['stale_index_growth']}")
    if metrics["queue_backlog"] > STOP_THRESHOLDS["queue_backlog"]:
        events.append(f"queue_backlog={metrics['queue_backlog']}")
    if metrics["orphan_growth"] > STOP_THRESHOLDS["orphans"]:
        events.append(f"orphan_growth={metrics['orphan_growth']}")
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
        "| Metrik | Wert | Stop-Schwelle |",
        "|---|---:|---:|",
        f"| stale_index_growth | {metrics['stale_index_growth']} | {STOP_THRESHOLDS['stale_index_growth']} |",
        f"| queue_backlog | {metrics['queue_backlog']} | {STOP_THRESHOLDS['queue_backlog']} |",
        f"| orphan_growth | {metrics['orphan_growth']} | {STOP_THRESHOLDS['orphans']} |",
        f"| retrieval_precision_at_5 | {metrics['retrieval_precision_at_5']} | {STOP_THRESHOLDS['retrieval_precision_at_5']} |",
        f"| retrieval_recall_at_5 | {metrics['retrieval_recall_at_5']} | {STOP_THRESHOLDS['retrieval_recall_at_5']} |",
        f"| error_rate | {metrics['error_rate']} | {STOP_THRESHOLDS['error_rate']} |",
        "",
        "## Stop-Kriterien",
        "",
    ]
    lines.extend(f"- {event}" for event in report["stop_events"]) if report["stop_events"] else lines.append("Keine Stop-Kriterien verletzt.")
    if report["warnings"]:
        lines += ["", "## Warnungen", ""]
        lines.extend(f"- {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"
