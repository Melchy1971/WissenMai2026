# Projektstatus

Stand: `reports/current/masterplan_status.json`

Der aktuelle Projektstatus, Data-Quality-Status, Score und Gate-Entscheidungen werden ausschliesslich aus maschinenlesbaren Reports abgeleitet:

- `reports/current/masterplan_status.json` - Gesamtstatus und M5-Statusmodell
- `docs/gate_hierarchy.json` - Parent-/Child-Gate-Hierarchie
- `reports/current/m5a_final_readiness_review.json` - M5a Final Readiness und READY_FOR_M5B-Entscheidung
- `reports/current/m5a_data_quality_gate.json` - erforderlicher M5a Data-Quality-Eingang
- `reports/current/m5a_start_gate.json` - M5a Slice-Start-Gate
- `reports/current/m5b_release_decision.json` - M5b PREPARED-/GO-Entscheidung
- `reports/current/documentation_truth_lint.json` - Dokumentations-Lint

Manuelle Statusaussagen duerfen keine Report-Werte ueberschreiben.

## M5a Regel

M5a ist nur dann Gesamt-`PASS`, wenn `reports/current/m5a_final_readiness_review.json` `READY_FOR_M5B` meldet. Diese Entscheidung setzt M5a Data Quality, Report Integrity v2, Documentation Truth Lint und M5a-scope Known Limitations voraus.

Slice-Gates wie `reports/current/m5a_duplicate_detector_gate.json`, `reports/current/m5a_metadata_detector_gate.json` oder `reports/current/m5a_lifecycle_integrity_gate.json` belegen nur ihren jeweiligen Slice. Ein Slice-`PASS` ist keine M5a-Gesamtfreigabe.

## M5b Regel

M5b Drift Architecture darf als Planung `DRAFT` sein, siehe `docs/m5b-drift-architecture.md`.

`reports/current/m5b_release_decision.json` trennt die Stufen: `DRAFT` erlaubt Architekturplanung, `PREPARED` erlaubt Vorbereitung ohne Implementierung, und nur `GO` erlaubt M5b Implementierung. Solange M5a nicht ueber `reports/current/m5a_final_readiness_review.json` bereit ist, bleibt M5b blockiert.

Stand 2026-06-12: M5b-Implementierung vollstaendig (Drift Detection, CLI, Dashboard, API, Observability, Performance Baseline). M5b-Gates BLOCKED durch Kaskade: Alpha Hardening Gate BLOCKED (AHG-BLOCKER-01: M5a nicht READY_FOR_M5B; AHG-BLOCKER-02: drift_report_integrity PARTIAL) → Beta BLOCKED → Production Readiness BLOCKED. M5c Preparation PREPARED (16/16 Checks, `reports/current/m5c_preparation_gate.json`). M5c GO nicht erlaubt: `reports/current/m5c_start_gate.json` BLOCKED. Cleanup-Implementierung und Repair-Aktionen dauerhaft verboten (PROHIBIT-02, PROHIBIT-06). Quelle: `reports/current/m5b_alpha_hardening_gate.json`, `reports/current/m5b_production_readiness_gate.json`, `reports/current/m5c_preparation_gate.json`, `reports/current/m5c_start_gate.json`.

## M5c Regel

M5c Cleanup darf erst implementiert werden wenn: (1) `reports/current/m5c_start_gate.json` = PASS, (2) PO-Sign-off auf `reports/current/cleanup_governance_boundary.json`. Beides ist aktuell nicht erfuellt. Status: NO_GO.

M5c Preparation = PREPARED bedeutet ausschliesslich: Definitionsdokumente sind komplett und valide. Es bedeutet nicht: GO, nicht: Implementierung erlaubt, nicht: Cleanup freigegeben.

Dry-Run-Only: Jeder M5c-Run ist ein Dry Run. Keine automatische Ausfuehrung ohne explizites PO-Approval je Proposal (No-Auto-Execute, PROHIBIT-08).

## Globale Aussagen

Es gibt keine globale 100%- oder Vollstaendigkeits-Aussage in dieser Datei. Fortschritt, Blocker und Freigaben stehen im generierten Maschinenstatus `reports/current/masterplan_status.json`.

## Documentation Truth Lint

Aktueller Nachweis: `reports/current/documentation_truth_lint.json`.

## Release Candidate Decision (Stand 2026-06-15)

Entscheidung: **BLOCKED** — Quelle: `reports/current/release_candidate_decision.json`

RC-Kriterien:

| Kriterium | Erforderlich | Status |
|---|---|---|
| `local_final_gate` PASS | Ja | NICHT ERFÜLLT — BLOCKED (4 required gates) |
| Keine `BLOCKING_CORE` Limitations | Ja | Erfüllt — 0 BLOCKING_CORE |
| `documentation_truth_lint` PASS | Ja | Erfüllt — 19/19 |
| `report_integrity_v2` PASS | Ja | NICHT ERFÜLLT — BLOCKED (20 Blocker) |
| `external_env_gate` NOT_RUN erlaubt | Nein | Erfüllt — NOT_RUN |

Root Cause: `TEST_DATABASE_URL` nicht gesetzt → m5a DB-Gates collected=0 → report_integrity_v2 BLOCKED → cascade.

## Local Final Gate Validator v2 (Stand 2026-06-15)

Validator: `scripts/local_final_gate_validator_v2.py`
Dependency Graph: `local_final_gate_dependency_graph.json`
Output: `reports/current/final_gate_report.json` — verdict=**BLOCKED**

Externe Tests: `reports/current/external_env_gate.json` — status=NOT_RUN (72 Tests). Blockiert local_final_gate nicht.

## PRI-2 Abschluss — Analysebereich (Stand 2026-06-16)

Sprint PRI-2 "Analysis Feature" abgeschlossen. 9/9 Tasks (#74–#82) completed. Sprint-Gate PASS.

| Kennzahl | Wert |
|---|---|
| Tasks abgeschlossen | 9/9 |
| Unit-Fast-Tests hinzugefügt | 95 |
| Gold-Path GP-A01–GP-A11 | 11/11 PASS |
| Product Gold Path | 7/8 PASS (GP-07 Export offen) |
| Product Maturity Score | 69 (v2: 52, Delta +17) |
| Schwellwert für 1.0-Release | 85 |

Datenanalyse ist vollständig implementiert: Data Model (Migration 0023), AnalysisService, KI-Provider-Interface, 10 REST-Endpoints, AnalysisPage.jsx, NewAnalysisJobDialog (5-Step-Wizard), Approval-Policy (8 Regeln), KB-Import-Service (Tags, Topics, DocumentTags, idempotent).

Security-Constraints eingehalten: PROHIBIT-02 (kein RepairButton), PROHIBIT-06 (kein CleanupButton), PROHIBIT-08 (Import nur nach approved + confirm=True + admin-Rolle).

Quellen: `reports/current/analysis_sprint_gate.json`, `reports/current/analysis_gold_path.json`, `reports/current/product_gold_path.json`, `reports/current/product_maturity_v3.json`.

Nächster Sprint PRI-3: Export Center (GP-07), Release-Gate entsperren (TEST_DATABASE_URL), Suche KWIC.

## PRI-4 Abschluss — Dashboard Drift Analytics (Stand 2026-06-17)

Sprint PRI-4 "Dashboard Drift Analytics" abgeschlossen. 10/10 Tasks (#3–#12) completed. Sprint-Gate PASS.

| Kennzahl | Wert |
|---|---|
| Tasks abgeschlossen | 10/10 |
| Gold-Path DGP-01–DGP-10 | 10/10 PASS |
| Additional Paths | 2/2 PASS |
| Security Checks | 7/7 PASS |
| Test-Coverage (Gesamt) | 78 Tests PASS |
| Backend Coverage | 92% |
| Frontend Coverage | 88% |
| Blocking Gaps | 0 |

Dashboard Drift Analytics ist vollständig implementiert: Datenmodell (Migration 0025, analytics_snapshots + analytics_metrics), AnalyticsRepository (INSERT-only, frozen dataclasses), DriftAnalyticsService (THRESHOLDS-Dict, 6 Calculators), 5 REST-Endpoints (/api/v1/drift/*), DriftWidgetPanel (6 Karten, GlobalStatusBar, RecalcDialog), DriftAnalyticsPage (4 Sektionen), AppShell-Integration (DriftGlobalBadge, BlockedBadge).

Security-Constraints eingehalten: PROHIBIT-02 (kein RepairButton), PROHIBIT-06 (kein CleanupButton), PROHIBIT-08 (POST /recalculate nur nach Confirm-Dialog). Fehlende Daten → WARNING (nicht PASS). BLOCKED(3) > FAIL(2) > WARNING(1) > PASS(0). Snapshots immutable. Keine technischen IDs sichtbar.

**Abschlussregel erfüllt:** Dashboard Drift PASS → PRI-5 Release Hardening starten.

Quellen: `reports/current/drift_gold_path.json`, `reports/current/drift_coverage.json`, `reports/current/dashboard_release_report.json`.

## Drift v2 (Stand 2026-06-15)

Route `/drift` → `DriftPage` → `drift_v2/DriftDashboard` — aktiv.
Nachweis: `reports/current/drift_v2_ui_truth_report.json` PASS (29/29), `reports/current/drift_v2_import_audit.json` PASS (0 alte Imports).
Formale Freigabe: ausstehend (m5b_production_readiness_gate BLOCKED durch gate cascade).
Cleanup/Repair: NO_GO — PROHIBIT-02, PROHIBIT-06 aktiv.
