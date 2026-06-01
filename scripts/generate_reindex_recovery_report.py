from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
OUTPUT_PATH = CURRENT_DIR / "reindex_recovery_report.json"
LEGACY_REINDEX = REPO_ROOT / "reindex_recovery_report.json"
LEGACY_RETRIEVAL = REPO_ROOT / "retrieval_validation_report.json"


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root must be object"
    return payload, None


def _write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    tmp_path.write_text(text, encoding="utf-8")

    parsed = json.loads(tmp_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Generated report root must be JSON object")

    tmp_path.replace(path)


def _pass_report(*, timestamp: str, reindex: dict[str, Any], retrieval: dict[str, Any] | None) -> dict[str, Any]:
    chunk_count = int(reindex.get("chunk_count") or 0)
    reindex_status = str(reindex.get("reindex_status") or "").lower()
    search_results = int((retrieval or {}).get("search_results") or 0)
    chat_results = int((retrieval or {}).get("chat_results") or 0)

    blockers: list[dict[str, Any]] = []
    ok = reindex_status == "completed" and chunk_count > 0
    if not ok:
        blockers.append(
            {
                "id": "legacy_reindex_not_completed",
                "severity": "blocking",
                "reason": "Legacy reindex report does not show completed status with chunks > 0.",
            }
        )

    status = "PASS" if ok else "BLOCKED"
    decision = "GO" if ok else "NO_GO"

    return {
        "report_schema_version": 1,
        "report_name": "reindex_recovery_report",
        "gate": "reindex_recovery_report",
        "generated_by": "gate_validator",
        "timestamp": timestamp,
        "environment": "local",
        "report_type": "truth",
        "status": status,
        "result": status,
        "collected": 1,
        "passed": 1 if ok else 0,
        "failed": 0,
        "errors": 0 if ok else 1,
        "skipped": 0,
        "exit_code": 0 if ok else 2,
        "blockers": blockers,
        "source_command": "python scripts/generate_reindex_recovery_report.py",
        "decision": {"go_no_go": decision, "result": decision},
        "reindex_status": reindex_status,
        "chunk_count": chunk_count,
        "search_results": search_results,
        "chat_results": chat_results,
        "inputs": {
            "legacy_reindex": str(LEGACY_REINDEX.relative_to(REPO_ROOT)),
            "legacy_retrieval": str(LEGACY_RETRIEVAL.relative_to(REPO_ROOT)),
        },
    }


def _blocked_report(*, timestamp: str, reason: str) -> dict[str, Any]:
    return {
        "report_schema_version": 1,
        "report_name": "reindex_recovery_report",
        "gate": "reindex_recovery_report",
        "generated_by": "gate_validator",
        "timestamp": timestamp,
        "environment": "local",
        "report_type": "truth",
        "status": "BLOCKED",
        "result": "BLOCKED",
        "collected": 1,
        "passed": 0,
        "failed": 0,
        "errors": 1,
        "skipped": 0,
        "exit_code": 2,
        "blockers": [
            {
                "id": "reindex_recovery_truth_not_executed",
                "severity": "blocking",
                "reason": reason,
            }
        ],
        "source_command": "pytest -q backend/tests/postgres_truth/test_m4e_reindex_recovery_truth.py",
        "decision": {"go_no_go": "NO_GO", "result": "NO_GO"},
        "inputs": {
            "legacy_reindex": str(LEGACY_REINDEX.relative_to(REPO_ROOT)),
            "legacy_retrieval": str(LEGACY_RETRIEVAL.relative_to(REPO_ROOT)),
        },
    }


def main() -> int:
    now = datetime.now(UTC).isoformat()
    legacy_reindex, reindex_error = _load_json(LEGACY_REINDEX)
    legacy_retrieval, _ = _load_json(LEGACY_RETRIEVAL)

    if legacy_reindex is None:
        payload = _blocked_report(
            timestamp=now,
            reason=(
                "No valid legacy reindex report available. "
                "Run pytest for test_m4e_reindex_recovery_truth.py and regenerate."
            ),
        )
    elif reindex_error is not None:
        payload = _blocked_report(
            timestamp=now,
            reason=f"Legacy reindex report is invalid: {reindex_error}",
        )
    else:
        payload = _pass_report(timestamp=now, reindex=legacy_reindex, retrieval=legacy_retrieval)

    _write_atomic_json(OUTPUT_PATH, payload)
    print(f"reindex_recovery_report = {payload['status']}")
    print(f"Wrote: {OUTPUT_PATH}")
    return int(payload.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
