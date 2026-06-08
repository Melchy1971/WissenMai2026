from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
DEFAULT_OUTPUT = CURRENT_DIR / "m5b_start_gate.json"

M5A_DATA_QUALITY_GATE = "m5a_data_quality_gate.json"
RETRIEVAL_BASELINE = "retrieval_quality_baseline_report.json"
DOCUMENTATION_TRUTH_LINT = "documentation_truth_lint.json"
M5B_ARCHITECTURE = REPO_ROOT / "docs" / "m5b-drift-architecture.md"

M5A_BLOCKER_ID = "M5A_PARENT_GATE_NOT_PASSED"
M5B_IMPLEMENTATION_GATE_REQUIRED = "M5B_IMPLEMENTATION_GATE_REQUIRED"


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root must be an object"
    return payload, None


def _status(report: dict[str, Any] | None) -> str:
    if not report:
        return "MISSING"
    return str(report.get("status") or report.get("result") or "UNKNOWN").upper()


def _decision(report: dict[str, Any] | None) -> str | None:
    if not report:
        return None
    raw = report.get("decision")
    if isinstance(raw, dict):
        raw = raw.get("go_no_go") or raw.get("result")
    return str(raw).upper().replace("-", "_") if raw is not None else None


def _is_pass_gate(report: dict[str, Any] | None) -> bool:
    if report is None:
        return False
    return (
        _status(report) == "PASS"
        and _decision(report) in {None, "GO"}
        and report.get("failed", 0) == 0
        and report.get("errors", 0) == 0
        and report.get("skipped", 0) == 0
        and report.get("exit_code", 0) == 0
    )


def _architecture_status() -> str:
    if not M5B_ARCHITECTURE.exists():
        return "MISSING"
    text = M5B_ARCHITECTURE.read_text(encoding="utf-8", errors="replace")
    return "DRAFT" if "Status: `DRAFT`" in text else "AVAILABLE"


def build_m5b_start_gate(
    report_dir: Path = CURRENT_DIR,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(timezone.utc).isoformat()
    m5a, m5a_error = _load_json(report_dir / M5A_DATA_QUALITY_GATE)
    retrieval, retrieval_error = _load_json(report_dir / RETRIEVAL_BASELINE)
    doc_lint, doc_error = _load_json(report_dir / DOCUMENTATION_TRUTH_LINT)

    m5a_pass = m5a_error is None and _is_pass_gate(m5a)
    architecture_status = _architecture_status()
    retrieval_decision = _decision(retrieval)
    retrieval_release_grade = bool((retrieval or {}).get("decision", {}).get("baseline_release_grade")) if isinstance((retrieval or {}).get("decision"), dict) else False

    blockers: list[dict[str, Any]] = []
    if not m5a_pass:
        blockers.append(
            {
                "id": M5A_BLOCKER_ID,
                "severity": "blocking",
                "reason": (
                    "M5b bleibt BLOCKED bis reports/current/m5a_data_quality_gate.json "
                    "status=PASS und decision.go_no_go=GO meldet."
                ),
                "source": f"reports/current/{M5A_DATA_QUALITY_GATE}",
            }
        )

    status = "PREPARED" if m5a_pass else "BLOCKED"
    implementation_blockers = [
        {
            "id": M5B_IMPLEMENTATION_GATE_REQUIRED,
            "severity": "blocking",
            "detail": "M5b Implementierung bleibt gesperrt bis ein separates M5b Implementation Gate PASS/GO meldet.",
            "source": "reports/current/m5b_implementation_gate.json",
        }
    ]
    if not retrieval_release_grade:
        implementation_blockers.append(
            {
                "id": "retrieval_baseline_not_release_grade",
                "severity": "blocking",
                "detail": "retrieval_quality_baseline_report: baseline_release_grade=false, requires_golden_retrieval_benchmark=true",
                "source": f"reports/current/{RETRIEVAL_BASELINE}",
            }
        )
    if architecture_status == "DRAFT":
        implementation_blockers.append(
            {
                "id": "m5b_architecture_draft",
                "severity": "blocking",
                "detail": "m5b-drift-architecture status=DRAFT - Architektur muss finalisiert sein vor Implementierungsstart",
                "source": "docs/m5b-drift-architecture.md",
            }
        )

    return {
        "report_schema_version": 1,
        "report_name": "m5b_start_gate",
        "generated_by": "gate_validator",
        "timestamp": generated_at,
        "generated_at": generated_at,
        "gate": "m5b_start_gate",
        "environment": "local",
        "report_type": "gate",
        "status": status,
        "result": status,
        "decision": {
            "go_no_go": "GO" if status == "PREPARED" else "NO_GO",
            "result": "GO" if status == "PREPARED" else "NO_GO",
            "preparation_status": status,
            "m5b_preparation_allowed": status == "PREPARED",
            "m5b_implementation_allowed": False,
            "m5b_implementation_gate_required": True,
            "implementation_state": "NOT_IMPLEMENTING",
            "forbidden_state": "IMPLEMENTING",
        },
        "preconditions": {
            "m5a_data_quality_gate": {
                "report": f"reports/current/{M5A_DATA_QUALITY_GATE}",
                "status": _status(m5a),
                "decision": _decision(m5a),
                "timestamp": (m5a or {}).get("timestamp") or (m5a or {}).get("generated_at"),
                "passed": m5a_pass,
                "error": m5a_error,
                "rule": "M5b darf erst PREPARED werden, wenn m5a_data_quality_gate PASS/GO meldet.",
            },
            "retrieval_quality_baseline_report": {
                "report": f"reports/current/{RETRIEVAL_BASELINE}",
                "status": _status(retrieval),
                "result": (retrieval or {}).get("result"),
                "decision": retrieval_decision,
                "timestamp": (retrieval or {}).get("timestamp") or (retrieval or {}).get("generated_at"),
                "passed": retrieval_release_grade,
                "error": retrieval_error,
                "note": "Kein Blocker fuer PREPARED, aber Blocker fuer Implementierungsfreigabe.",
            },
            "m5b_drift_architecture": {
                "source": "docs/m5b-drift-architecture.md",
                "status": architecture_status,
                "planning_allowed": True,
                "implementation_allowed": False,
                "note": "Planung erlaubt; Implementierung nur mit separatem M5b Implementation Gate.",
            },
            "documentation_truth_lint": {
                "report": f"reports/current/{DOCUMENTATION_TRUTH_LINT}",
                "status": _status(doc_lint),
                "timestamp": (doc_lint or {}).get("timestamp") or (doc_lint or {}).get("generated_at"),
                "passed": doc_error is None and _status(doc_lint) == "PASS",
                "error": doc_error,
            },
        },
        "implementation_blockers": implementation_blockers,
        "blockers": blockers,
        "rule": (
            "Wenn m5a_data_quality_gate nicht PASS/GO ist, bleibt M5b BLOCKED mit "
            "M5A_PARENT_GATE_NOT_PASSED. Bei M5a PASS darf M5b PREPARED werden; "
            "Implementierung erfordert ein separates M5b Implementation Gate."
        ),
        "collected": 1,
        "passed": 1 if status == "PREPARED" else 0,
        "failed": 0 if status == "PREPARED" else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if status == "PREPARED" else 1,
        "source_command": "python scripts/generate_m5b_start_gate.py",
    }


def write_output(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the M5b start gate.")
    parser.add_argument("--report-dir", type=Path, default=CURRENT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    payload = build_m5b_start_gate(args.report_dir)
    write_output(payload, args.output)
    print(f"M5b Start Gate = {payload['status']}")
    for blocker in payload["blockers"]:
        print(f"  BLOCKER: {blocker['id']} - {blocker['reason']}")
    print(f"Wrote: {args.output}")
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
