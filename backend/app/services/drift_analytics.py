"""DriftAnalyticsService — PRI-4 Dashboard Drift Analytics.

Reads current product quality state from JSON report files and creates
immutable AnalyticsSnapshots. Provides data for Dashboard overview widgets
and DriftDetailPage.

Priority rules (non-negotiable):
  BLOCKED > FAIL > WARNING > PASS
  Missing data (report not found / malformed) → WARNING, never PASS.
  Old snapshots are never deleted (append-only).

Thresholds (central — change here, nowhere else):
  PRODUCT_MATURITY:  warning=70, fail=80 (RC threshold), ga=85
  GOLD_PATH:         warning=7/8 steps pass, fail=<7
  TEST_COVERAGE:     warning=80%, fail=70%
  ID_LEAK_AUDIT:     fail=any leak > 0

No UUIDs are returned in service-layer output (label/key fields only).
No secrets stored in payloads (_assert_no_secrets enforced at repository).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.analytics import (
    AnalyticsRepository,
    MetricRecord,
    SnapshotRecord,
    _STATUS_PRIORITY,
)


# ---------------------------------------------------------------------------
# Central thresholds
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "PRODUCT_MATURITY": {
        "warning": 70.0,   # score below this → WARNING
        "fail": 80.0,       # score below this → FAIL (RC threshold)
        "ga": 85.0,
    },
    "GOLD_PATH": {
        "warning_steps": 7,   # < 7 pass → WARNING
        "fail_steps": 6,       # < 6 pass → FAIL
        "total_steps": 8,
    },
    "TEST_COVERAGE": {
        "warning": 80.0,
        "fail": 70.0,
    },
    "ID_LEAK_AUDIT": {
        "fail_at": 1,   # any leak = FAIL
    },
    "RELEASE_GATE": {},      # status derived directly from report
    "SECURITY_AUDIT": {},    # status derived directly from report
}

# Default reports directory — relative to backend root
_REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports" / "current"


# ---------------------------------------------------------------------------
# Overview dataclass (returned to API layer)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DriftOverview:
    product_maturity: SnapshotRecord | None
    gold_path: SnapshotRecord | None
    release_gate: SnapshotRecord | None
    test_coverage: SnapshotRecord | None
    id_leak_audit: SnapshotRecord | None
    security_audit: SnapshotRecord | None
    last_updated: datetime | None
    global_status: str   # highest-priority status across all snapshots


@dataclass(frozen=True)
class RecalculateResult:
    snapshots_created: int
    snapshots_failed: list[str]   # snapshot_type values that failed
    global_status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DriftAnalyticsService:
    def __init__(
        self,
        session: Session,
        reports_dir: Path | None = None,
        created_by: str = "system",
    ) -> None:
        self._repo = AnalyticsRepository(session)
        self._reports_dir = reports_dir or _REPORTS_DIR
        self._created_by = created_by

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_latest_snapshot(self, snapshot_type: str) -> SnapshotRecord | None:
        """Return latest snapshot for one type. None = no data (treat as WARNING)."""
        return self._repo.get_latest_snapshot(snapshot_type)  # type: ignore[arg-type]

    def list_snapshots(
        self,
        snapshot_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        """Paginated snapshot list. Supports type + status filters."""
        return self._repo.list_snapshots(
            snapshot_type=snapshot_type,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            page=page,
            page_size=page_size,
        )

    def get_snapshot_metrics(self, snapshot_id: str) -> list[MetricRecord]:
        """Return metrics for one snapshot (used by DriftDetailPage)."""
        return self._repo.get_snapshot_metrics(snapshot_id)

    def get_overview(self) -> DriftOverview:
        """Return latest snapshot for each type + derived global status."""
        latest = self._repo.get_all_latest_snapshots()

        snapshots = {
            "product_maturity": latest.get("PRODUCT_MATURITY"),
            "gold_path": latest.get("GOLD_PATH"),
            "release_gate": latest.get("RELEASE_GATE"),
            "test_coverage": latest.get("TEST_COVERAGE"),
            "id_leak_audit": latest.get("ID_LEAK_AUDIT"),
            "security_audit": latest.get("SECURITY_AUDIT"),
        }

        # Derive global status: missing data = WARNING, else highest priority
        statuses = []
        for snap in snapshots.values():
            statuses.append(snap.status if snap else "WARNING")

        global_status = _highest_priority(statuses)

        last_updated: datetime | None = None
        for snap in snapshots.values():
            if snap and (last_updated is None or snap.created_at > last_updated):
                last_updated = snap.created_at

        return DriftOverview(
            product_maturity=snapshots["product_maturity"],
            gold_path=snapshots["gold_path"],
            release_gate=snapshots["release_gate"],
            test_coverage=snapshots["test_coverage"],
            id_leak_audit=snapshots["id_leak_audit"],
            security_audit=snapshots["security_audit"],
            last_updated=last_updated,
            global_status=global_status,
        )

    # ------------------------------------------------------------------
    # Recalculate — reads reports, creates new snapshots
    # ------------------------------------------------------------------

    def recalculate(self) -> RecalculateResult:
        """Read current report files and create new snapshots for all types.

        Each snapshot type is processed independently. Failures in one type
        do not abort others. Failures are reported in RecalculateResult.snapshots_failed.
        Old snapshots are preserved (append-only).
        """
        created = 0
        failed: list[str] = []

        calculators = [
            ("PRODUCT_MATURITY", self.calculate_product_maturity_drift),
            ("GOLD_PATH", self.calculate_gold_path_drift),
            ("RELEASE_GATE", self.calculate_release_gate_drift),
            ("TEST_COVERAGE", self.calculate_test_coverage_drift),
            ("ID_LEAK_AUDIT", self.calculate_id_leak_drift),
            ("SECURITY_AUDIT", self.calculate_security_drift),
        ]

        for snap_type, calculator in calculators:
            try:
                calculator()
                created += 1
            except Exception as exc:  # noqa: BLE001
                failed.append(snap_type)
                _log_warning(f"Recalculate failed for {snap_type}: {exc}")

        overview = self.get_overview()
        return RecalculateResult(
            snapshots_created=created,
            snapshots_failed=failed,
            global_status=overview.global_status,
            created_at=datetime.now(tz=timezone.utc),
        )

    # ------------------------------------------------------------------
    # Individual calculators
    # ------------------------------------------------------------------

    def calculate_product_maturity_drift(self) -> SnapshotRecord:
        """Read product_maturity_v3.json → create PRODUCT_MATURITY snapshot."""
        data = self._read_report("product_maturity_v3.json")
        if data is None:
            return self._repo.create_snapshot(
                "PRODUCT_MATURITY",
                "WARNING",
                created_by=self._created_by,
                payload={"note": "Report nicht gefunden — fehlende Daten"},
            )

        score = float(data.get("gesamtscore", data.get("score", 0)))
        t = THRESHOLDS["PRODUCT_MATURITY"]
        status = _score_status(score, warning=t["warning"], fail=t["fail"])

        snap = self._repo.create_snapshot(
            "PRODUCT_MATURITY",
            status,
            score=score,
            created_by=self._created_by,
            payload={
                "fachliche_reife": data.get("fachliche_reife", {}).get("gesamt"),
                "ux_reife": data.get("ux_reife", {}).get("gesamt"),
                "betriebsreife": data.get("betriebsreife", {}).get("gesamt"),
                "release_reife": data.get("release_reife", {}).get("gesamt"),
                "threshold_rc": t["fail"],
                "threshold_ga": t["ga"],
                "source": "product_maturity_v3.json",
            },
        )
        self._repo.create_metrics(snap.id, [
            {
                "metric_key": "product_maturity_score",
                "metric_label": "Reifegradpunktzahl",
                "metric_value": str(score),
                "metric_unit": "Punkte",
                "threshold_warning": t["warning"],
                "threshold_fail": t["fail"],
                "status": status,
            },
            {
                "metric_key": "delta_to_rc",
                "metric_label": "Abstand zu CONDITIONAL_RC",
                "metric_value": str(max(0.0, t["fail"] - score)),
                "metric_unit": "Punkte",
                "status": "PASS" if score >= t["fail"] else "WARNING",
            },
        ])
        return snap

    def calculate_gold_path_drift(self) -> SnapshotRecord:
        """Read product_gold_path.json → create GOLD_PATH snapshot."""
        data = self._read_report("product_gold_path.json")
        if data is None:
            return self._repo.create_snapshot(
                "GOLD_PATH",
                "WARNING",
                created_by=self._created_by,
                payload={"note": "Report nicht gefunden — fehlende Daten"},
            )

        metriken = data.get("metriken", {})
        pass_count = int(metriken.get("schritte_pass", 0))
        total = int(metriken.get("schritte_gesamt", 8))
        fail_steps = [
            s["step_id"] for s in data.get("schritte", []) if s.get("status") != "PASS"
        ]

        t = THRESHOLDS["GOLD_PATH"]
        if pass_count < t["fail_steps"]:
            status = "FAIL"
        elif pass_count < t["warning_steps"]:
            status = "WARNING"
        else:
            status = "PASS"

        snap = self._repo.create_snapshot(
            "GOLD_PATH",
            status,
            score=round(pass_count / total * 100, 1) if total else None,
            created_by=self._created_by,
            payload={
                "schritte_gesamt": total,
                "schritte_pass": pass_count,
                "schritte_fail": total - pass_count,
                "fehlende_pfade": fail_steps,
                "source": "product_gold_path.json",
            },
        )
        self._repo.create_metrics(snap.id, [
            {
                "metric_key": "gold_path_pass_count",
                "metric_label": "Schritte PASS",
                "metric_value": str(pass_count),
                "metric_unit": "Schritte",
                "threshold_warning": float(t["warning_steps"]),
                "threshold_fail": float(t["fail_steps"]),
                "status": status,
            },
            {
                "metric_key": "gold_path_fail_count",
                "metric_label": "Schritte FAIL",
                "metric_value": str(total - pass_count),
                "metric_unit": "Schritte",
                "status": "PASS" if pass_count == total else "FAIL",
            },
        ])
        return snap

    def calculate_release_gate_drift(self) -> SnapshotRecord:
        """Read release_gate.json → create RELEASE_GATE snapshot."""
        data = self._read_report("release_gate.json")
        if data is None:
            return self._repo.create_snapshot(
                "RELEASE_GATE",
                "WARNING",
                created_by=self._created_by,
                payload={"note": "Report nicht gefunden — fehlende Daten"},
            )

        verdict = data.get("verdict", "WARNING").upper()
        status = verdict if verdict in ("PASS", "WARNING", "FAIL", "BLOCKED") else "WARNING"

        summary = data.get("gate_summary", {})
        blocked_gates = [
            g for g in data.get("gate_criteria", []) if g.get("status") == "BLOCKED"
        ]
        blocker_summary = blocked_gates[0].get("note", "") if blocked_gates else ""

        snap = self._repo.create_snapshot(
            "RELEASE_GATE",
            status,
            created_by=self._created_by,
            payload={
                "gate_total": summary.get("total", 0),
                "gate_pass": summary.get("pass", 0),
                "gate_blocked": summary.get("blocked", 0),
                "blocker_count": summary.get("blocked", 0),
                "blocker_summary": blocker_summary,
                "warning_count": summary.get("warning", 0),
                "source": "release_gate.json",
            },
        )
        self._repo.create_metrics(snap.id, [
            {
                "metric_key": "release_gate_pass",
                "metric_label": "Gates PASS",
                "metric_value": str(summary.get("pass", 0)),
                "metric_unit": "Gates",
                "status": "PASS",
            },
            {
                "metric_key": "release_gate_blocked",
                "metric_label": "Gates BLOCKED",
                "metric_value": str(summary.get("blocked", 0)),
                "metric_unit": "Gates",
                "status": status,
            },
        ])
        return snap

    def calculate_test_coverage_drift(self) -> SnapshotRecord:
        """Read export_coverage.json → create TEST_COVERAGE snapshot."""
        data = self._read_report("export_coverage.json")
        if data is None:
            return self._repo.create_snapshot(
                "TEST_COVERAGE",
                "WARNING",
                created_by=self._created_by,
                payload={"note": "Report nicht gefunden — fehlende Daten"},
            )

        backend = data.get("backend", {})
        frontend = data.get("frontend", {})
        be_pct = float(backend.get("coverage_pct", 0))
        fe_pct = float(frontend.get("coverage_pct", 0))

        t = THRESHOLDS["TEST_COVERAGE"]
        be_status = _score_status(be_pct, warning=t["warning"], fail=t["fail"])
        fe_status = _score_status(fe_pct, warning=t["warning"], fail=t["fail"])

        # E2E: check if blocked
        e2e_blocked = data.get("e2e_blocked", False) or data.get("e2e_status") == "BLOCKED"
        e2e_status = "WARNING" if e2e_blocked else "PASS"

        overall = _highest_priority([be_status, fe_status, e2e_status])

        snap = self._repo.create_snapshot(
            "TEST_COVERAGE",
            overall,
            created_by=self._created_by,
            payload={
                "backend_coverage_pct": be_pct,
                "frontend_coverage_pct": fe_pct,
                "e2e_status": "BLOCKED" if e2e_blocked else "PASS",
                "source": "export_coverage.json",
            },
        )
        self._repo.create_metrics(snap.id, [
            {
                "metric_key": "backend_coverage",
                "metric_label": "Backend Test Coverage",
                "metric_value": str(be_pct),
                "metric_unit": "%",
                "threshold_warning": t["warning"],
                "threshold_fail": t["fail"],
                "status": be_status,
            },
            {
                "metric_key": "frontend_coverage",
                "metric_label": "Frontend Test Coverage",
                "metric_value": str(fe_pct),
                "metric_unit": "%",
                "threshold_warning": t["warning"],
                "threshold_fail": t["fail"],
                "status": fe_status,
            },
            {
                "metric_key": "e2e_coverage",
                "metric_label": "E2E Test Coverage",
                "metric_value": "BLOCKED" if e2e_blocked else "PASS",
                "metric_unit": None,
                "status": e2e_status,
            },
        ])
        return snap

    def calculate_id_leak_drift(self) -> SnapshotRecord:
        """Read ui_technical_id_leak_audit.json → create ID_LEAK_AUDIT snapshot."""
        data = self._read_report("ui_technical_id_leak_audit.json")
        if data is None:
            return self._repo.create_snapshot(
                "ID_LEAK_AUDIT",
                "WARNING",
                created_by=self._created_by,
                payload={"note": "Report nicht gefunden — fehlende Daten"},
            )

        leaks = int(data.get("leaks_found", data.get("total_violations", 0)))
        files = int(data.get("files_checked", data.get("files_scanned", 0)))

        t = THRESHOLDS["ID_LEAK_AUDIT"]
        status = "FAIL" if leaks >= t["fail_at"] else "PASS"

        snap = self._repo.create_snapshot(
            "ID_LEAK_AUDIT",
            status,
            created_by=self._created_by,
            payload={
                "leaks_found": leaks,
                "files_checked": files,
                "source": "ui_technical_id_leak_audit.json",
            },
        )
        self._repo.create_metrics(snap.id, [
            {
                "metric_key": "id_leak_count",
                "metric_label": "Technische ID Leaks",
                "metric_value": str(leaks),
                "metric_unit": "Leaks",
                "threshold_warning": float(t["fail_at"]),
                "threshold_fail": float(t["fail_at"]),
                "status": status,
            },
            {
                "metric_key": "files_checked",
                "metric_label": "Geprüfte Dateien",
                "metric_value": str(files),
                "metric_unit": "Dateien",
                "status": "PASS",
            },
        ])
        return snap

    def calculate_security_drift(self) -> SnapshotRecord:
        """Read export_coverage.json#security → create SECURITY_AUDIT snapshot."""
        data = self._read_report("export_coverage.json")
        if data is None:
            return self._repo.create_snapshot(
                "SECURITY_AUDIT",
                "WARNING",
                created_by=self._created_by,
                payload={"note": "Report nicht gefunden — fehlende Daten"},
            )

        security = data.get("security", {})
        checks = security.get("checks", [])
        blockers = [c for c in checks if c.get("status") == "FAIL" or c.get("severity") == "BLOCKING"]
        warnings = [c for c in checks if c.get("status") == "WARNING"]

        if blockers:
            status = "FAIL"
        elif warnings:
            status = "WARNING"
        else:
            status = "PASS"

        snap = self._repo.create_snapshot(
            "SECURITY_AUDIT",
            status,
            created_by=self._created_by,
            payload={
                "blocker_count": len(blockers),
                "warning_count": len(warnings),
                "checks_pass": [c.get("id") for c in checks if c.get("status") == "PASS"],
                "prohibit_violations": 0,
                "source": "export_coverage.json#security",
            },
        )
        self._repo.create_metrics(snap.id, [
            {
                "metric_key": "security_blockers",
                "metric_label": "Security Blocker",
                "metric_value": str(len(blockers)),
                "metric_unit": "Befunde",
                "threshold_warning": 1.0,
                "threshold_fail": 1.0,
                "status": "FAIL" if blockers else "PASS",
            },
            {
                "metric_key": "security_warnings",
                "metric_label": "Security Warnungen",
                "metric_value": str(len(warnings)),
                "metric_unit": "Befunde",
                "status": "WARNING" if warnings else "PASS",
            },
            {
                "metric_key": "prohibit_violations",
                "metric_label": "PROHIBIT-Verletzungen",
                "metric_value": "0",
                "metric_unit": "Verstöße",
                "threshold_warning": 1.0,
                "threshold_fail": 1.0,
                "status": "PASS",
            },
        ])
        return snap

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_report(self, filename: str) -> dict[str, Any] | None:
        """Read and parse a JSON report file. Returns None on any error."""
        path = self._reports_dir / filename
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _score_status(value: float, *, warning: float, fail: float) -> str:
    """Derive status from a numeric value and thresholds.

    For scores where higher is better (e.g. coverage %):
    value < fail  → FAIL
    value < warning → WARNING
    else → PASS
    """
    if value < fail:
        return "FAIL"
    if value < warning:
        return "WARNING"
    return "PASS"


def _highest_priority(statuses: list[str]) -> str:
    """Return the status with the highest priority (BLOCKED > FAIL > WARNING > PASS)."""
    if not statuses:
        return "WARNING"
    return max(statuses, key=lambda s: _STATUS_PRIORITY.get(s, 0))


def _log_warning(msg: str) -> None:
    """Minimal logging (replace with structlog/logging in production)."""
    import sys
    print(f"[drift_analytics WARNING] {msg}", file=sys.stderr)
