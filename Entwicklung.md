# Entwicklung

Statusquelle: `reports/current/masterplan_status.json`, `docs/gate_hierarchy.json`, `reports/current/m5a_final_readiness_review.json`, `reports/current/m5b_release_decision.json`

Aktuelle Freigaben werden nicht manuell gepflegt. Der generierte Maschinenstatus in `reports/current/masterplan_status.json` ist autoritativ.

## Gate-Hierarchie nach Fix

- M5a ist nur dann Gesamt-`PASS`, wenn `reports/current/m5a_final_readiness_review.json` `READY_FOR_M5B` meldet.
- Ein M5a Slice-Gate bewertet nur den jeweiligen Slice. Slice-`PASS` ist keine M5a-Gesamtfreigabe.
- `reports/current/m5a_data_quality_gate.json` bleibt ein erforderlicher Eingang fuer M5a Final Readiness, ersetzt aber nicht `reports/current/m5a_final_readiness_review.json`.
- `reports/current/m5b_release_decision.json` trennt `DRAFT`, `PREPARED` und `GO`: `PREPARED` erlaubt Vorbereitung, `GO` erlaubt Implementierung.
- Es gibt keine globale Prozent- oder Vollstaendigkeitsfreigabe ausserhalb maschinenlesbarer Reports.

## M5a Slice-Arbeit

Vorhandene Slice-Artefakte:

- Duplicate Detector: `reports/current/m5a_duplicate_detector_gate.json`
- Metadata Detector: `reports/current/m5a_metadata_detector_gate.json`
- Lifecycle Integrity Detector: `reports/current/m5a_lifecycle_integrity_gate.json`

Diese Reports koennen Slice-Fortschritt belegen. Sie ersetzen nicht `reports/current/m5a_final_readiness_review.json` und nicht die Parent-Gate-Validierung aus `docs/gate_hierarchy.json`.

## M5b Planung

M5b Drift Architecture ist ein Planungsartefakt: `docs/m5b-drift-architecture.md`.

Planung als `DRAFT` ist erlaubt. `PREPARED` erlaubt nur Vorbereitung; Implementierung bleibt untersagt, solange `reports/current/m5b_release_decision.json` kein `GO` meldet.

Stand 2026-06-12: M5b-Implementierung vollstaendig. Alpha Gate PASS (Score 100/100, 6 Detektoren, 106/106 Tests). CLI, Dashboard (23/23 Frontend-Tests), REST-API (read-only), Observability (21/21 Tests), Performance Baseline (sub-linear, 100→10k Dokumente) implementiert. M5b-Gates BLOCKED durch Kaskade: Alpha Hardening Gate BLOCKED (AHG-BLOCKER-01: M5a nicht READY_FOR_M5B; AHG-BLOCKER-02: drift_report_integrity PARTIAL) → Beta BLOCKED → Production Readiness BLOCKED. Quelle: `reports/current/m5b_alpha_hardening_gate.json`, `reports/current/m5b_production_readiness_gate.json`.

M5c Preparation PREPARED (16/16 Checks, `reports/current/m5c_preparation_gate.json`). Domain Model, Risk Scoring, Detection Rules, Dry Run Governance, Report Schema, Audit Trail, Dashboard Scope, Implementation Boundary definiert. M5c GO bleibt gesperrt: `reports/current/m5c_start_gate.json` BLOCKED (alle 5 Release-Conditions unerfuellt). M5c Cleanup-Implementierung: NO_GO.

**Cleanup-Aktionen und Repair-Aktionen sind dauerhaft verboten (PROHIBIT-02, PROHIBIT-06). Invariante: Drift Detection darf nur erkennen, nie korrigieren.**

Preparation-Artefakte (vollstaendig, PREP-01 bis PREP-27):
- `docs/m5b-preparation-boundary.md`, `m5b_boundary_report.json`
- `docs/m5b-drift-types.md`, `schemas/drift_types.schema.json`
- `reports/current/m5b_gate_criteria.json`, `docs/m5b-gates.md`
- `docs/m5b-test-strategy.md`, `test_matrix_m5b.json`
- `docs/m5b-risk-matrix.md`, `m5b_risk_matrix.json`
- `docs/m5b-drift-governance.md`, `drift_governance.schema.json`
- `docs/m5b-drift-severity.md`, `drift_severity_matrix.json`
- `docs/m5b-entity-mapping.md`, `drift_entity_mapping.json`
- `docs/m5b-drift-metrics.md`, `drift_metrics.schema.json`
- `docs/m5b-drift-history.md`, `drift_history_model.json`
- `docs/m5b-reporting.md`, `reporting_architecture.json`
- `docs/m5b-testdata-strategy.md`, `drift_test_dataset_plan.json`
- `docs/m5b-rollback.md`, `rollback_strategy.json`
- `reports/current/m5b_architecture_review.json`

Scope- und Boundary-Artefakte (Planungsphase Alpha/Beta):
- `docs/m5b-drift-dashboard-scope.md`, `dashboard_testids.md`
- `docs/m5b-drift-api-scope.md`, `openapi_drift_scope.json`
- `docs/m5b-beta-boundary.md`

Bekannte Risiken: `docs/m5b-risk-matrix.md` (7 Risiken, davon 5 blocking, 2 mit critical impact).

Drift Finding Governance: `docs/m5b-drift-governance.md`, `drift_governance.schema.json`. Invariante: Drift Detection darf nur erkennen, nie korrigieren. Alle 8 PROHIBIT-Regeln sind im Schema maschinenlesbar hinterlegt.

Architecture Review: `reports/current/m5b_architecture_review.json`. Score: 8/8 Artefakte vollstaendig, 0 strukturelle Luecken, 3 offene Entscheidungen (OD-01..OD-03 loesen sich bei Implementation), 2 blockierende Risiken (CCR-02 KL-GOV-001, CCR-03 externe Preconditions).

Alpha/Beta-Gates: Alpha BLOCKED (keine Implementierung vorhanden; erwartet bei Implementation Gate NO-GO). Beta BLOCKED (3/6 Kriterien; BSG-04 API Scope, BSG-05 Dashboard Scope, BSG-06 Documentation Truth bereits PASS). M5c setzt Beta PASS voraus.

## GUI Cleanup (ABGESCHLOSSEN, 2026-06-12)

GUI bereinigt auf freigegebene Masterplan-Bereiche. Nachweis: `reports/current/gui_truth_report.json` PASS (12/12).

Entfernte Routen (8): /tools, /memory, /tasks, /projects, /agents, /collaboration, /governance, /admin/diagnostics. Keine Feature Flags, keine Hidden Menüs, keine Disabled-State-Routen.

Aktive Routen (6 + Auth): /dashboard, /chat (Suche), /documents, /rag (Datenanalyse), /data-quality, /settings.

Entfernte Artefakte: 8 Page-Komponenten, 1 Feature-Komponente (DriftDashboard — M5b BLOCKED), 14 Shared Components (GateStatusCard, ApprovalQueue, AuditLogTable u.a.), 8 API-Dateien.

Dashboard: Nur Systemstatus, Dokumentanzahl, Importstatus, Suchaktivität, Data Quality Score, Letzte Analysen, Wichtige Warnungen. Gate-Widgets entfernt.

Einstellungen: Nur KI Provider, Import / Sucheinstellungen, Benutzerprofil / Darstellung. Sections Voice/Security/Governance/Memory/Agents/Collaboration entfernt.

Drift Detection nicht in Navigation: Freigabe erst bei `m5b_production_readiness_gate` PASS (aktuell BLOCKED).

Inventar: `docs/gui_inventory.md`. Freigabe-Scope: `docs/final_gui_scope.md`. Navigation: `docs/final_navigation.md`. Route-Audit: `docs/gui_route_audit.md`. Komponenten-Cleanup: `docs/gui_component_cleanup.md`.

## Laufende technische Arbeit

- Data-Quality-Runner, Detectoren, Read-only API und Dashboard bleiben read-only.
- Cleanup-, Merge- oder Repair-Actions brauchen separate Governance.
- Lifecycle-Aenderungen durch Data-Quality-Prozesse bleiben ausser Scope.

## Relevante Tests

- Metadata Slice: `backend/tests/test_metadata_quality_detector.py`, `backend/tests/postgres_truth/test_m5a_metadata_quality_truth.py`
- Lifecycle Slice: `backend/tests/test_lifecycle_integrity_detector.py`, `backend/tests/postgres_truth/test_m5a_lifecycle_integrity_truth.py`
- Gate-Hierarchie: `tests/test_m5a_gate_hierarchy.py`, `backend/tests/test_parent_gate_validator.py`

Testergebnisse und Freigaben werden nur aus aktuellen Reports unter `reports/current/` abgeleitet.
