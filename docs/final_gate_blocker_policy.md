# Final Gate Blocker Policy

Stand: 2026-06-15
Version: 1.0
Authority: PO (Markus Dickscheit)

---

## Kategorien

### 1. BLOCKING_CORE

Blockiert das lokale Final Gate vollständig. Release-Freigabe unmöglich.

Kriterien:
- Fehler in `report_integrity_v2` (Required-Set)
- Fehler im Backend Local Gate (`pytest tests/api -m local_gate`)
- Fehler in `documentation_truth_lint`

Beispiele:
- `m5a_source_status_integrity_gate` invalide → BLOCKING_CORE
- Local Gate Exit Code ≠ 0 → BLOCKING_CORE

---

### 2. BLOCKING_FRONTEND

Blockiert das lokale Final Gate. Tritt auf bei messbaren Frontend-Fehlern.

Kriterien:
- Vitest-Tests schlagen fehl (Exit Code ≠ 0, `numFailedTests > 0`)
- Pflicht-`data-testid` fehlt im DriftDashboard
- PROHIBIT-02 oder PROHIBIT-06 verletzt (Repair- oder Cleanup-Button im DriftDashboard)
- Parse-Fehler in einer Komponenten-Datei, die von aktiven Tests importiert wird

Beispiele:
- `DriftDashboard.test.jsx` Fehler → BLOCKING_FRONTEND
- `DashboardPage.jsx` truncated → BLOCKING_FRONTEND (löst Parse-Fehler in abhängigen Tests aus)

---

### 3. BLOCKING_BACKEND

Blockiert das lokale Final Gate auf Backend-Ebene.

Kriterien:
- Backend Local Gate (`pytest -m local_gate`) mit Fehler oder Skip
- `report_integrity_v2` mit blocking-Einträgen aus Required-Set
- Gate-Kaskade: wenn M5a blockiert ist, blockiert M5b transitiv

Beispiele:
- `m5a_orphan_detector_gate` invalide → BLOCKING_BACKEND via report_integrity_v2
- `m5b_alpha_hardening_gate` BLOCKED als Folge von M5a → BLOCKING_BACKEND

---

### 4. BLOCKING_TEST_INFRA

Blockiert das lokale Final Gate durch Infrastruktur-Defekte. Höhere Priorität als BLOCKING_CORE, weil Ergebnisse nicht verlässlich sind.

Kriterien:
- Testdatei strukturell korrupt (truncated, Syntax-Fehler, null bytes)
- `TEST_DATABASE_URL` nicht gesetzt → Postgres-Gate-Tests laufen nicht
- vitest kann nicht starten (Node/npm-Fehler)

Beispiele:
- `DriftDashboard.test.jsx` truncated → BLOCKING_TEST_INFRA bis repariert
- `TEST_DATABASE_URL` fehlt → Postgres-Truth-Tests nicht ausführbar → BLOCKING_TEST_INFRA

---

### 5. EXTERNAL_ONLY

Blockiert nicht lokal. Blockiert nur den External Env Gate.

Kriterien:
- Marker `external_env_only` oder `legacy_live_http`
- Tests, die httpx gegen einen laufenden Server brauchen
- Postgres-Truth-Tests ohne laufende Datenbank

Regel: Bewusstes Skip ist kein stiller PASS. External Env Tests müssen im externen Gate explizit ausgewiesen werden.

Beispiele:
- `test_gui_backend_endpoints.py` → EXTERNAL_ONLY
- `test_settings_endpoints.py` → EXTERNAL_ONLY

---

### 6. LEGACY_NON_BLOCKING

Blockiert weder lokal noch extern. Muss archiviert sein.

Kriterien:
- Test gehört zu einem Komponenten ohne aktive Route
- Test aus `frontend/tests/archive/legacy/` (außerhalb des vitest-include-Patterns)
- `known_limitations` mit `blocking=false`
- `m5_truth`, `governance_truth`, `observability_truth` (non-blocking für M4)

Regel: Ein LEGACY_NON_BLOCKING Test darf nicht in `src/tests/` liegen, wenn er eine Komponente ohne aktive Route testet. Er ist zu archivieren.

Beispiele:
- `DocumentsPage.test.jsx` → archiviert → LEGACY_NON_BLOCKING
- `known_limitations` KL-NB-001 → LEGACY_NON_BLOCKING

---

## Permission-Denied-Regel

```
permission_denied_on_old_path + active_safe_replacement_path = NON_BLOCKING

permission_denied_on_old_path + old_path_still_imported = BLOCKING_CORE
```

Anwendung auf Drift Path Recovery:
- `features/drift` nicht schreibbar (ACL) → irrelevant, weil `features/drift` nicht importiert wird
- `features/drift_v2` aktiv, alle Imports zeigen auf drift_v2 → non-blocking

---

## Skip-Regel

| Kontext | Wirkung |
|---|---|
| Skip in `local_gate` | BLOCKING_CORE |
| Skip in `external_env_only` | NON_BLOCKING lokal |
| Skip in `legacy_live_http` | NON_BLOCKING lokal |
| Timeout beim Ausführen | BLOCKING_TEST_INFRA |

---

## Anwendung auf final_gate_report.json

Jeder Eintrag in `blockers[]` trägt eine `category` aus dieser Policy. Jeder Eintrag in `non_blockers[]` trägt `EXTERNAL_ONLY` oder `LEGACY_NON_BLOCKING`.

Die `status`-Felder in `final_gate_report.json` werden ausschließlich nach dieser Policy gesetzt. Manuelle Überschreibungen sind nicht zulässig.
