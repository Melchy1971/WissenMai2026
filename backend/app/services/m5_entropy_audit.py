from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
LONGRUN_LATEST = REPO_ROOT / "reports" / "m5_longrun" / "latest.json"
RETRIEVAL_LATEST = REPO_ROOT / "reports" / "m5_retrieval" / "latest.json"
REPORT_DIR = REPO_ROOT / "reports" / "m5_entropy"
SUMMARY_PATH = REPO_ROOT / "reports" / "m5_entropy_audit.md"


def run_audit(
    *,
    longrun_report: dict[str, Any] | None = None,
    retrieval_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    longrun = longrun_report or _read_json(LONGRUN_LATEST)
    retrieval = retrieval_report or _read_json(RETRIEVAL_LATEST)
    categories = [
        _stale_queue_jobs(longrun),
        _outdated_backups(longrun),
        _orphan_growth(longrun),
        _stale_index_entries(longrun),
        _historical_citation_drift(retrieval),
        _duplicate_growth(retrieval),
        _cleanup_residue(longrun),
    ]
    aging_risks = [category for category in categories if category["risk"] in {"medium", "high"}]
    status = "blocked" if any(category["risk"] == "high" for category in categories) else "watch" if aging_risks else "pass"
    return {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "audit_version": "m5-data-aging-entropy-v1",
        "status": status,
        "sources": {
            "longrun": str(LONGRUN_LATEST),
            "retrieval": str(RETRIEVAL_LATEST),
            "longrun_generated_at": longrun.get("generated_at"),
            "retrieval_generated_at": retrieval.get("generated_at"),
        },
        "entropy_matrix": categories,
        "aging_risks": aging_risks,
        "prevention_measures": _prevention_measures(categories),
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required audit source is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _cycle_metrics(longrun: dict[str, Any], metric: str) -> list[float]:
    values: list[float] = []
    for cycle in longrun.get("cycles_detail", []):
        metrics = cycle.get("metrics", {})
        value = metrics.get(metric)
        if isinstance(value, int | float):
            values.append(float(value))
    return values


def _growth(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"start": None, "end": None, "delta": None, "per_cycle": None, "max": None}
    delta = round(values[-1] - values[0], 4)
    denominator = max(len(values) - 1, 1)
    return {
        "start": values[0],
        "end": values[-1],
        "delta": delta,
        "per_cycle": round(delta / denominator, 4),
        "max": max(values),
    }


def _risk_from_threshold(end: float | None, threshold: float, *, increasing_is_bad: bool = True) -> str:
    if end is None:
        return "medium"
    if increasing_is_bad and end > threshold:
        return "high"
    if increasing_is_bad and end > threshold * 0.6:
        return "medium"
    if not increasing_is_bad and end < threshold:
        return "high"
    return "low"


def _stale_queue_jobs(longrun: dict[str, Any]) -> dict[str, Any]:
    values = _cycle_metrics(longrun, "queue_backlog")
    growth = _growth(values)
    threshold = float(longrun.get("thresholds", {}).get("queue_backlog", 25))
    return {
        "category": "stale Queue Jobs",
        "growth_over_time": growth,
        "risk": _risk_from_threshold(growth["end"], threshold),
        "evidence": f"queue_backlog final={growth['end']} max={growth['max']} threshold={threshold}",
        "detection_strategy": "Age-bucket queue rows by status and claimed_at/updated_at; alert on running timeout, retryable backlog, dead_letter growth and missing audit transitions.",
        "cleanup_repair_strategy": "Move timed-out running jobs to retryable, replay dead_letter with advisory lock, cap retry attempts, and preserve replay audit rows.",
    }


def _outdated_backups(longrun: dict[str, Any]) -> dict[str, Any]:
    backup_cycles = [
        int(cycle["cycle"])
        for cycle in longrun.get("cycles_detail", [])
        if isinstance(cycle.get("backup_restore"), dict) and cycle["backup_restore"].get("status") == "pass"
    ]
    cycle_count = int(longrun.get("cycles", 0))
    max_gap = max([backup_cycles[0], *[right - left for left, right in zip(backup_cycles, backup_cycles[1:])], cycle_count - backup_cycles[-1] if backup_cycles else cycle_count])
    risk = "high" if not backup_cycles else "medium" if max_gap > int(longrun.get("restore_every", 7)) else "low"
    return {
        "category": "veraltete Backups",
        "growth_over_time": {"successful_restore_cycles": backup_cycles, "max_backup_age_cycles": max_gap, "cycle_count": cycle_count},
        "risk": risk,
        "evidence": f"restore checks passed at cycles={backup_cycles}; max_backup_age_cycles={max_gap}",
        "detection_strategy": "Track latest successful backup timestamp, verify-backup status, restore dry-run age and checksum drift.",
        "cleanup_repair_strategy": "Fail readiness when no fresh verified backup exists; rotate old backups only after a newer restore-verified backup is present.",
    }


def _orphan_growth(longrun: dict[str, Any]) -> dict[str, Any]:
    values = _cycle_metrics(longrun, "orphan_growth")
    growth = _growth(values)
    return {
        "category": "orphan growth",
        "growth_over_time": growth,
        "risk": "high" if growth["max"] and growth["max"] > 0 else "low",
        "evidence": f"orphan_growth final={growth['end']} max={growth['max']}",
        "detection_strategy": "Run referential integrity probes for chunks without versions, files without documents, citations without message snapshots and index rows without live chunks.",
        "cleanup_repair_strategy": "Dry-run first, delete only provably unreachable rows/files, and require protected counts for historical citations and backup artifacts.",
    }


def _stale_index_entries(longrun: dict[str, Any]) -> dict[str, Any]:
    values = _cycle_metrics(longrun, "stale_index_growth")
    growth = _growth(values)
    return {
        "category": "stale Indexeintraege",
        "growth_over_time": growth,
        "risk": "high" if growth["max"] and growth["max"] > 0 else "low",
        "evidence": f"stale_index_growth final={growth['end']} max={growth['max']}",
        "detection_strategy": "Compare search index document/chunk ids against DB lifecycle state after upload, archive, delete, restore and reindex.",
        "cleanup_repair_strategy": "Run workspace-scoped reindex, remove archived/deleted stale entries, then verify drift report is empty.",
    }


def _historical_citation_drift(retrieval: dict[str, Any]) -> dict[str, Any]:
    summary = retrieval.get("summary", {})
    completeness = float(summary.get("citation_completeness", 0))
    lifecycle_violations = int(summary.get("lifecycle_exclusion_violations", 1))
    risk = "high" if completeness < 0.9 or lifecycle_violations else "low"
    return {
        "category": "historische Citation Drift",
        "growth_over_time": {"citation_completeness": completeness, "lifecycle_exclusion_violations": lifecycle_violations},
        "risk": risk,
        "evidence": f"citation_completeness={completeness}; lifecycle_exclusion_violations={lifecycle_violations}",
        "detection_strategy": "Replay golden citation queries and compare stored citation snapshots against current document lifecycle/source_status.",
        "cleanup_repair_strategy": "Never rewrite historical quote snapshots; repair missing source_status metadata and keep deleted/archived sources visible as historical citations only.",
    }


def _duplicate_growth(retrieval: dict[str, Any]) -> dict[str, Any]:
    duplicate_query = next((query for query in retrieval.get("queries", []) if query.get("query_id") == "GQ-002"), None)
    detected = duplicate_query is not None and duplicate_query.get("recall_at_5") == 1.0
    return {
        "category": "duplicate growth",
        "growth_over_time": {"golden_duplicate_detection": "pass" if detected else "failed", "production_duplicate_cardinality": "not_measured"},
        "risk": "medium" if detected else "high",
        "evidence": "GQ-002 duplicate handling is covered; full DB duplicate cardinality requires a live content_hash aggregation audit.",
        "detection_strategy": "Aggregate by workspace_id + content_hash and by normalized title/source metadata; alert when controlled duplicates exceed expected pairs.",
        "cleanup_repair_strategy": "Keep content_hash uniqueness enforced; merge accidental duplicates only through an audited repair script preserving citations and versions.",
    }


def _cleanup_residue(longrun: dict[str, Any]) -> dict[str, Any]:
    candidate_counts = [
        int(cycle.get("cleanup_dry_run", {}).get("candidate_count", 0))
        for cycle in longrun.get("cycles_detail", [])
    ]
    blocked_counts = [
        int(cycle.get("cleanup_dry_run", {}).get("blocked_count", 0))
        for cycle in longrun.get("cycles_detail", [])
    ]
    growth = _growth([float(value) for value in candidate_counts])
    blocked_max = max(blocked_counts) if blocked_counts else 0
    return {
        "category": "Cleanup-Rueckstaende",
        "growth_over_time": {**growth, "blocked_max": blocked_max},
        "risk": "high" if blocked_max > 0 else "medium" if growth["max"] and growth["max"] > 10 else "low",
        "evidence": f"cleanup candidates final={growth['end']} max={growth['max']}; blocked_max={blocked_max}",
        "detection_strategy": "Run cleanup dry-runs on a schedule and track candidate_count, protected_count and blocked_count deltas.",
        "cleanup_repair_strategy": "Convert recurring dry-run candidates into explicit retention rules; require zero blocked_count before destructive cleanup.",
    }


def _prevention_measures(categories: list[dict[str, Any]]) -> list[str]:
    measures = [
        "Schedule entropy audit after every longrun simulation and before M5 readiness promotion.",
        "Gate M5 on stale_index_growth=0, orphan_growth=0, lifecycle_exclusion_violations=0 and successful restore verification.",
        "Store audit deltas over time so slow growth is visible before thresholds are breached.",
    ]
    if any(category["category"] == "duplicate growth" and category["risk"] != "low" for category in categories):
        measures.append("Add live DB duplicate cardinality audit before treating duplicate growth as fully closed.")
    if any(category["category"] == "stale Queue Jobs" and category["risk"] == "medium" for category in categories):
        measures.append("Add queue age percentiles, not just backlog counts, to separate healthy backlog from stale jobs.")
    return measures


def write_reports(output_dir: Path | None = None) -> dict[str, Any]:
    report = run_audit()
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
    lines = [
        "# M5 Data Aging & Entropy Audit",
        "",
        f"Status: `{report['status']}`",
        f"Audit: `{report['audit_version']}`",
        "",
        "## Entropie-Matrix",
        "",
        "| Kategorie | Risiko | Wachstum ueber Zeit | Erkennung | Cleanup/Repair |",
        "|---|---|---|---|---|",
    ]
    for item in report["entropy_matrix"]:
        lines.append(
            "| {category} | {risk} | {growth} | {detect} | {repair} |".format(
                category=item["category"],
                risk=item["risk"],
                growth=_compact(item["growth_over_time"]),
                detect=item["detection_strategy"],
                repair=item["cleanup_repair_strategy"],
            )
        )
    lines += ["", "## Aging-Risiken", ""]
    if report["aging_risks"]:
        lines.extend(f"- `{item['category']}`: {item['evidence']}" for item in report["aging_risks"])
    else:
        lines.append("Keine harten Aging-Risiken in den aktuellen Baselines.")
    lines += ["", "## Praeventionsmassnahmen", ""]
    lines.extend(f"- {measure}" for measure in report["prevention_measures"])
    return "\n".join(lines) + "\n"


def _compact(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{key}={item}" for key, item in value.items())
    return str(value)
