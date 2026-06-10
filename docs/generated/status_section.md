<!-- BEGIN GENERATED MASTERPLAN STATUS v3 -->
## Maschinenstatus Masterplan

Stand: `2026-06-10T08:49:46.556653+00:00`
Engine: `masterplan_status_engine_v3`

Gesamtstatus: `BLOCKED`
Fortschritt: `50.0%`
Release-Freigabe: `nein`
Blocker: `4`

> Dieser Abschnitt ist maschinell generiert. Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben.

### Phasen

| Phase | Status | Entscheidung | Gate | Gate-Status |
|---|---|---|---|---|
| M3a Frontend Foundation | `blocked` | `NO_GO` | `m3a_release_candidate_gate` | `FAIL` |
| M4 Backend | `gate_passed` | `GO` | `m4_backend_release_candidate_gate` | `PASS` |
| M5 Vorbereitung | `gate_passed` | `GO` | `m5_preparation_gate` | `PASS` |
| M5 Implementierung | `blocked` | `NO_GO` | `m5_implementation_gate` | `BLOCKED` |
| M5a Data Quality | `blocked` | `NO_GO` | `m5a_final_readiness_review` | `BLOCKED` |
| M5b Drift | `blocked` | `NO_GO` | `m5b_release_decision` | `BLOCKED` |

### M5 Statusmodell

- Status: `SLICE_IMPLEMENTING`
- M5a: `BLOCKED`
- M5b: `BLOCKED`
- Implementierung global: `NO_GO`
- Parent-Gate-Hierarchie: `BLOCKED`

### Dokumentations-Lint

- Ergebnis: `PASS`
- Errors: `0`  Warnings: `0`

### Blocker

- M3a RC is STALE: mandatory input reports are newer than the RC. Regenerate with: python scripts/generate_m3a_release_candidate.py (documentation_truth_lint_newer_than_rc (2026-06-10T08:49:25.259368+00:00 > 2026-06-05T10:06:18.467008+00:00)) (laut reports/current/m3a_release_candidate.json)
- documentation_truth_lint: passing child report requires collected > 0 or report_type=supporting (laut docs/gate_hierarchy.json)
- M5 Implementierung ist nicht global PASS, solange M5a Final Readiness nicht READY_FOR_M5B ist. (laut reports/current/m5a_final_readiness_review.json)
- m5a_data_quality_gate.status=BLOCKED; READY_FOR_M5B requires PASS. (laut reports/current/m5a_data_quality_gate.json)
- report_integrity_v2.status=BLOCKED; READY_FOR_M5B requires PASS. (laut reports/current/report_integrity_v2.json)
- M5b bleibt BLOCKED bis m5a_final_readiness_review READY_FOR_M5B meldet. (laut reports/current/m5a_final_readiness_review.json)
- Report Integrity evidence is BLOCKED, not PASS. (laut reports/current/report_integrity_v2.json)

<!-- END GENERATED MASTERPLAN STATUS v3 -->

<!-- BEGIN M5B PREPARATION ADDENDUM — Stand: 2026-06-10 -->
## M5b Preparation Addendum

> Ergaenzung zur maschinengenerierten Statusmatrix. Quelle: `reports/current/m5b_preparation_gate.json`, `reports/current/m5b_implementation_gate.json`.

### M5b Status

| Dimension | Status |
|-----------|--------|
| M5b formal PREPARED | BLOCKED (6/8 Kriterien) |
| M5b formal GO | NO-GO (1/4 Kriterien) |
| Preparation-Artefakte vollstaendig | JA (10/10) |
| Drift Detection Code implementiert | NEIN |
| Implementation erlaubt | NEIN |

**PREPARED != IMPLEMENTED.** Alle Planungsartefakte sind vorhanden. Formales PREPARED bleibt geblockt durch PG-07 (M5a READY_FOR_M5B) und PG-08 (Report Integrity PASS).

### M5b Blocker

| ID | Kriterium | Quelle |
|----|-----------|--------|
| PG-BLOCKER-01 | M5a READY_FOR_M5B fehlt | `reports/current/m5a_final_readiness_review.json` |
| PG-BLOCKER-02 | Report Integrity nicht PASS | `reports/current/report_integrity_v2.json` |
| IG-BLOCKER-01 | Start-Gate NO_GO | `reports/current/m5b_start_gate.json` |
| IG-BLOCKER-02 | KL-M5-T-001, KL-M5-T-002 offen | `reports/current/known_limitations.json` |
| IG-BLOCKER-03 | KL-GOV-001 nicht abgegrenzt | `reports/current/known_limitations.json` |

<!-- END M5B PREPARATION ADDENDUM -->

<!-- BEGIN M5B ARCHITECTURE ADDENDUM — Stand: 2026-06-10 -->
## M5b Architecture Addendum

> Ergaenzung zur maschinengenerierten Statusmatrix. Quelle: `reports/current/m5b_architecture_review.json`, `reports/current/m5b_preparation_gate.json`.

### Architecture Review Ergebnis

| Dimension | Status |
|-----------|--------|
| Architecture Review | COMPLETE |
| Review Score | 8/8 Artefakte vollstaendig |
| Strukturelle Luecken | 0 |
| Offene Entscheidungen | 3 (OD-01, OD-02, OD-03) |
| Blockierende Risiken | 2 (CCR-02, CCR-03) |
| Preparation-Artefakte gesamt | 27 (PREP-01 bis PREP-27) |
| Neue Artefakte (diese Phase) | 17 (PREP-11 bis PREP-27) |
| Implementation erlaubt | NEIN |
| Implementation Gate | NO-GO |
| Drift Code implementiert | NEIN |

### Neue Artefakte (PREP-11 bis PREP-27)

| ID | Artefakt |
|----|----------|
| PREP-11 | docs/m5b-drift-governance.md |
| PREP-12 | drift_governance.schema.json |
| PREP-13 | docs/m5b-drift-severity.md |
| PREP-14 | drift_severity_matrix.json |
| PREP-15 | docs/m5b-entity-mapping.md |
| PREP-16 | drift_entity_mapping.json |
| PREP-17 | docs/m5b-drift-metrics.md |
| PREP-18 | drift_metrics.schema.json |
| PREP-19 | docs/m5b-drift-history.md |
| PREP-20 | drift_history_model.json |
| PREP-21 | docs/m5b-reporting.md |
| PREP-22 | reporting_architecture.json |
| PREP-23 | docs/m5b-testdata-strategy.md |
| PREP-24 | drift_test_dataset_plan.json |
| PREP-25 | docs/m5b-rollback.md |
| PREP-26 | rollback_strategy.json |
| PREP-27 | reports/current/m5b_architecture_review.json |

### Offene Entscheidungen (loesen vor Implementation Gate GO)

| ID | Beschreibung | Impact |
|----|--------------|--------|
| OD-01 | Search-Index-Technologie nicht festgelegt | low |
| OD-02 | DriftSnapshot-Retention kein oberes Limit | medium |
| OD-03 | Feature-Flag-Speichermechanismus nicht spezifiziert | low |

### Blockierende Risiken

| ID | Beschreibung | Aktion |
|----|--------------|--------|
| CCR-02 | KL-GOV-001 nicht gegen read-only Drift Checks abgegrenzt | Erklaerung in known_limitations.json eintragen |
| CCR-03 | Externe Preconditions unerfuellt (M5a READY_FOR_M5B, Report Integrity PASS) | Externe Preconditions ausraeumen |

**Architecture COMPLETE != Implementation freigegeben.** M5b bleibt BLOCKED. Implementation Gate NO-GO.

<!-- END M5B ARCHITECTURE ADDENDUM -->

<!-- BEGIN M5B ALPHA ADDENDUM — Stand: 2026-06-10 -->
## M5b Alpha Addendum

> Ergaenzung nach Alpha-Evaluation. Quelle: `reports/current/m5b_alpha_validation_report.json`, `reports/current/m5b_beta_start_gate.json`.

### Alpha Validation Ergebnis

| Dimension | Status |
|-----------|--------|
| Alpha Validation | BLOCKED |
| Inputs gefunden | 1/4 (nur documentation_truth_lint.json) |
| Alpha-Implementierung vorhanden | NEIN |
| Implementation Gate | NO-GO |
| Drift Code implementiert | NEIN |

Alpha ist korrekt BLOCKED: keine Implementierung vorhanden. Dies ist kein Fehler, sondern der erwartete Zustand bei Implementation Gate NO-GO.

### Beta Start Gate Ergebnis

| Kriterium | Status | Quelle |
|-----------|--------|--------|
| BSG-01 M5b Alpha Validation PASS | FAILED | m5b_alpha_validation_report.json |
| BSG-02 Drift Regression Suite PASS | FAILED | m5b_drift_regression_report.json (fehlt) |
| BSG-03 Drift Report Schema Validation PASS | FAILED | drift_report_schema_validation.json (fehlt) |
| BSG-04 Drift API Scope definiert | PASS | docs/m5b-drift-api-scope.md, openapi_drift_scope.json |
| BSG-05 Drift Dashboard Scope definiert | PASS | docs/m5b-drift-dashboard-scope.md, dashboard_testids.md |
| BSG-06 Documentation Truth PASS | PASS | reports/current/documentation_truth_lint.json |

**Ergebnis: BLOCKED (3/6 Kriterien).** Beta-Implementierung nicht erlaubt.

### Neue Planungsartefakte (diese Phase)

| Artefakt | Typ |
|----------|-----|
| `docs/m5b-drift-dashboard-scope.md` | Scope-Definition |
| `dashboard_testids.md` | Test-ID-Spezifikation |
| `docs/m5b-drift-api-scope.md` | API-Scope-Definition |
| `openapi_drift_scope.json` | Maschinenlesbares API-Schema |
| `docs/m5b-beta-boundary.md` | Beta-Boundary-Definition |
| `reports/current/m5b_alpha_validation_report.json` | Gate-Report |
| `reports/current/m5b_beta_start_gate.json` | Gate-Report |

### M5 Gesamtstatus

| Komponente | Status |
|------------|--------|
| M5b Alpha | BLOCKED |
| M5b Beta | BLOCKED |
| M5c | NOT_STARTED (NO_GO) |
| M5 Gesamt | OPEN |

**Alpha BLOCKED != Fehler.** Pfad zu Alpha GO: Implementation Gate GO erreichen (aktuell 1/4), dann Implementierung, dann Validierung.

<!-- END M5B ALPHA ADDENDUM -->
