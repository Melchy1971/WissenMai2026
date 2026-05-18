# Truth Root Cause Matrix

Stand: 2026-05-18

## Ziel

Diese Matrix reduziert die aktuellen roten Truth-Reports auf wenige gemeinsame Ursachencluster, damit die naechste Fix-Runde nicht gegen 38 Einzel-Fehlerfaelle blind arbeitet.

## Frontend Truth

Ausgangslage:

- `80 collected`
- `58 passed`
- `22 failed`
- Quelle: `reports/frontend_truth_report.json`

### Cluster 1: Auth-Bootstrap Error-Surface Mismatch

Prioritaet: `P1`

Betroffene Flows:

- Backend unreachable zeigt keinen erwarteten Error-State
- Retry nach backend unreachable landet nicht wie erwartet im geschuetzten Pfad
- 403 von `/auth/me` zeigt keinen erwarteten Error-State
- 403 zeigt dadurch auch den Retry-/No-Retry-Pfad nicht wie erwartet

Lokale Hypothese:

Die echten Browser-Snapshots landen auf der Login-Seite, waehrend die Specs den ProtectedRoute-Error-State erwarten. Das deutet primaer auf eine Zustandsdiskrepanz zwischen `AuthContext`, `ProtectedRoute` und den E2E-Fixtures hin, nicht auf ein fehlendes `ErrorState`-Rendering an sich.

Besitzender Code:

- `frontend/src/auth/AuthContext.jsx`
- `frontend/src/app/routes.jsx`
- `frontend/tests/gui_truth/test_02_auth_bootstrap.spec.js`

Billigster Gegencheck:

- Nur Szenario 05/07 erneut laufen lassen und Request-/Storage-Zustand um `/auth/me` herum protokollieren.

### Cluster 2: Shell-/Route-Remount-Instabilitaet

Prioritaet: `P2`

Betroffene Flows:

- Logout-Klicks mit `element is not stable` / `detached`
- Upload-, Search-, Chat-, Lifecycle- und Admin-Nav-Klicks mit denselben Symptomen
- einzelne Workspace-Bootstrap-Flows mit fehlendem persistentem Shell-Target

Lokale Hypothese:

Die Mehrheit der roten GUI-Flows teilt dasselbe Playwright-Symptom: Ziel-Elemente werden beim Klicken oder Fuellen ausgetauscht. Das sieht nach einem gemeinsamen Remount- oder Navigationseffekt aus, nicht nach isolierten Fachfehlern pro Seite.

Besitzender Code:

- `frontend/src/app/AppShell.jsx`
- `frontend/src/auth/AuthContext.jsx`
- `frontend/src/pages/DocumentsPage.jsx`
- `frontend/tests/gui_truth/fixtures.js`

Billigster Gegencheck:

- Einen Logout- und einen Search-Flow mit Trace laufen lassen und pruefen, ob AppShell oder die Route-Subtree zwischen Locator-Aufloesung und Action neu gemountet werden.

### Cluster 3: UI-Contract-Drift in Chat/Diagnostics/Upload

Prioritaet: `P3`

Betroffene Flows:

- erwartete Upload-Form-Signale nicht sichtbar
- Chat-Heading/Composer nicht wie im Spec gefunden
- Diagnostics-Karten mit `Systemstatus`, `DB Status`, `Migration Status` nicht wie erwartet sichtbar

Lokale Hypothese:

Ein kleinerer Teil der roten Flows sieht nach direktem Text-/Label- oder Render-Drift zwischen den realen Pages und den Truth-Specs aus. Dieser Cluster ist wahrscheinlich echt, aber sekundaer zum Shell-/Bootstrap-Problem.

## Backend Truth

Ausgangslage:

- `138 collected`
- `120 passed`
- `16 failed`
- `2 errors`
- Quelle: `reports/postgres_truth_report.json`

### Cluster 1: Entropy-Helper oder Metric-Model Breakage

Prioritaet: `P1`

Betroffene Tests:

- Orphan Growth
- Citation Degradation
- Multi-Epoch Entropy Simulation
- Drift Trend Structure

Lokale Hypothese:

Die Haeuufung in `test_entropy_truth.py` spricht stark fuer einen gemeinsamen Bruch in `entropy_helpers.py`, der Metrikerhebung oder den aktuellen Seeding-/Repair-Annahmen. Das ist eher ein Slice-Defekt als sieben unabhaengige Fehler.

Besitzender Code:

- `backend/tests/postgres_truth/test_entropy_truth.py`
- `backend/tests/postgres_truth/entropy_helpers.py`

Billigster Gegencheck:

- `test_entropy_truth.py -x` laufen lassen und den ersten Stacktrace als Primaeranker verwenden.

### Cluster 2: Queue Drift und Dead-Letter Recovery

Prioritaet: `P2`

Betroffene Tests:

- retryable jobs accumulate and are detected
- dead-letter accumulation is detected
- draining jobs reduces backlog
- stale import retry recovery without duplicate rows

Lokale Hypothese:

Diese Gruppe zeigt einen zusammenhaengenden Defekt rund um Job-Lifecycle, Retry-/Dead-Letter-Zaehllogik oder Queue-Recovery-Semantik.

Besitzender Code:

- `app/services/jobs/background_jobs.py`
- `backend/tests/postgres_truth/test_entropy_truth.py`
- `backend/tests/postgres_truth/test_m4_truth_flows.py`

### Cluster 3: Retrieval- und Stale-Index-Repair Divergenz

Prioritaet: `P3`

Betroffene Tests:

- searchability drift reduces coverage
- retrieval repair restores coverage
- stale index grows when archive skips repair
- stale index cleared by repair pass
- restore cycle does not create stale entries

Lokale Hypothese:

Der Golden Retrieval Benchmark ist gruen, aber die niedrigere Entropy-/Repair-Schicht ist rot. Das spricht fuer eine Divergenz zwischen qualitativem Benchmark und DB-/Repair-Semantik bei `is_searchable`, Lifecycle und Reindex.

Besitzender Code:

- `app/services/search_index_service.py`
- `app/services/search_service.py`
- `backend/tests/postgres_truth/test_entropy_truth.py`

## Empfohlene Reihenfolge

1. Frontend: nur Auth-Bootstrap Szenario 05/07 isolieren, bis klar ist, warum Login statt Error-State erscheint.
2. Frontend: danach Shell-/Route-Remount fuer Logout/Search/Nav analysieren, weil dieser Cluster die meisten GUI-Fails erklaert.
3. Backend: `test_entropy_truth.py -x` als primaeren Root-Cause-Run ausfuehren.
4. Backend: Queue-Drift und Stale-Index/Retrieval danach als getrennte Stabilitaetsslices reparieren.

## Kurzfazit

Die Lage ist enger als die nackten Fail-Zaehler vermuten lassen.

- Frontend: nicht 22 unabhängige Defekte, sondern primaer ein Bootstrap-/Shell-Stabilitaetsproblem plus kleiner UI-Contract-Drift.
- Backend: nicht ein genereller M4-Kollaps, sondern ein konzentrierter Entropy-/Stabilitaetsbruch oberhalb eines weiterhin starken M4a/M4b/M4c-Kerns.