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

Stand 2026-06-10: Alle M5b Preparation-Artefakte sind vollstaendig (27/27, PREP-01 bis PREP-27). Architecture Review COMPLETE (8/8 Artefakte, 0 Luecken). Formales `PREPARED` ist geblockt durch externe Preconditions (M5a READY_FOR_M5B fehlt, Report Integrity BLOCKED). Implementation Gate ist explizit NO-GO (`reports/current/m5b_implementation_gate.json`). Alpha Validation BLOCKED (`reports/current/m5b_alpha_validation_report.json`). Beta Start Gate BLOCKED 3/6 (`reports/current/m5b_beta_start_gate.json`). M5c NOT_STARTED.

**Drift Detection Code ist nicht vorhanden. Repair Code ist nicht vorhanden. Kein Code darf implementiert werden vor explizitem Implementation Gate GO. Cleanup-Aktionen und Repair-Aktionen sind dauerhaft verboten (PROHIBIT-02, PROHIBIT-06).**

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

## Laufende technische Arbeit

- Data-Quality-Runner, Detectoren, Read-only API und Dashboard bleiben read-only.
- Cleanup-, Merge- oder Repair-Actions brauchen separate Governance.
- Lifecycle-Aenderungen durch Data-Quality-Prozesse bleiben ausser Scope.

## Relevante Tests

- Metadata Slice: `backend/tests/test_metadata_quality_detector.py`, `backend/tests/postgres_truth/test_m5a_metadata_quality_truth.py`
- Lifecycle Slice: `backend/tests/test_lifecycle_integrity_detector.py`, `backend/tests/postgres_truth/test_m5a_lifecycle_integrity_truth.py`
- Gate-Hierarchie: `tests/test_m5a_gate_hierarchy.py`, `backend/tests/test_parent_gate_validator.py`

Testergebnisse und Freigaben werden nur aus aktuellen Reports unter `reports/current/` abgeleitet.
