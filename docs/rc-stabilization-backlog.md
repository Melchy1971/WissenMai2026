# RC Stabilization Backlog

Stand: 2026-06-15
RC Gate: BLOCKED (2/7)
Quelle: `reports/current/rc_stabilization_backlog.json`

---

## Kategorie 1: Release Blocker

Muss vor RELEASE_CANDIDATE behoben sein.

### RCB-001 — TEST_DATABASE_URL fehlt: PostgreSQL-Truth-Tests nicht ausfuehrbar

| Feld | Wert |
|------|------|
| Ursache | `TEST_DATABASE_URL` nicht in `.env` gesetzt. pytest sammelt 0 Tests (collected=0, errors=1) fuer m5a_source_status_integrity und m5a_orphan_detector. |
| Risiko | Kaskade: report_integrity_v2 (20 Blocker) -> m5b_alpha_hardening -> m5b_production_readiness -> m5c_start_gate -> local_final_gate. Root Cause fuer GATE-01 und GATE-05. |
| Betroffene Datei | `.env` (fehlt), `backend/tests/postgres_truth/test_m5a_source_status_integrity_truth.py`, `backend/tests/postgres_truth/test_m5a_orphan_detector_truth.py` |
| Fix | `TEST_DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname` in `.env` setzen. Danach: `pytest tests/api -m local_gate` -> `python scripts/generate_report_integrity_v2.py` -> `python scripts/local_final_gate_validator_v2.py` |
| Gate-Auswirkung | Loest GATE-01 + GATE-05 + gesamte Blocker-Kaskade (5 Gates) |
| Aufwand | Niedrig — Konfiguration, kein Code |
| Referenz | BLOCKER-TI-001, BLOCKER-TI-002, RC-PREREQ-01 |

### RCB-002 — AppShell NAV_ITEMS divergiert vom Masterplan: 4 Abweichungen

| Feld | Wert |
|------|------|
| Ursache | `/search` statt `/chat`, `/data-quality` fehlt in NAV, `/topics` und `/import` extra (nicht im Masterplan). |
| Risiko | S04 (Suche) BLOCKED, S08 (Data Quality) BLOCKED. Navigation R1, R7, R8 FAIL. Blockiert GATE-02 und GATE-04. |
| Betroffene Datei | `frontend/src/components/AppShell.jsx` (NAV_ITEMS), `docs/final_navigation.md` |
| Fix | PO-Entscheidung: Option A) `/search` -> `/chat`, `/data-quality` hinzufuegen, `/topics` + `/import` entfernen. Option B) Masterplan erweitern. NAV-FIX-01 bis -03 umsetzen. Danach Reports neu ausfuehren. |
| Gate-Auswirkung | Loest GATE-02 (enduser_acceptance) + GATE-04 (navigation_release_check) |
| Aufwand | Niedrig bis mittel — PO-Entscheidung erforderlich |
| Referenz | NAV-FIX-01, NAV-FIX-02, NAV-FIX-03, RC-PREREQ-02, S04, S08 |

### RCB-003 — routes.jsx: kein Router-seitiger Admin-Guard + 7 undokumentierte Routen

| Feld | Wert |
|------|------|
| Ursache | `AdminDiagnosticsPage` prueft `isAdmin()` nur in Komponente. Route erreichbar fuer alle angemeldeten User. `/tools`, `/memory`, `/tasks`, `/projects`, `/agents`, `/collaboration`, `/governance` ohne Rollengate. |
| Risiko | Defense-in-depth verletzt. Angreifsflaeche unnoetig gross. SEC-10 BLOCKED. Blockiert GATE-03. |
| Betroffene Datei | `frontend/src/app/routes.jsx`, `frontend/src/pages/AdminDiagnosticsPage.jsx` |
| Fix | `AdminRoute`-Wrapper in `routes.jsx`. `/admin/diagnostics` in `AdminRoute` wickeln. Die 7 undokumentierten Routen entfernen oder hinter `AdminRoute`. Danach `rc_security_smoke_report.json` neu ausfuehren. |
| Gate-Auswirkung | Loest GATE-03 (security_smoke) + R8 in GATE-04 |
| Aufwand | Niedrig — Router-Wrapper, kein Logik-Change |
| Referenz | SEC-10, NAV-FIX-04, NAV-FIX-05, RC-PREREQ-03, GATE-03 |

---

## Kategorie 2: High Priority

Blockieren nachgelagerte Gates oder erzeugen Kaskaden-Risiken.

### RCH-001 — Drift CLI nie ausgefuehrt: drift_report.json + drift_summary.json fehlen

| Feld | Wert |
|------|------|
| Ursache | Kein einmaliger Drift-CLI-Run erfolgt. Dateien existieren nicht. Unabhaengig von TEST_DATABASE_URL. |
| Risiko | `drift_report_integrity` PARTIAL. Blockiert `m5b_alpha_hardening` (AHG-BLOCKER-02) + `m5c_start_gate` (SG-03). |
| Betroffene Datei | `reports/current/drift_report.json` (fehlt), `reports/current/drift_summary.json` (fehlt) |
| Fix | `python -m drift.cli run` ausfuehren. Danach `drift_report_integrity` neu generieren. Drift ist Read-Only — kein Mutationsrisiko (PROHIBIT-02/06 aktiv). |
| Gate-Auswirkung | Loest AHG-BLOCKER-02 + SG-03. Parallel zu RCB-001 abarbeitbar. |
| Aufwand | Niedrig — einmaliger CLI-Run |
| Referenz | BLOCKER-DR-001, BLOCKER-DR-002, FIX-002 |

### RCH-002 — drift_dashboard_truth_report.json truncated (JSON_PARSE_ERROR)

| Feld | Wert |
|------|------|
| Ursache | Datei endet bei char 2750 ohne schliessende Klammern. Frueher PASS (23/23). |
| Risiko | Optional Gate INVALID statt PASS. WARNING in `local_final_gate`. Kein direkter RC-Blocker. |
| Betroffene Datei | `reports/current/drift_dashboard_truth_report.json` |
| Fix | `npm run test -- --reporter=json` neu ausfuehren und Datei neu schreiben. |
| Gate-Auswirkung | Optional Gate: WARNING entfaellt. Kein Einfluss auf RC Gate. |
| Aufwand | Niedrig |
| Referenz | WARN-DR-001 |

---

## Kategorie 3: Medium Priority

Bekannte Defekte ohne direkten RC-Block. Sollten vor erstem produktivem Betrieb behoben sein.

### RCM-001 — 3 testid-GAPs in DriftDashboard.jsx

| Feld | Wert |
|------|------|
| Ursache | `data-testid` fehlen: `drift-run-summary`, `drift-severity-breakdown`, `drift-type-breakdown`. |
| Risiko | `drift_v2_component_contract` PARTIAL_FAIL. Erschwerter automatisierter E2E-Test. |
| Betroffene Datei | `frontend/src/features/drift_v2/DriftDashboard.jsx` |
| Fix | 3 `data-testid`-Attribute einfuegen. Test-Assertions aktualisieren. |
| Gate-Auswirkung | Optional Gate: PARTIAL_FAIL -> PASS. Kein RC-Blocker. |
| Aufwand | Niedrig — 3 Attribut-Ergaenzungen |
| Referenz | WARN-DR-002, docs/drift_v2_component_contract.md |

### RCM-002 — /import und /topics in NAV ohne Masterplan-Deckung

| Feld | Wert |
|------|------|
| Ursache | NAV_ITEMS enthalten `/import` und `/topics`, die nicht in `docs/final_navigation.md` stehen. |
| Risiko | Ungeplante Funktionen in Navigation. S03/S05 PASS_WITH_WARNING. |
| Betroffene Datei | `frontend/src/components/AppShell.jsx`, `docs/final_navigation.md` |
| Fix | Wird durch RCB-002-Fix mitgeloest (PO-Entscheidung zu NAV_ITEMS). |
| Gate-Auswirkung | Teil von GATE-02 (S03/S05) und GATE-04 (R7). |
| Aufwand | Abhaengig von PO-Entscheidung |
| Referenz | S03, S05, NAV-FIX-03, RCB-002 |

---

## Kategorie 4: Low Priority

Technical Debt. Keine Gate-Auswirkung.

| ID | Titel | Referenz |
|----|-------|---------|
| RCL-001 | API-Alias `/api/v1/documents` nicht durchgaengig verfuegbar | KL-NB-001 |
| RCL-002 | OCR fuer gescannte PDFs nicht in V1 | KL-DEF-001 |
| RCL-003 | Embeddings und Vektorsuche optional, nicht V1-kritisch | KL-DEF-002 |

---

## Kategorie 5: External Env Only

### EXT-001 — 72 externe Tests NOT_RUN

| Feld | Wert |
|------|------|
| Ursache | Tests benoetigen laufendes Backend (`localhost:8000`) + `TEST_DATABASE_URL`. NOT_RUN ist erlaubter RC-Zustand. |
| Risiko | Unbekannte Integrationsfehler bis zu externem Test-Lauf. |
| Betroffene Datei | `tests/api/test_gui_backend_endpoints.py` u.a. (6 Dateien, 72 Tests) |
| Fix | Backend starten, dann: `pytest tests/api -m 'external_env_only or legacy_live_http'`. Erst nach RC-Stabilisierung (OPT-2). |
| Gate-Auswirkung | `external_env_gate`: NOT_RUN -> PASS. Kein RC-Blocker. Separate Freigabestufe. |
| Aufwand | Mittel — Infrastruktur-Voraussetzung |

---

## Kategorie 6: Future Phase

| ID | Titel | Target | Referenz |
|----|-------|--------|---------|
| FUT-001 | M5 Entropy-/Drift-Truth-Failures blockieren Slice-Start | M5B_IMPL | KL-M5-T-001 |
| FUT-002 | Drei Pflicht-Artefakte pro M5-Slice fehlen vor Slice-Start | M5B_IMPL | KL-M5-T-002 |
| FUT-003 | Mutierende Admin-Aktionen ohne Runbook gesperrt | GOVERNANCE | KL-GOV-001 |
| FUT-004 | Cleanup Governance DRAFT statt RATIFIED (SG-05) | M5C_START | m5c_start_gate |

---

## Minimaler Unblocking-Pfad

```
RCB-001: TEST_DATABASE_URL setzen
  -> pytest tests/api -m local_gate
  -> python scripts/generate_report_integrity_v2.py
  -> python scripts/local_final_gate_validator_v2.py

RCH-001 (parallel): python -m drift.cli run
  -> drift_report_integrity neu generieren

RCB-002: PO-Entscheidung NAV_ITEMS
  -> AppShell.jsx korrigieren
  -> enduser_acceptance_rc.json + final_navigation_release_check.json neu ausfuehren

RCB-003: AdminRoute-Wrapper in routes.jsx
  -> rc_security_smoke_report.json neu ausfuehren

RC Gate re-run -> Erwartetes Ergebnis: RELEASE_CANDIDATE (7/7)
```

**M5c-Implementierung bleibt gesperrt** bis: RC = RELEASE_CANDIDATE + externe Testentscheidung + m5c_start_gate PASS + PO-Sign-off.
