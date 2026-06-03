<!-- BEGIN GENERATED MASTERPLAN STATUS v3 -->
## Maschinenstatus Masterplan

Stand: `2026-06-03T09:11:54.280344+00:00`
Engine: `masterplan_status_engine_v3`

Gesamtstatus: `BLOCKED`
Fortschritt: `55%`
Release-Freigabe: `nein`
Blocker: `3`

> Dieser Abschnitt ist maschinell generiert. Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben.

### Phasen

| Phase | Status | Entscheidung | Gate | Gate-Status |
|---|---|---|---|---|
| M3a Frontend Foundation | `blocked` | `NO_GO` | `m3a_release_candidate_gate` | `FAIL` |
| M4 Backend | `gate_passed` | `GO` | `m4_backend_release_candidate_gate` | `PASS` |
| M5 Vorbereitung | `gate_passed` | `GO` | `m5_preparation_gate` | `PASS` |
| M5 Implementierung | `in_progress` | `NO_GO` | `m5_implementation_gate` | `IN_PROGRESS` |
| M5a Data Quality | `blocked` | `NO_GO` | `m5a_data_quality_gate` | `BLOCKED` |
| M5b Drift | `blocked` | `NO_GO` | `m5b_start_gate` | `BLOCKED` |

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

- M3a RC is STALE: mandatory input reports are newer than the RC. Regenerate with: python scripts/generate_m3a_release_candidate.py (documentation_truth_lint_newer_than_rc (2026-06-03T09:11:43.140066+00:00 > 2026-06-01T09:44:37.687128+00:00)) (laut reports/current/m3a_release_candidate.json)
- runtime_connectivity_gate: missing (laut docs/gate_hierarchy.json)
- M5 Implementierung ist nicht global PASS, solange m5a_data_quality_gate nicht PASS ist. (laut reports/current/m5a_data_quality_gate.json)
- M5a Data Quality gate is not PASS. (laut reports/current/m5a_data_quality_gate.json)
- report_integrity_pre_m5a: child status is blocking (['BLOCKED']) (laut docs/gate_hierarchy.json)
- source_status_integrity_gate: missing (laut docs/gate_hierarchy.json)
- orphan_detector_gate: missing (laut docs/gate_hierarchy.json)
- M5b darf erst PREPARED sein, wenn M5a durch das Parent-Gate PASS ist. (laut reports/current/m5a_data_quality_gate.json)
- M5b Start Gate is BLOCKED because m5a_data_quality_gate is not PASS. (laut reports/current/m5a_data_quality_gate.json)

<!-- END GENERATED MASTERPLAN STATUS v3 -->
