<!-- BEGIN GENERATED MASTERPLAN STATUS v2 -->
## Maschinenstatus Masterplan

Stand: `2026-05-27T09:09:52.387998+00:00`
Engine: `masterplan_status_engine_v2`

Gesamtstatus: `BLOCKED`
Fortschritt: `12.5%`
Freigabe: `nein`
Blocker: `8`

> Dieser Abschnitt ist maschinell generiert. Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben.

### Phasen

| Phase | Status | Entscheidung | Gate | Gate-Status |
|---|---|---|---|---|
| M3a Frontend Foundation | `tested` | `NO_GO` | `m3a_gate` | `FAIL` |
| M4 Stabilization | `blocked` | `NO_GO` | `m4_overall_gate` | `BLOCKED` |
| M5 Start | `blocked` | `NO_GO` | `m5_start_gate` | `BLOCKED` |
| Operational Governance | `blocked` | `NO_GO` | `operational_governance_gate` | `BLOCKED` |

### Gate-Hierarchie

| Gate | Status | Blocker |
|---|---|---|
| `m3a_gate` | `FAIL` | m3a_frontend_truth.json: passed (5) must equal collected (100); m3a_frontend_tru |
| `m4a_gate` | `PASS` | - |
| `m4b_gate` | `FAIL` | m4b_upload_queue_truth.json: passed (46) must equal collected (51); m4b_upload_q |
| `m4c_gate` | `PASS` | - |
| `m4e_gate` | `PASS` | - |
| `m4_crosscutting_gate` | `FAIL` | missing report: reports\current\m4_truth_report.json |
| `m4_overall_gate` | `BLOCKED` | dependency not passed: m4_crosscutting_gate; dependency not passed: m4b_gate |
| `m5_start_gate` | `BLOCKED` | dependency not passed: m4_overall_gate |
| `operational_governance_gate` | `BLOCKED` | dependency not passed: m5_start_gate |

### Dokumentations-Lint

- Ergebnis: `FAIL`
- Errors: `282`  Warnings: `67`

### Blocker

- **`doc_lint_errors`** [documentation]: documentation_truth_lint.json reports 282 errors (broken-reference=87, claim-without-reference=124, masterplan-contradic
- **`KL-M4-001`** [known_limitation]: Der aktuelle PostgreSQL-Truth-Report ist nicht gruen: 138 collected, 120 passed, 16 failed, 2 errors, exit_code 1.
- **`KL-M4-002`** [known_limitation]: M4b-kritischer Truth-Test fuer stale import job recovery ist rot.
- **`KL-M4-003`** [known_limitation]: PostgreSQL Truth enthaelt 2 Setup-/Collect-Errors; unklassifizierte Setup-Errors bleiben gate-blockierend.
- **`KL-M4-004`** [known_limitation]: Split-Reports fuer M4a, M4b, M4c, M4e und M4 Gesamt fehlen im reports-Verzeichnis.
- **`KL-M5-001`** [known_limitation]: M5 Startgate bleibt blockiert, solange M4 Gesamtgate nicht PASS ist.
- **`KL-M5-002`** [known_limitation]: Aktuelle PostgreSQL-Truth-Findings enthalten 15 M5 Entropy-/Drift-Failures.
- **`KL-M5-003`** [known_limitation]: Operational Governance Gate darf erst nach M5 Startgate blockierend bewertet werden.

### Known Limitations

- Gesamt: 15  Blockierend: 7

<!-- END GENERATED MASTERPLAN STATUS v2 -->
