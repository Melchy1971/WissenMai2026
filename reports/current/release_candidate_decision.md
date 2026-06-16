# Release Candidate Decision

Stand: 2026-06-15
Entscheidung: **BLOCKED**

---

## Ergebnis

**RELEASE_CANDIDATE: NEIN**

3 von 4 RC-Kriterien erfüllt. 2 Kriterien nicht erfüllt — beide auf denselben Root Cause zurückführbar.

---

## RC-Kriterien

| Kriterium | Erforderlich | Status |
|---|---|---|
| `local_final_gate` PASS | Ja | NICHT ERFÜLLT — verdict=BLOCKED |
| Keine `BLOCKING_CORE` Limitations | Ja | Erfüllt — 0 von 6 Limitations sind BLOCKING_CORE |
| `documentation_truth_lint` PASS | Ja | Erfüllt — 19/19 Checks PASS |
| `report_integrity_v2` PASS | Ja | NICHT ERFÜLLT — BLOCKED (20 Blocker) |
| `external_env_gate` NOT_RUN erlaubt | Nein (optional) | Erfüllt — status=NOT_RUN |

---

## Blocker-Kette

Root Cause: **TEST_DATABASE_URL nicht gesetzt**

```
TEST_DATABASE_URL fehlt
→ m5a_source_status_integrity_gate: collected=0, errors=1
→ m5a_orphan_detector_gate: collected=0, errors=1
→ m5a_data_quality_gate: nicht lauffähig
→ m5a_final_readiness_review: blockiert
→ report_integrity_v2: BLOCKED (20 Blocker)
→ m5b_alpha_hardening_gate: BLOCKED (cascade)
→ m5b_production_readiness_gate: BLOCKED (cascade)
→ m5c_start_gate: BLOCKED (cascade)
→ local_final_gate: BLOCKED (4 required gates BLOCKED)
→ release_candidate_decision: BLOCKED
```

**Einzige erforderliche Aktion:**
`TEST_DATABASE_URL` setzen → pytest neu ausführen → report_integrity_v2 neu generieren → cascade-Blocker lösen sich auf.

---

## Inputs

| Report | Status | Relevant für RC |
|---|---|---|
| `final_gate_report.json` | BLOCKED (4/10 required BLOCKED) | Ja — blockiert |
| `external_env_gate.json` | NOT_RUN (72 Tests) | Nein — nicht erforderlich |
| `masterplan_status_v2.json` | blocked | Informativ |
| `known_limitations.json` | INFO (0 BLOCKING_CORE) | Ja — erfüllt |
| `documentation_truth_lint.json` | PASS (19/19) | Ja — erfüllt |
| `report_integrity_v2.json` | BLOCKED (20 Blocker) | Ja — blockiert |

**Hinweis:** `masterplan_status.json` ist truncated (JSON parse error) — `masterplan_status_v2.json` als Fallback verwendet.

---

## Warnungen (nicht blockierend)

| Gate | Warnung |
|---|---|
| `drift_v2_component_contract` | PARTIAL_FAIL: 3 testid-GAPs (drift-run-summary, drift-severity-breakdown, drift-type-breakdown). Pre-existing, dokumentiert in `docs/drift_v2_component_contract.md`. |
| `drift_dashboard_truth_report` | INVALID: JSON parse error (Datei truncated bei byte 2750). Vorgänger-Status war PASS (23/23). |

---

## Non-Blocking

| Gate | Grund |
|---|---|
| `permission_blocker` | ACL-Blockierung auf `features/drift` (alt). Aktiver Pfad ist `features/drift_v2`. Regel 6: NON_BLOCKING. |

---

## Externe Tests

| Gate | Status | Blockiert RC |
|---|---|---|
| `external_env_gate` | NOT_RUN (72 Tests) | Nein |

Ausführung erfordert: laufender Server (`uvicorn`) + `TEST_DATABASE_URL` gesetzt.
Dateien: `test_gui_backend_endpoints.py`, `test_gui_contracts.py`, `test_gui_secret_masking.py`, `test_secret_masking_api.py`, `test_settings_endpoints.py`, `test_settings_patch.py`

---

## Cleanup / Repair

**NO-GO.** M5c Cleanup ist gesperrt bis `m5c_start_gate = PASS` und PO-Sign-off vorliegen.
Aktive Verbote: PROHIBIT-02 (RepairButton), PROHIBIT-06 (CleanupButton).
