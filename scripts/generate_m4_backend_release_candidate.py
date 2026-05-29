from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"

SPLIT_REPORTS = (
    "m4a_auth_truth.json",
    "m4b_upload_queue_truth.json",
    "m4c_lifecycle_retrieval_truth.json",
    "m4e_backup_restore_truth.json",
)
AGGREGATE_REPORT = "m4_truth_report.json"
PREFLIGHT_REPORT = "report_truth_preflight.json"
DOC_LINT_REPORT = "documentation_truth_lint.json"
OUTPUT_JSON = CURRENT_DIR / "m4_backend_release_candidate.json"
OUTPUT_MD = CURRENT_DIR / "m4_backend_release_candidate.md"


def _commit_hash() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _load_report(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "report root must be a JSON object"
    return payload, None


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _report_blockers(name: str, report: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    collected = _int_value(report.get("collected"))
    passed = _int_value(report.get("passed"))
    failed = _int_value(report.get("failed"))
    errors = _int_value(report.get("errors"))
    skipped = _int_value(report.get("skipped"))
    exit_code = _int_value(report.get("exit_code"))

    if report.get("status") != "PASS":
        blockers.append(f"{name}: status must be PASS, got {report.get('status')!r}")
    if collected <= 0:
        blockers.append(f"{name}: collected must be > 0, got {report.get('collected')!r}")
    if passed != collected:
        blockers.append(f"{name}: passed ({passed}) must equal collected ({collected})")
    if failed != 0:
        blockers.append(f"{name}: failed must be 0, got {failed}")
    if errors != 0:
        blockers.append(f"{name}: errors must be 0, got {errors}")
    if skipped != 0:
        blockers.append(f"{name}: skipped must be 0, got {skipped}")
    if exit_code != 0:
        blockers.append(f"{name}: exit_code must be 0, got {exit_code}")
    return blockers


def build_report_truth_preflight(
    report_dir: Path = CURRENT_DIR,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    timestamp = timestamp or datetime.now(UTC).isoformat()
    required = [*SPLIT_REPORTS, AGGREGATE_REPORT, DOC_LINT_REPORT]
    checks: list[dict[str, Any]] = []
    blockers: list[dict[str, str]] = []

    for name in required:
        path = report_dir / name
        payload, error = _load_report(path)
        if error:
            checks.append({"report": name, "status": "FAIL", "reason": error})
            blockers.append({"gate": "report_truth_preflight", "severity": "critical", "reason": f"{name}: {error}"})
            continue
        checks.append({
            "report": name,
            "status": "PASS",
            "reason": None,
            "report_status": payload.get("status"),
            "timestamp": payload.get("timestamp") or payload.get("generated_at"),
        })

    status = "PASS" if not blockers else "FAIL"
    report = {
        "report_schema_version": 1,
        "report_name": "report_truth_preflight",
        "generated_by": "gate_validator",
        "timestamp": timestamp,
        "gate": "report_truth_preflight",
        "status": status,
        "result": status,
        "environment": "local",
        "report_type": "gate",
        "collected": len(checks),
        "passed": sum(1 for check in checks if check["status"] == "PASS"),
        "failed": sum(1 for check in checks if check["status"] == "FAIL"),
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if status == "PASS" else 1,
        "checks": checks,
        "blockers": blockers,
        "source_command": "python scripts/generate_m4_backend_release_candidate.py",
    }
    commit = _commit_hash()
    if commit:
        report["commit_hash"] = commit
    return report


def _component(name: str, report_dir: Path) -> tuple[dict[str, Any], list[str]]:
    path = report_dir / name
    payload, error = _load_report(path)
    if error or payload is None:
        blockers = [f"{name}: {error}"]
        return {
            "name": name,
            "path": f"reports/current/{name}",
            "available": False,
            "status": "FAIL",
            "blockers": blockers,
        }, blockers

    blockers = _report_blockers(name, payload)
    return {
        "name": name,
        "path": f"reports/current/{name}",
        "available": True,
        "status": "PASS" if not blockers else "FAIL",
        "report_status": payload.get("status"),
        "collected": payload.get("collected"),
        "passed": payload.get("passed"),
        "failed": payload.get("failed"),
        "errors": payload.get("errors"),
        "skipped": payload.get("skipped"),
        "exit_code": payload.get("exit_code"),
        "timestamp": payload.get("timestamp") or payload.get("generated_at"),
        "blockers": blockers,
    }, blockers


def _documentation_blockers(report_dir: Path) -> tuple[dict[str, Any], list[str]]:
    payload, error = _load_report(report_dir / DOC_LINT_REPORT)
    if error or payload is None:
        return {
            "name": DOC_LINT_REPORT,
            "path": f"reports/current/{DOC_LINT_REPORT}",
            "available": False,
            "status": "FAIL",
            "blockers": [f"{DOC_LINT_REPORT}: {error}"],
        }, [f"{DOC_LINT_REPORT}: {error}"]

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    errors = _int_value(summary.get("errors"))
    blockers = []
    if errors:
        blockers.append(f"{DOC_LINT_REPORT}: documentation lint has {errors} error(s)")
    if payload.get("status") == "FAIL" or payload.get("result") == "FAIL":
        blockers.append(f"{DOC_LINT_REPORT}: status/result must not be FAIL")

    return {
        "name": DOC_LINT_REPORT,
        "path": f"reports/current/{DOC_LINT_REPORT}",
        "available": True,
        "status": "PASS" if not blockers else "FAIL",
        "report_status": payload.get("status") or payload.get("result"),
        "errors": errors,
        "warnings": _int_value(summary.get("warnings")),
        "timestamp": payload.get("timestamp") or payload.get("generated_at"),
        "blockers": blockers,
    }, blockers


def build_release_candidate(
    report_dir: Path = CURRENT_DIR,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    timestamp = timestamp or datetime.now(UTC).isoformat()
    components: list[dict[str, Any]] = []
    blocker_reasons: list[str] = []

    for name in SPLIT_REPORTS:
        component, blockers = _component(name, report_dir)
        components.append(component)
        blocker_reasons.extend(blockers)

    aggregate, blockers = _component(AGGREGATE_REPORT, report_dir)
    components.append(aggregate)
    blocker_reasons.extend(blockers)

    preflight, blockers = _component(PREFLIGHT_REPORT, report_dir)
    components.append(preflight)
    blocker_reasons.extend(blockers)

    documentation, blockers = _documentation_blockers(report_dir)
    components.append(documentation)
    blocker_reasons.extend(blockers)

    collected = sum(_int_value(component.get("collected")) for component in components if component["name"] in SPLIT_REPORTS)
    status = "PASS" if not blocker_reasons else "FAIL"
    go_no_go = "GO" if status == "PASS" else "NO-GO"
    blockers_payload = [
        {"gate": "m4_backend_release_candidate", "severity": "critical", "reason": reason}
        for reason in blocker_reasons
    ]

    payload = {
        "report_schema_version": 1,
        "report_name": "m4_backend_release_candidate",
        "generated_by": "gate_validator",
        "timestamp": timestamp,
        "gate": "m4_backend_release_candidate",
        "status": status,
        "result": status,
        "decision": {
            "go_no_go": go_no_go,
            "m4_backend_release_candidate": go_no_go,
        },
        "environment": "local",
        "report_type": "release_candidate",
        "rules": {
            "all_split_reports_pass": True,
            "split_collected_must_be_gt_zero": True,
            "split_failed_errors_skipped_must_be_zero": True,
            "m4_truth_report_must_pass": True,
            "report_truth_preflight_must_pass": True,
            "documentation_lint_must_have_no_m4_blocking_errors": True,
        },
        "inputs": [f"reports/current/{name}" for name in [*SPLIT_REPORTS, AGGREGATE_REPORT, PREFLIGHT_REPORT, DOC_LINT_REPORT]],
        "components": components,
        "collected": collected,
        "passed": collected if status == "PASS" else 0,
        "failed": 0 if status == "PASS" else len(blocker_reasons),
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if status == "PASS" else 1,
        "blockers": blockers_payload,
        "source_command": "python scripts/generate_m4_backend_release_candidate.py",
    }
    commit = _commit_hash()
    if commit:
        payload["commit_hash"] = commit
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# M4 Backend Release Candidate",
        "",
        f"Status: `{payload['status']}`",
        f"Entscheidung: `{payload['decision']['go_no_go']}`",
        f"Zeitpunkt: `{payload['timestamp']}`",
        "",
        "## Inputs",
        "",
    ]
    lines.extend(f"- `{item}`" for item in payload["inputs"])
    lines.extend([
        "",
        "## Komponenten",
        "",
        "| Report | Status | Collected | Failed | Errors | Skipped |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for component in payload["components"]:
        lines.append(
            f"| `{component['name']}` | `{component['status']}` | "
            f"{component.get('collected', '-')} | {component.get('failed', '-')} | "
            f"{component.get('errors', '-')} | {component.get('skipped', '-')} |"
        )
    lines.extend(["", "## Blocker", ""])
    if payload["blockers"]:
        lines.extend(f"- {blocker['reason']}" for blocker in payload["blockers"])
    else:
        lines.append("- keine")
    lines.append("")
    return "\n".join(lines)


def write_outputs(report_dir: Path = CURRENT_DIR) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)
    preflight = build_report_truth_preflight(report_dir)
    (report_dir / PREFLIGHT_REPORT).write_text(json.dumps(preflight, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    payload = build_release_candidate(report_dir)
    (report_dir / OUTPUT_JSON.name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (report_dir / OUTPUT_MD.name).write_text(render_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    payload = write_outputs()
    print(f"M4 Backend Release Candidate = {payload['decision']['go_no_go']}")
    print(f"Wrote: {OUTPUT_JSON}")
    print(f"Wrote: {OUTPUT_MD}")
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
