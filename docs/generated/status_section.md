<!-- BEGIN GENERATED MASTERPLAN STATUS v3 -->
## Maschinenstatus Masterplan

Stand: `2026-06-01T07:46:51.064756+00:00`
Engine: `masterplan_status_engine_v3`

Gesamtstatus: `BLOCKED`
Fortschritt: `35%`
Release-Freigabe: `nein`
Blocker: `3`

> Dieser Abschnitt ist maschinell generiert. Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben.

### Phasen

| Phase | Status | Entscheidung | Gate | Gate-Status |
|---|---|---|---|---|
| M3a Frontend Foundation | `blocked` | `NO_GO` | `m3a_release_candidate_gate` | `FAIL` |
| M4 Backend | `gate_passed` | `GO` | `m4_backend_release_candidate_gate` | `PASS` |
| M5 Vorbereitung | `blocked` | `NO_GO` | `m5_preparation_gate` | `FAIL` |
| M5 Implementierung | `blocked` | `NO_GO` | `m5_implementation_gate` | `FAIL` |
| M5a Data Quality | `blocked` | `NO_GO` | `m5a_start_gate` | `FAIL` |

### M5

- Statusmodell: `BLOCKED`
- Vorbereitung erlaubt: `nein`
- Slice-Start erlaubt: `nein`
- Implementierung erlaubt: `nein`
- Implementierungsentscheidung: `NO_GO`

### Dokumentations-Lint

- Ergebnis: `PASS`
- Errors: `0`  Warnings: `0`

### Blocker

- `m3a_rc_stale`: M3a RC is STALE: mandatory input reports are newer than the RC. Regenerate with: python scripts/generate_m3a_release_candidate.py (documentation_truth_lint_newer_than_rc (2026-06-01T07:46:15.936859+00:00 > 2026-05-29T08:51:25.441334+00:00))
- `m3a_rc_not_pass`: m3a_release_candidate.json must be PASS/GO and not stale.
- `m5_assessment_implementation_contradiction`: m5_gate_assessment allows implementation without a valid slice start gate.

### M5-Implementierungsblocker

- `m5_assessment_implementation_contradiction`: m5_gate_assessment allows implementation without a valid slice start gate. Quelle: `reports/current/m5_gate_assessment.json`.

<!-- END GENERATED MASTERPLAN STATUS v3 -->
