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

## Drift v2 (ABGESCHLOSSEN, 2026-06-15)

Route `/drift` → `DriftPage` → `drift_v2/DriftDashboard` aktiv. Alle Imports aus `features/drift` (alt) entfernt.

- `reports/current/drift_v2_import_audit.json` PASS (0 alte Imports)
- `reports/current/drift_v2_ui_truth_report.json` PASS (29/29 Tests, 8/8 Checks)
- `reports/current/drift_route_recovery_report.json` PASS
- Component Contract: `docs/drift_v2_component_contract.md` (3 testid-GAPs dokumentiert, nicht blockierend)

Formale Freigabe: ausstehend (m5b_production_readiness_gate BLOCKED, cascade aus M5a, root: TEST_DATABASE_URL).
**Cleanup/Repair: NO_GO** — PROHIBIT-02, PROHIBIT-06.

## Local Final Gate Validator v2 (2026-06-15)

Validator: `scripts/local_final_gate_validator_v2.py` — Dependency Graph: `local_final_gate_dependency_graph.json`
Output: `reports/current/final_gate_report.json` — verdict=**BLOCKED**

Blocker (4): report_integrity_v2, m5b_alpha_hardening_gate, m5b_production_readiness_gate, m5c_start_gate.
Warnungen (2): drift_v2_component_contract (PARTIAL_FAIL, 3 GAPs), drift_dashboard_truth_report (INVALID, truncated).
Extern (1): external_env_gate NOT_RUN (72 Tests, blockiert Gate nicht).
Non-Blocking (1): permission_blocker — ACL auf features/drift (alt), aktiver Pfad ist drift_v2, Regel 6 greift.

## Post-RC Plan (2026-06-15)

Entscheidung: `PHASE_0_RC_STABILIZATION_REQUIRED`
Quelle: `reports/current/post_rc_decision.json`, `docs/post_rc_plan.md`

Regel: Keine M5c-Implementierung vor RC-Stabilisierung und externer Testentscheidung.

Phasenreihenfolge:
1. Phase 0 (aktiv): RC-Stabilisierung -- RC-PREREQ-01 bis 03 beheben, RC Gate re-run bis RELEASE_CANDIDATE
2. Phase 1 (gesperrt): Externe Umgebungstests (72 Tests, external_env_gate)
3. Phase 2 (gesperrt): Installer / Deployment
4. Phase 3 (NO_GO): M5c Cleanup Dry-Run Planung -- erst nach m5c_start_gate PASS + PO-Sign-off
5. Parallel moeglich: OPT-5 Nutzerfeedback (S04/S08 als Basis fuer RC-PREREQ-02)

M5c-Lock: LOCKED. Unlock: RC=RELEASE_CANDIDATE + ext. Testentscheidung + m5c_start_gate PASS + PO-Sign-off.

## RC Stabilization Gate (2026-06-15)

Entscheidung: **BLOCKED** (1/6) — `reports/current/rc_stabilization_gate.json`

| Condition | Status |
|---|---|
| SCG-01: Release Blocker geschlossen | BLOCKED (RCB-001, RCB-002, RCB-003 offen) |
| SCG-02: Deployment Readiness keine BLOCKED-Checks | BLOCKED (DRC-01, DRC-03) |
| SCG-03: Backup/Restore Re-Test PASS | BLOCKED (kein Live-Backend, TEST_DATABASE_URL fehlt) |
| SCG-04: Performance Smoke PASS | BLOCKED (kein Live-Backend) |
| SCG-05: UX Polish — keine Critical-UX-Items | PARTIAL_PASS (NAV + Router-Guard offen) |
| SCG-06: Documentation Truth Lint PASS | PASS |

Naechster Schritt: Minimaler Unblocking-Pfad: RC-PREREQ-01 (TEST_DATABASE_URL) -> RC-PREREQ-02 (NAV PO-Entscheidung) -> RC-PREREQ-03 (Router-Guard) -> RC Gate re-run -> bei RELEASE_CANDIDATE: Backup/Restore + Performance im Live-System.

Regeln (unveraenderlich):
- RC bleibt BLOCKED bis RC Gate = RELEASE_CANDIDATE
- M5c Cleanup-Implementierung: NO_GO
- Externe Tests: gesperrt bis RC Gate = RELEASE_CANDIDATE

## Production Readiness Assessment (2026-06-15)

Entscheidung: **BLOCKED** — `reports/current/production_readiness_assessment.json`

| Check | Status |
|---|---|
| PRA-01 Auth & Workspace Isolation | PASS |
| PRA-02 Workspace-Scope API | PASS |
| PRA-03 Datenpruefung (Alembic 20) | PARTIAL_PASS |
| PRA-04 Backup/Restore | BLOCKED |
| PRA-05 Alembic Migrationsstand | PASS |
| PRA-06 Structured Logging | PARTIAL_PASS |
| PRA-07 Frontend Error Handling | PARTIAL_PASS |
| PRA-08 Performance | BLOCKED |
| PRA-09 Frontend Build | PARTIAL_PASS |
| PRA-10 API Readiness | PARTIAL_PASS |

Root Causes: PRA-04 (kein Live-Backend, TEST_DATABASE_URL fehlt), PRA-08 (kein Messbar ohne Live-System).
Evaluation: static_code_analysis — kein Live-Backend verfuegbar.

## Production Gate (2026-06-15)

Entscheidung: **BLOCKED** (2/5) — `reports/current/production_gate.json`

| Condition | Status |
|---|---|
| PGC-01: RC Gate = RELEASE_CANDIDATE | BLOCKED |
| PGC-02: Production Readiness PASS | PARTIAL_PASS |
| PGC-03: Incident Runbooks vollstaendig | PASS |
| PGC-04: VPS Deployment Blueprint vollstaendig | PASS |
| PGC-05: Monitoring PASS | PARTIAL_PASS |

6 Blocker (PGB-01 bis PGB-06). Naechster Schritt: RC Gate deblocken.

## Version 1.0 Entscheidung (2026-06-15)

Status: **BLOCKED** — `reports/current/version_1_0_decision.json`

| Bedingung | Status |
|---|---|
| V10-01: Production Gate PASS | FAIL |
| V10-02: 0 BLOCKING_CORE Limitations | PASS |
| V10-03: PROHIBIT-02/06/08 aktiv, M5c LOCKED | PASS |

Unblocking-Pfad: 10 Schritte — Root: RC Gate deblocken (TEST_DATABASE_URL setzen).

## Post-1.0 Roadmap (2026-06-15)

Dokumentiert in `docs/post_1_0_roadmap.md`. Voraussetzung: Version 1.0 APPROVED.

6 Phasen (sequenziell, Phase 4-6 teilweise parallelisierbar):
1. M5c Cleanup Dry Run — Mittel (2-3 W), Voraussetzung: m5c_start_gate PASS + PO-Sign-off
2. M5d Repair Governance — Hoch (4-6 W), Voraussetzung: Phase 1 stabil
3. Governance Automation — Hoch (6-8 W), Voraussetzung: Phase 2 > 30 Tage produktiv
4. Performance Optimierung — Mittel (2-4 W), Voraussetzung: Live-Metriken
5. Multi-User Ausbau — Hoch (4-6 W), Voraussetzung: Workspace-Isolation verifiziert
6. Erweiterte KI Analyse — Sehr hoch (8-12 W), Voraussetzung: Phase 4 + Datenschutz-Assessment

Invarianten unveraendert: PROHIBIT-02/06/08 gelten in allen Phasen.

## Release Candidate Gate (2026-06-15)

Entscheidung: **BLOCKED** (2/7) — `reports/current/release_candidate_gate.json`
Vollstaendige Dokumentation: `docs/release-candidate.md`

Root Causes:
1. TEST_DATABASE_URL fehlt: report_integrity_v2 BLOCKED (20 Blocker) -> Gate-Kaskade (GATE-01, GATE-05)
2. AppShell NAV_ITEMS: 4 Abweichungen vom Masterplan (GATE-02, GATE-04)
3. routes.jsx: kein Router-seitiger Admin-Guard /admin/diagnostics (GATE-03)

PASS: GATE-06 (0 BLOCKING_CORE), GATE-07 (Cleanup/Repair NO-GO bestaetigt)

RC-Checks: Regression Guard 6/6 PASS. Enduser Acceptance 7/10 PASS. Security Smoke 9/10 PASS. Navigation 4/8 PASS.
Mindest-Fixes: RC-PREREQ-01 (TEST_DATABASE_URL), RC-PREREQ-02 (NAV), RC-PREREQ-03 (Routing)

## Release Candidate Decision (Vorgaenger, 2026-06-15)

Entscheidung: **BLOCKED** — `reports/current/release_candidate_decision.json` (abgeloest durch RC Gate)

3/4 RC-Kriterien erfuellt (keine BLOCKING_CORE Limitations + documentation_truth_lint PASS). Unblocking: TEST_DATABASE_URL setzen, pytest neu ausfuehren.

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
