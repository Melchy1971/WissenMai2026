<!-- BEGIN GENERATED MASTERPLAN STATUS v3 -->
## Maschinenstatus Masterplan

Stand: `2026-06-08T10:07:06.754746+00:00`
Engine: `masterplan_status_engine_v3`

Gesamtstatus: `BLOCKED`
Fortschritt: `50.0%`
Release-Freigabe: `nein`
Blocker: `3`

> Dieser Abschnitt ist maschinell generiert. Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben.

### Phasen

| Phase | Status | Entscheidung | Gate | Gate-Status |
|---|---|---|---|---|
| M3a Frontend Foundation | `blocked` | `NO_GO` | `m3a_release_candidate_gate` | `FAIL` |
| M4 Backend | `gate_passed` | `GO` | `m4_backend_release_candidate_gate` | `PASS` |
| M5 Vorbereitung | `gate_passed` | `GO` | `m5_preparation_gate` | `PASS` |
| M5 Implementierung | `blocked` | `NO_GO` | `m5_implementation_gate` | `BLOCKED` |
| M5a Data Quality | `blocked` | `NO_GO` | `m5a_data_quality_gate` | `BLOCKED` |
| M5b Drift | `blocked` | `NO_GO` | `m5b_start_gate` | `DRAFT` |

### M5 Statusmodell

- Status: `SLICE_IMPLEMENTING`
- M5a: `BLOCKED`
- M5b: `DRAFT`
- Implementierung global: `NO_GO`
- Parent-Gate-Hierarchie: `BLOCKED`

### Dokumentations-Lint

- Ergebnis: `PASS`
- Errors: `0`  Warnings: `0`

### Blocker

- documentation_truth_lint: passing child report requires collected > 0 or report_type=supporting (laut docs/gate_hierarchy.json)
- M5 Implementierung ist nicht global PASS, solange m5a_data_quality_gate nicht PASS ist. (laut reports/current/m5a_data_quality_gate.json)
- M5a Data Quality gate is not PASS. (laut reports/current/m5a_data_quality_gate.json)
- report_integrity_v2: child status is blocking (['BLOCKED']) (laut docs/gate_hierarchy.json)
- documentation_truth_lint: passing child report requires collected > 0 or report_type=supporting (laut docs/gate_hierarchy.json)
- data_quality_report: passing child report requires collected > 0 or report_type=supporting (laut docs/gate_hierarchy.json)
- source_status_integrity_gate: child status is blocking (['BLOCKED']) (laut docs/gate_hierarchy.json)
- orphan_detector_gate: child status is blocking (['BLOCKED']) (laut docs/gate_hierarchy.json)
- M5b bleibt BLOCKED bis m5a_data_quality_gate PASS/GO meldet. (laut reports/current/m5a_data_quality_gate.json)
- M5b bleibt DRAFT bis reports/current/m5a_data_quality_gate.json status=PASS, decision.go_no_go=GO und parent_gate_validation.status=PASS meldet. (laut reports/current/m5a_data_quality_gate.json)

<!-- END GENERATED MASTERPLAN STATUS v3 -->
