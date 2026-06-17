"""Seed analytics_snapshots and analytics_metrics with test data.

Reflects the current product state after PRI-3 (Export Center abgeschlossen):
- PRODUCT_MATURITY: score=76, FAIL (< 80 RC-Threshold)
- GOLD_PATH: 8/8 PASS
- RELEASE_GATE: BLOCKED (TEST_DATABASE_URL)
- TEST_COVERAGE: WARNING (TEST_DATABASE_URL blockiert E2E-Suite)
- ID_LEAK_AUDIT: PASS (0 Leaks)
- SECURITY_AUDIT: PASS (keine Blocker)

Run: python -m backend.scripts.seed_analytics
or:  PYTHONPATH=. python backend/scripts/seed_analytics.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.repositories.analytics import AnalyticsRepository


def main() -> None:
    session = SessionLocal()
    repo = AnalyticsRepository(session)
    now = datetime.now(tz=timezone.utc)

    try:
        # 1. PRODUCT_MATURITY — score=76, FAIL (RC requires 80)
        snap_pm = repo.create_snapshot(
            snapshot_type="PRODUCT_MATURITY",
            status="FAIL",
            score=76.0,
            created_by="system",
            payload={
                "fachliche_reife": 74,
                "ux_reife": 74,
                "betriebsreife": 92,
                "release_reife": 72,
                "threshold_rc": 80,
                "threshold_ga": 85,
                "source": "product_maturity_v3.json",
            },
        )
        repo.create_metrics(
            snap_pm.id,
            [
                {
                    "metric_key": "product_maturity_score",
                    "metric_label": "Reifegradpunktzahl",
                    "metric_value": "76",
                    "metric_unit": "Punkte",
                    "threshold_warning": 70.0,
                    "threshold_fail": 80.0,
                    "status": "FAIL",
                },
                {
                    "metric_key": "threshold_rc",
                    "metric_label": "Zielwert CONDITIONAL_RC",
                    "metric_value": "80",
                    "metric_unit": "Punkte",
                    "status": "PASS",
                },
                {
                    "metric_key": "threshold_ga",
                    "metric_label": "Zielwert GA",
                    "metric_value": "85",
                    "metric_unit": "Punkte",
                    "status": "PASS",
                },
                {
                    "metric_key": "delta_to_rc",
                    "metric_label": "Abstand zu CONDITIONAL_RC",
                    "metric_value": "4",
                    "metric_unit": "Punkte",
                    "status": "WARNING",
                },
            ],
        )
        print(f"  PRODUCT_MATURITY snapshot created (score=76, FAIL)")

        # 2. GOLD_PATH — 8/8 PASS
        snap_gp = repo.create_snapshot(
            snapshot_type="GOLD_PATH",
            status="PASS",
            score=100.0,
            created_by="system",
            payload={
                "schritte_gesamt": 8,
                "schritte_pass": 8,
                "schritte_fail": 0,
                "fehlende_pfade": [],
                "source": "product_gold_path.json",
            },
        )
        repo.create_metrics(
            snap_gp.id,
            [
                {
                    "metric_key": "gold_path_pass_count",
                    "metric_label": "Gold Path Schritte PASS",
                    "metric_value": "8",
                    "metric_unit": "Schritte",
                    "threshold_warning": 7.0,
                    "threshold_fail": 6.0,
                    "status": "PASS",
                },
                {
                    "metric_key": "gold_path_total",
                    "metric_label": "Gold Path Schritte gesamt",
                    "metric_value": "8",
                    "metric_unit": "Schritte",
                    "status": "PASS",
                },
                {
                    "metric_key": "gold_path_fail_count",
                    "metric_label": "Gold Path Schritte FAIL",
                    "metric_value": "0",
                    "metric_unit": "Schritte",
                    "status": "PASS",
                },
            ],
        )
        print(f"  GOLD_PATH snapshot created (8/8 PASS)")

        # 3. RELEASE_GATE — BLOCKED (TEST_DATABASE_URL)
        snap_rg = repo.create_snapshot(
            snapshot_type="RELEASE_GATE",
            status="BLOCKED",
            score=None,
            created_by="system",
            payload={
                "gate_total": 7,
                "gate_pass": 6,
                "gate_blocked": 1,
                "blocker_count": 1,
                "blocker_summary": "RG-06: TEST_DATABASE_URL fehlt, M5a nicht READY_FOR_M5B",
                "warning_count": 0,
                "source": "release_gate.json",
            },
        )
        repo.create_metrics(
            snap_rg.id,
            [
                {
                    "metric_key": "release_gate_pass",
                    "metric_label": "Gates PASS",
                    "metric_value": "6",
                    "metric_unit": "Gates",
                    "status": "PASS",
                },
                {
                    "metric_key": "release_gate_blocked",
                    "metric_label": "Gates BLOCKED",
                    "metric_value": "1",
                    "metric_unit": "Gates",
                    "status": "BLOCKED",
                },
                {
                    "metric_key": "release_gate_blocker",
                    "metric_label": "Haupt-Blocker",
                    "metric_value": "TEST_DATABASE_URL fehlt (M5a-Kaskade)",
                    "metric_unit": None,
                    "status": "BLOCKED",
                },
            ],
        )
        print(f"  RELEASE_GATE snapshot created (BLOCKED)")

        # 4. TEST_COVERAGE — WARNING (E2E blockiert)
        snap_tc = repo.create_snapshot(
            snapshot_type="TEST_COVERAGE",
            status="WARNING",
            score=None,
            created_by="system",
            payload={
                "backend_coverage_pct": 94,
                "frontend_coverage_pct": 91,
                "e2e_status": "BLOCKED",
                "e2e_blocker": "TEST_DATABASE_URL",
                "source": "export_coverage.json",
            },
        )
        repo.create_metrics(
            snap_tc.id,
            [
                {
                    "metric_key": "backend_coverage",
                    "metric_label": "Backend Test Coverage",
                    "metric_value": "94",
                    "metric_unit": "%",
                    "threshold_warning": 80.0,
                    "threshold_fail": 70.0,
                    "status": "PASS",
                },
                {
                    "metric_key": "frontend_coverage",
                    "metric_label": "Frontend Test Coverage",
                    "metric_value": "91",
                    "metric_unit": "%",
                    "threshold_warning": 80.0,
                    "threshold_fail": 70.0,
                    "status": "PASS",
                },
                {
                    "metric_key": "e2e_coverage",
                    "metric_label": "E2E Test Coverage",
                    "metric_value": "BLOCKED",
                    "metric_unit": None,
                    "status": "WARNING",
                },
            ],
        )
        print(f"  TEST_COVERAGE snapshot created (WARNING — E2E blockiert)")

        # 5. ID_LEAK_AUDIT — 0 Leaks, PASS
        snap_il = repo.create_snapshot(
            snapshot_type="ID_LEAK_AUDIT",
            status="PASS",
            score=None,
            created_by="system",
            payload={
                "leaks_found": 0,
                "files_checked": 57,
                "source": "ui_technical_id_leak_audit.json",
            },
        )
        repo.create_metrics(
            snap_il.id,
            [
                {
                    "metric_key": "id_leak_count",
                    "metric_label": "Technische ID Leaks",
                    "metric_value": "0",
                    "metric_unit": "Leaks",
                    "threshold_warning": 1.0,
                    "threshold_fail": 1.0,
                    "status": "PASS",
                },
                {
                    "metric_key": "files_checked",
                    "metric_label": "Geprüfte Dateien",
                    "metric_value": "57",
                    "metric_unit": "Dateien",
                    "status": "PASS",
                },
            ],
        )
        print(f"  ID_LEAK_AUDIT snapshot created (0 Leaks, PASS)")

        # 6. SECURITY_AUDIT — PASS (keine Blocker)
        snap_sa = repo.create_snapshot(
            snapshot_type="SECURITY_AUDIT",
            status="PASS",
            score=None,
            created_by="system",
            payload={
                "blocker_count": 0,
                "warning_count": 0,
                "checks_pass": ["SEC-EXP-01", "SEC-EXP-02", "SEC-EXP-03", "SEC-EXP-04", "SEC-EXP-05"],
                "prohibit_violations": 0,
                "source": "export_coverage.json#security",
            },
        )
        repo.create_metrics(
            snap_sa.id,
            [
                {
                    "metric_key": "security_blockers",
                    "metric_label": "Security Blocker",
                    "metric_value": "0",
                    "metric_unit": "Befunde",
                    "threshold_warning": 1.0,
                    "threshold_fail": 1.0,
                    "status": "PASS",
                },
                {
                    "metric_key": "security_warnings",
                    "metric_label": "Security Warnungen",
                    "metric_value": "0",
                    "metric_unit": "Befunde",
                    "status": "PASS",
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
            ],
        )
        print(f"  SECURITY_AUDIT snapshot created (PASS)")

        session.commit()
        print("\nSeed completed. 6 snapshots committed.")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
