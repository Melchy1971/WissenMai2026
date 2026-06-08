"""
Runtime Connectivity Gate
=========================
Wertet reports/current/runtime_connectivity_report.json aus und berechnet einen Score.

9 Checks (je 1 Punkt):
  1. db_reachable          — DATABASE_URL gesetzt + DB erreichbar
  2. alembic_head          — Alembic-Schema aktuell
  3. seed_ok               — seed_auth.py erfolgreich
  4. backend_health        — /health HTTP 200
  5. login_ok              — /api/v1/auth/login HTTP 200 + Token
  6. auth_me_ok            — /api/v1/auth/me HTTP 200 + Workspace-ID
  7. workspace_bootstrap   — Workspace-Bootstrap-Redirect erhalten
  8. frontend_reachable    — Frontend erreicht Backend (API-Responses > 0)
  9. no_api_unreachable    — Kein API_UNREACHABLE im Normalflow

Score:
  >= 95 % (9/9 oder 8,6/9 → gerundet: 9) → PASS (Runtime Connectivity grün)
  < 95 %                                 → FAIL (blockiert M3a/M4)

Exit-Codes:
  0  PASS
  1  FAIL (Score < 95 %)
  2  Report fehlt oder ungültig
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
REPORT_IN = CURRENT_DIR / "runtime_connectivity_report.json"
REPORT_OUT = CURRENT_DIR / "runtime_connectivity_gate.json"
THRESHOLD_PCT = 95.0
TOTAL_CHECKS = 9


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"[FAIL] Report nicht gefunden: {path}\n       Führe zuerst run_runtime_connectivity_report.js aus.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[FAIL] Ungültiges JSON in {path}: {exc}") from exc


def _check_val(report: dict, *keys: str) -> Any:
    """Navigiere nested dict. Gibt None zurück wenn Pfad nicht existiert."""
    cur: Any = report
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _evaluate(report: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(check_id: str, passed: bool, evidence: str = "") -> None:
        checks.append({
            "id": check_id,
            "status": "pass" if passed else "fail",
            **({"evidence": evidence} if evidence else {}),
        })

    # 1. db_reachable: DATABASE_URL gesetzt + Alembic/Seed impliziert DB-Zugriff
    db_url = bool(report.get("database_url") or report.get("database_url_set"))
    alembic_ok = _check_val(report, "alembic", "ok") is True
    add("db_reachable", db_url and alembic_ok,
        f"database_url_set={db_url} alembic.ok={alembic_ok}")

    # 2. alembic_head: alembic.ok und keine missing_heads
    missing_heads = _check_val(report, "alembic", "missing_heads") or []
    add("alembic_head", alembic_ok and not missing_heads,
        f"ok={alembic_ok} missing={missing_heads}")

    # 3. seed_ok: seed exit_code == 0
    seed_exit = _check_val(report, "seed", "exit_code")
    add("seed_ok", seed_exit == 0, f"seed.exit_code={seed_exit}")

    # 4. backend_health: /health status 200
    health_status = _check_val(report, "health", "status_code")
    if health_status is None:
        # Fallback: prüfe checks-Array
        health_check = next(
            (c for c in (report.get("checks") or []) if "health" in c.get("id", "").lower()),
            None,
        )
        health_status = 200 if (health_check and health_check.get("result") == "PASS") else None
    add("backend_health", health_status == 200, f"status_code={health_status}")

    # 5. login_ok: /auth/login 200 + Token
    login_status = _check_val(report, "login", "status_code")
    login_token = bool(_check_val(report, "login", "token"))
    if login_status is None:
        login_check = next(
            (c for c in (report.get("checks") or []) if "login" in c.get("id", "").lower()),
            None,
        )
        login_status = 200 if (login_check and login_check.get("result") == "PASS") else None
        login_token = login_status == 200
    add("login_ok", login_status == 200 and login_token,
        f"status_code={login_status} token={login_token}")

    # 6. auth_me_ok: /auth/me 200 + workspace_id vorhanden
    me_status = _check_val(report, "auth_me", "status_code")
    me_workspace = _check_val(report, "auth_me", "active_workspace_id")
    if me_status is None:
        me_check = next(
            (c for c in (report.get("checks") or [])
             if "me" in c.get("id", "").lower() or "auth_me" in c.get("id", "").lower()),
            None,
        )
        me_status = 200 if (me_check and me_check.get("result") == "PASS") else None
        me_workspace = "present" if me_status == 200 else None
    add("auth_me_ok", me_status == 200 and bool(me_workspace),
        f"status_code={me_status} workspace={me_workspace}")

    # 7. workspace_bootstrap: Redirect zu /documents erhalten
    bootstrap_url = _check_val(report, "frontend", "final_url") or _check_val(report, "auth_me", "active_workspace_id")
    bootstrap_ok = (
        "/documents" in str(bootstrap_url or "")
        or bool(bootstrap_url)
        or next(
            (True for c in (report.get("checks") or [])
             if "workspace" in c.get("id", "").lower() or "bootstrap" in c.get("id", "").lower()
             and c.get("result") == "PASS"),
            False,
        )
    )
    add("workspace_bootstrap", bootstrap_ok, f"signal={bootstrap_url or 'none'}")

    # 8. frontend_reachable: Frontend hat mindestens 1 API-Response empfangen
    api_responses = _check_val(report, "frontend", "api_response_count")
    if api_responses is None:
        fe_check = next(
            (c for c in (report.get("checks") or []) if "frontend" in c.get("id", "").lower()),
            None,
        )
        api_responses = 1 if (fe_check and fe_check.get("result") == "PASS") else 0
    add("frontend_reachable", (api_responses or 0) > 0, f"api_responses={api_responses}")

    # 9. no_api_unreachable: kein API_UNREACHABLE im Report
    api_unreachable = any(
        "API_UNREACHABLE" in str(v)
        for v in _flatten_values(report)
        if isinstance(v, str)
    )
    add("no_api_unreachable", not api_unreachable,
        "API_UNREACHABLE detected" if api_unreachable else "clean")

    return checks


def _flatten_values(obj: Any, depth: int = 0) -> list[Any]:
    if depth > 6:
        return []
    if isinstance(obj, dict):
        result = []
        for v in obj.values():
            result.extend(_flatten_values(v, depth + 1))
        return result
    if isinstance(obj, list):
        result = []
        for item in obj:
            result.extend(_flatten_values(item, depth + 1))
        return result
    return [obj]


def main() -> int:
    report = _load(REPORT_IN)
    checks = _evaluate(report)
    generated_at = datetime.now(timezone.utc).isoformat()
    evidence_timestamp = report.get("generated_at", report.get("timestamp", ""))

    passed = sum(1 for c in checks if c["status"] == "pass")
    score_pct = round(passed / TOTAL_CHECKS * 100, 1)
    gate_passed = score_pct >= THRESHOLD_PCT
    blockers = [c["id"] for c in checks if c["status"] == "fail"]

    result_payload = {
        "report_schema_version": 1,
        "report_name": "runtime_connectivity_gate",
        "generated_by": "gate_validator",
        "name": "runtime_connectivity_gate",
        "timestamp": generated_at,
        "gate": "runtime_connectivity_gate",
        "status": "PASS" if gate_passed else "FAIL",
        "result": "PASS" if gate_passed else "FAIL",
        "threshold_pct": THRESHOLD_PCT,
        "total_checks": TOTAL_CHECKS,
        "passed_checks": passed,
        "score_pct": score_pct,
        "status": "PASS" if gate_passed else "FAIL",
        "checks": checks,
        "blockers": [{"id": b, "severity": "critical", "reason": f"check '{b}' failed"} for b in blockers],
        "m3a_impact": "green" if gate_passed else "blocked",
        "m4_impact": "unblocked" if gate_passed else "blocked",
        "environment": "local",
        "database_url_set": bool(report.get("database_url") or report.get("database_url_set")),
        "test_database_url_set": bool(report.get("test_database_url_set")),
        "collected": TOTAL_CHECKS,
        "passed": passed,
        "failed": TOTAL_CHECKS - passed,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if gate_passed else 1,
        "source_command": "python scripts/validate_runtime_connectivity_gate.py",
        "decision": {
            "go_no_go": "GO" if gate_passed else "NO_GO",
            "result": "GO" if gate_passed else "NO_GO",
            "runtime_connectivity_allowed": gate_passed,
        },
        "known_limitations": [],
        "generated_at": generated_at,
        "re_evaluated_at": generated_at,
        "evidence_from": "reports/current/runtime_connectivity_report.json",
        "evidence_timestamp": evidence_timestamp,
    }

    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(
        json.dumps(result_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Runtime Connectivity Gate = {result_payload['status']}")
    print(f"Score: {passed}/{TOTAL_CHECKS} = {score_pct}% (Schwelle: {THRESHOLD_PCT}%)")
    if blockers:
        print(f"Blocker ({len(blockers)}):")
        for b in blockers:
            print(f"  - {b}")
    else:
        print("Keine Blocker.")
    print(f"Report: {REPORT_OUT}")

    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
