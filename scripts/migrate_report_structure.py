from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
CURRENT_DIR = REPORTS_DIR / "current"
ARCHIVE_DIR = REPORTS_DIR / "archive"

CANONICAL_REPORTS: dict[str, dict[str, Any]] = {
    "m3a_frontend_truth": {
        "current": "m3a_frontend_truth.json",
        "sources": [
            "current/m3a_frontend_truth.json",
            "frontend_truth_report.json",
            "current/m3a.json",
            "m3a_truth_report.json",
        ],
    },
    "m3a_release_candidate": {
        "current": "m3a_release_candidate.json",
        "sources": ["current/m3a_release_candidate.json", "m3a_release_candidate.json"],
    },
    "m4a_auth_truth": {
        "current": "m4a_auth_truth.json",
        "sources": ["current/m4a_auth_truth.json", "current/m4a.json", "m4a_auth_truth_report.json"],
    },
    "m4b_upload_queue_truth": {
        "current": "m4b_upload_queue_truth.json",
        "sources": ["current/m4b_upload_queue_truth.json", "current/m4b.json", "m4b_upload_queue_truth_report.json"],
    },
    "m4c_lifecycle_retrieval_truth": {
        "current": "m4c_lifecycle_retrieval_truth.json",
        "sources": ["current/m4c_lifecycle_retrieval_truth.json", "current/m4c.json", "m4c_lifecycle_retrieval_truth_report.json"],
    },
    "m4e_backup_restore_truth": {
        "current": "m4e_backup_restore_truth.json",
        "sources": ["current/m4e_backup_restore_truth.json", "current/m4e.json", "m4e_backup_restore_truth_report.json"],
    },
    "masterplan_status": {
        "current": "masterplan_status.json",
        "sources": ["current/masterplan_status.json", "masterplan_status.json"],
    },
}


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _archive_path(gate: str, timestamp: str, source: Path) -> Path:
    return ARCHIVE_DIR / gate / f"{timestamp}_{source.name}"


def _move_with_collision_handling(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.move(str(source), str(target))
        return target

    stem = target.stem
    suffix = target.suffix
    counter = 2
    while True:
        candidate = target.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            shutil.move(str(source), str(candidate))
            return candidate
        counter += 1


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _is_manual_gate_status_report(path: Path) -> bool:
    payload = _load_json(path)
    if not payload:
        return False
    return payload.get("status") in {"PASS", "FAIL", "BLOCKED"} and payload.get("generated_by") != "gate_validator"


def _infer_gate(path: Path) -> str:
    name = path.name
    for gate, config in CANONICAL_REPORTS.items():
        if name == config["current"] or any(name == Path(source).name for source in config["sources"]):
            return gate
    payload = _load_json(path)
    if payload:
        marker = payload.get("marker") or payload.get("gate") or payload.get("name") or payload.get("report")
        if isinstance(marker, str) and marker.strip():
            return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in marker.strip().lower())
    return "legacy"


def _candidate_paths(relative_sources: list[str]) -> list[Path]:
    return [REPORTS_DIR / source for source in relative_sources]


def migrate_reports(*, timestamp: str | None = None) -> dict[str, Any]:
    ts = timestamp or _timestamp()
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    log: dict[str, Any] = {
        "timestamp": ts,
        "canonical_reports": {},
        "archived": [],
        "missing_sources": [],
        "current_dir": _relative(CURRENT_DIR),
        "archive_dir": _relative(ARCHIVE_DIR),
    }

    selected_sources: set[Path] = set()
    for gate, config in CANONICAL_REPORTS.items():
        target = CURRENT_DIR / config["current"]
        source = None
        for candidate in _candidate_paths(config["sources"]):
            if not candidate.exists():
                continue
            if _is_manual_gate_status_report(candidate):
                archived = _move_with_collision_handling(candidate, _archive_path(gate, ts, candidate))
                log["archived"].append({
                    "reason": "manual_gate_status_report",
                    "gate": gate,
                    "from": _relative(candidate),
                    "to": _relative(archived),
                })
                continue
            source = candidate
            break
        if source is None:
            log["missing_sources"].append({"gate": gate, "target": _relative(target), "candidates": config["sources"]})
            continue

        selected_sources.add(source.resolve())
        if target.exists() and target.resolve() != source.resolve():
            archived_target = _move_with_collision_handling(target, _archive_path(gate, ts, target))
            log["archived"].append({
                "reason": "previous_current",
                "gate": gate,
                "from": _relative(target),
                "to": _relative(archived_target),
            })

        if source.resolve() != target.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))

        log["canonical_reports"][gate] = {
            "path": _relative(target),
            "source": _relative(source),
        }

    for path in sorted(REPORTS_DIR.glob("*.json")):
        if path.resolve() in selected_sources:
            continue
        gate = _infer_gate(path)
        archived = _move_with_collision_handling(path, _archive_path(gate, ts, path))
        log["archived"].append({
            "reason": "manual_gate_status_report" if _is_manual_gate_status_report(archived) else "root_legacy_json",
            "gate": gate,
            "from": _relative(path),
            "to": _relative(archived),
        })

    for path in sorted(CURRENT_DIR.glob("*.json")):
        if path.name in {config["current"] for config in CANONICAL_REPORTS.values()}:
            continue
        gate = _infer_gate(path)
        archived = _move_with_collision_handling(path, _archive_path(gate, ts, path))
        log["archived"].append({
            "reason": "manual_gate_status_report" if _is_manual_gate_status_report(archived) else "noncanonical_current_json",
            "gate": gate,
            "from": _relative(path),
            "to": _relative(archived),
        })

    log_path = ARCHIVE_DIR / "report_migration_log.json"
    if log_path.exists():
        archived_log = _move_with_collision_handling(log_path, _archive_path("migration_log", ts, log_path))
        log["archived"].append({
            "reason": "previous_archive_log",
            "gate": "migration_log",
            "from": _relative(log_path),
            "to": _relative(archived_log),
        })
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return log


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate reports to the canonical reports/current + reports/archive layout.")
    parser.add_argument("--timestamp", help="Archive timestamp prefix, defaults to current UTC time.")
    args = parser.parse_args()
    log = migrate_reports(timestamp=args.timestamp)
    print("Report migration complete.")
    print(f"Current reports: {len(log['canonical_reports'])}")
    print(f"Archived reports: {len(log['archived'])}")
    print(f"Missing canonical sources: {len(log['missing_sources'])}")
    print(f"Archive log: {ARCHIVE_DIR / 'report_migration_log.json'}")
    return 0 if not log["missing_sources"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
