# M4 Gap- und Risikoanalyse: Feature vs. Produktionsreife

Stand: 2026-05-11
Grundlage: Code-Analyse, postgres_truth-Lauf (33/33), Completion Matrix.

---

## 1. Differenzliste — Feature vorhanden, aber nicht truth-validiert

Für jeden Eintrag: Feature-Status, Truth-Status, konkreter Code-Beleg, Lückentyp.

| # | Bereich | Feature | Truth | Lückentyp |
|---|---|---|---|---|
| D1 | Parallele Duplicate-Imports | 80% | — | Race Condition, fehlender Test |
| D2 | LLM-Provider in Produktion | 75% | — | Fehlende Implementierung, Orphaned State |
| D3 | Token-Revocation / Logout | 70% | — | fehlende Recovery, unsichere Auth |
| D4 | Stale-Job-Recovery (Startup) | 80% | — | fehlende Recovery, Datenverlust-Risiko |
| D5 | Search-Index-Reparatur | 85% | — | operativ nicht reparierbarer Zustand |
| D6 | m4d_gate-Marker fehlt | 85% | 15% | fehlende Tests |
| D7 | Frontend-Auth E2E | 80% | 0% | fehlende Tests, unklare Doku |
| D8 | Chat-Retrieval nach Lifecycle | 80% | 40% | fehlender End-to-End-Test |
| D9 | CORS-Konfiguration produktiv | 85% | — | unklare Doku, kein Deployment-Gate |
| D10 | OCR-Fehlerhandling sichtbar | 85% | 50% | unklare Doku (korrekt implementiert, aber undokumentiert) |

### D1 — Parallele Duplicate-Imports

```
backend/tests/integration/test_documents_import.py:1
  test_parallel_duplicate_imports_create_single_document

→ Liegt in tests/integration/, nicht tests/postgres_truth/
→ Kein @pytest.mark.m4b_gate
→ Wird geskippt wenn TEST_DATABASE_URL nicht gesetzt
→ Ist NICHT im postgres_truth-Lauf enthalten
```

Advisory-Lock ist implementiert (`import_persistence_service.py:74`), aber der einzige Test
dafür läuft nicht als Pflichtgate. Das Mechanismus-Vertrauen fehlt ohne grünen PostgreSQL-Nachweis.

### D2 — LLM-Provider in Produktion

```python
# chat.py:39-41
class UnconfiguredLlmProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("LLM provider is not configured")
```

Jede Produktion-Chat-Anfrage, die den LLM-Aufruf erreicht, scheitert mit `LlmUnavailableApiError`.
Kritisch: Die Benutzerfrage wird VOR dem LLM-Aufruf persistiert (`rag_chat_service.py:100`):

```python
self._require_session_in_workspace(...)
self._save_user_question(...)         # ← user message already written
answer = self._generate_answer(...)   # ← fails here
```

Resultat: Jede Chat-Sitzung enthält User-Messages ohne Antwort.
Das ist keine stille Fehlfunktion, sondern ein dauerhaft inkonsistenter Session-Zustand.

### D3 — Token-Revocation / Logout

```python
# auth.py:104
if auth_session is None or auth_session.revoked_at is not None ...
```

`auth_session.revoked_at` wird niemals im produktiven Code gesetzt. Kein
`POST /api/v1/auth/logout` Endpoint existiert. Tokens sind für 12 Stunden gültig und
können weder vom Client noch vom Server vorzeitig invalidiert werden.

### D4 — Stale-Job-Recovery beim Start

```python
# background_jobs.py:190
def recover_stale_jobs(self, *, worker_id: str, ...) -> int: ...
```

`recover_stale_jobs` ist implementiert, aber wird nirgendwo automatisch aufgerufen.
`main.py` hat weder `@app.on_event("startup")` noch `lifespan`. Wenn der Backend-Prozess
während eines laufenden Import-Jobs abstürzt, bleibt der Job im Status `pending` mit abgelaufenem
Lock — bis ein Operator manuell `recover_stale_jobs` triggert oder den Job replayed.

Nach `background_job_max_attempts = 3` (config.py:16) wechselt der Job in `dead_letter`.
Dead-Letter-Jobs erfordern explizit `POST /api/v1/admin/jobs/{job_id}/replay`.

### D5 — Search-Index-Reparatur nicht möglich

```python
# admin.py:73
@router.post("/search-index/rebuild", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def rebuild_search_index(...):
    raise AdminActionNotImplementedApiError(...)
```

Die Diagnostics-API erkennt Index-Drift korrekt (`diagnostics.py:153-154`):
```python
((Document.lifecycle_status != "active") & Chunk.is_searchable.is_(True))
| ((Document.lifecycle_status == "active") & Chunk.is_searchable.is_(False))
```

Aber wenn Drift diagnostiziert wird, gibt es keinen operativen Reparaturpfad.

### D6 — m4d_gate-Marker fehlt

15 qualitativ gute Diagnostics-Tests existieren in `test_admin_diagnostics_api.py` und
`test_admin_search_index_api.py`, aber keiner trägt `@pytest.mark.m4d_gate`.
Der Validator meldet `gate_scores.m4d_gate = null` — kein Gate-Score berechenbar.

### D7 — Frontend-Auth E2E

```javascript
// routes.jsx:15-22
const { token, isAuthReady, bootstrapError } = useAuth();
if (!token) {
  return <Navigate replace to="/login" state={{ from: location }} />;
```

Route Guard ist vorhanden. Aber: Kein Frontend-CI-Lauf, kein Vitest-Pipeline. Der
`AuthBootstrap.test.jsx` testet den Bootstrap-Flow, aber kein Test verifiziert den
vollständigen Login→Token→Request→Redirect-Zyklus gegen die echte API.

### D8 — Chat-Retrieval nach Lifecycle-Transition

Die Lifecycle-Transition ist korrekt implementiert (lifecycle_status + is_searchable
werden atomar committed), und die Search-Query filtert auf `lifecycle_status == "active"`.
Aber kein postgres_truth-Test verifiziert den vollständigen Pfad:

```
archiviere Dokument → sende neue Chat-Anfrage → erwarte: kein Hit aus archiviertem Chunk
```

Die m4c_gate-Tests decken Search-Drift und Citation-Status ab, aber nicht den
expliziten "kein neuer Chat-Hit nach Archive"-Beweis.

### D9 — CORS nur für localhost konfiguriert

```python
# main.py:17-28
allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", ...]
```

Acht localhost-Varianten sind erlaubt, kein Produktions-Origin. Kein automatischer
Test prüft CORS-Konfiguration. Bei Deployment würde jede echte Domain blockiert.

### D10 — OCR-Fehlerhandling

```python
# import_service.py:45-50
if extracted.ocr_required:
    if self._ocr_engine is None:
        ImportError(code="ocr_failed", ...)
```

Die Implementierung ist korrekt — fehlende OCR-Engine erzeugt explizite `ImportError`.
Lücke: Dies ist in keiner Doku erwähnt. Nutzer erhalten `ocr_failed` ohne Hinweis darauf,
dass OCR prinzipiell nicht verfügbar ist.

---

## 2. Risikomatrix

Bewertung: **Schwere** (Datenverlust/Sicherheit/Korrektheit) × **Eintrittswahrscheinlichkeit** = **Priorität**

| Priorität | Risiko | Kategorie | Schwere | Eintrittsw. | Belegt durch |
|---|---|---|---|---|---|
| **P1** | Stale-Jobs bleiben ohne manuelle Intervention stuck | fehlende Recovery | Hoch | Hoch | `main.py:1-35`, `background_jobs.py:190` |
| **P2** | Orphaned User-Messages bei LLM-Fehler | Datenkonsistenz | Mittel | Sicher | `rag_chat_service.py:99-130`, `chat.py:61` |
| **P3** | Token läuft nicht ab bei Logout (kein Logout) | unsichere Auth | Mittel | Hoch | `auth.py:88`, kein Logout-Endpoint |
| **P4** | Race Condition Duplicate-Import unbewiesen | Race Condition | Mittel | Möglich | `test_documents_import.py:1` fehlt in Truth |
| **P5** | Search-Index-Drift ohne Reparaturpfad | operativ nicht reparierbar | Mittel | Möglich | `admin.py:73` (501) |
| **P6** | Falsche RAG-Antwort durch fehlende Lifecycle-Garantie | falsche RAG-Antwort | Mittel | Möglich | kein m4c-Chat-Archive-Test |
| **P7** | Cross-Workspace Leak via Header-Manipulation | Cross-Workspace Leak | Hoch | Gering | `auth.py:113-120` (Membership-Check vorhanden) |
| **P8** | m4d_gate fehlt: Diagnostics ohne Gate-Score | fehlende Tests | Niedrig | Sicher | Validator: gate_scores.m4d_gate = null |
| **P9** | CORS blockiert Produktion | unklare Doku | Mittel | Sicher bei Deployment | `main.py:16-29` |
| **P10** | Frontend-Auth E2E ungetestet | fehlende Tests | Niedrig | Möglich | kein Frontend-CI |

### Risikodetails

**P1 — Stale-Jobs (Datenverlust-Risiko):**
Kein automatisches Job-Recovery beim Start. Ein Prozess-Crash während des Imports lässt
das Dokument in `pending` oder `retryable`. Der Nutzer sieht einen hängenden Job. Nach 3
Versuchen: `dead_letter` — Dokument faktisch verloren bis Operator eingreift.
Kein Alarm, kein Auto-Recovery, kein Monitoring-Endpoint dafür.

**P2 — Orphaned User-Messages:**
In jeder Produktions-Chat-Session, die LLM-Generierung erreicht, wird die Benutzerfrage
persistiert, die Antwort schlägt fehl. Session-Zustand: 1 User-Message, 0 Antworten.
Dauer: bis LLM-Provider konfiguriert wird. Alle bisherigen Test-Sessions sind betroffen.
Diese Inkonsistenz ist nicht selbstheilend.

**P3 — Token ohne Revoke:**
12-Stunden-Fenster nach kompromittiertem Token. Betrifft alle Multi-User-Szenarien.
Logout existiert nur im Frontend (Token wird aus localStorage gelöscht), nicht im Backend.
Token bleibt serverseitig gültig.

**P4 — Race Condition unbewiesen:**
Advisory-Lock-Mechanismus ist korrekt implementiert, aber der einzige Test dafür liegt
außerhalb von postgres_truth und wird in CI geskippt. Unter Last könnten doppelte
Dokumente entstehen wenn der Lock nicht greift.

**P5 — Search-Index nicht reparierbar:**
Diagnostics zeigt Drift → Operator kann Drift sehen, aber nicht beheben (501).
Einziger Ausweg: direktes DB-Update, was undokumentiert und unsupported ist.

**P6 — Falsche RAG-Antwort:**
Wenn ein Dokument archiviert wird und kurz danach eine Chat-Session aktiv ist: die neue
Frage sollte keinen Hit aus dem archivierten Dokument bekommen. Architektonisch korrekt
implementiert (lifecycle_status-Filter), aber der konkrete E2E-Pfad ist nie auf echter
PostgreSQL-DB durchlaufen worden.

**P7 — Cross-Workspace Leak:**
`AuthService.authenticate()` validiert `WorkspaceMembership` für jede Anfrage. Ein
Angreifer mit gültigem Token kann `x-workspace-id` einer anderen Workspace senden und
bekommt 403 (Membership-Check schlägt fehl). Architektonisch korrekt. Residualrisiko:
SQL-Fehler oder NULL-Membership-Bug. Gut durch m4a_gate-Tests abgedeckt.

---

## 3. Fix-Reihenfolge

Sortiert nach: P1=sofort, P2=vor ersten Nutzern, P3=vor Production-Deployment.

### Schritt 1 — Sofortmaßnahmen (blocking für M4 Stabilization Gate)

**Fix S1: Stale-Job-Recovery bei Startup aktivieren** (P1)
```python
# main.py — lifespan hinzufügen
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    _recover_stale_jobs_on_startup()
    yield

def _recover_stale_jobs_on_startup() -> None:
    with Session(get_engine()) as session:
        service = BackgroundJobService(session)
        recovered = service.recover_stale_jobs(worker_id="startup-recovery")
        if recovered:
            log_event("startup_job_recovery", recovered=recovered)
```
Aufwand: 1h. Schließt P1.

**Fix S2: Logout-Endpoint implementieren** (P3)
```python
# auth.py — auth_session.revoked_at setzen
def revoke_session(self, *, bearer_token: str) -> None:
    ...
    auth_session.revoked_at = datetime.now(UTC)
    self._session.commit()

# auth.py (API) — POST /auth/logout hinzufügen
@router.post("/logout", status_code=204)
def logout(request: Request, service: AuthService = Depends()):
    bearer = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    service.revoke_session(bearer_token=bearer)
```
Aufwand: 2h. Schließt P3. Kein Breaking Change.

**Fix S3: Race-Test nach postgres_truth verschieben** (P4)
```
backend/tests/integration/test_documents_import.py
→ backend/tests/postgres_truth/test_m4b_parallel_import_truth.py

Marker: @pytest.mark.postgres_truth, @pytest.mark.m4b_gate
```
Aufwand: 1h. Schließt D1, schließt RC-Blocker "Race Condition".

**Fix S4: @pytest.mark.m4d_gate auf Diagnostics-Tests setzen** (P8)
```python
# test_admin_diagnostics_api.py — auf mindestens 3 Tests:
@pytest.mark.m4d_gate
def test_admin_diagnostics_returns_read_only_summary(...)
@pytest.mark.m4d_gate
def test_admin_diagnostics_rejects_foreign_workspace(...)
@pytest.mark.m4d_gate
def test_admin_search_index_rebuild_returns_stable_shape(...)
```
Aufwand: 30min. Schließt D6. Gate-Score m4d sofort auswertbar.

**Fix S5: Chat-Archive-E2E als postgres_truth-Test** (P6)
```python
# tests/postgres_truth/test_m4_truth_flows.py — neuer Test:
@pytest.mark.postgres_truth
@pytest.mark.m4c_gate
def test_archived_document_excluded_from_new_chat_retrieval(truth_session, truth_ids):
    # archive document → create new chat message → assert no citation from archived doc
    ...
```
Aufwand: 3h. Schließt D8. RC-Blocker "source_status Inkonsistenz" stärker belegt.

### Schritt 2 — Vor ersten Nutzern (blocking für M4-Release)

**Fix M1: UnconfiguredLlmProvider durch expliziten 503 ersetzen** (P2)
```python
# chat.py
class UnconfiguredLlmProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise LlmUnavailableApiError(message="LLM provider not configured in this deployment")
```
Und: `_save_user_question` NACH dem Kontext-Check verschieben, damit keine Orphaned
Messages entstehen wenn LLM nicht verfügbar ist.
Aufwand: 2h. Schließt P2.

**Fix M2: CORS-Konfiguration aus ENV lesen** (P9)
```python
# config.py
cors_allowed_origins: list[str] = ["http://localhost:5173"]

# main.py
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_allowed_origins)
```
Aufwand: 1h. Schließt P9.

### Schritt 3 — Vor Produktions-Deployment

**Fix L1: Search-Index-Rebuild implementieren** (P5)
POST /search-index/rebuild von 501 auf echte Implementierung migrieren,
nachdem M4a+M4b+M4c Gates grün sind.
Aufwand: 1 Tag.

**Fix L2: Frontend CI + E2E Auth-Test** (P10)
Vitest in CI-Pipeline, `AuthBootstrap.test.jsx` auf Login→Redirect-E2E ausweiten.
Aufwand: 4h.

---

## Gesamtbewertung

| Metrik | Wert | Quelle |
|---|---|---|
| Feature-Fortschritt | ~80% | Completion Matrix |
| Produktionsreife | ~60% | Gate-fähig-Wert |
| Differenz | **-20%** | strukturell |
| Sofort-Fixes (S1–S5) | ~5 Arbeitstage | Schätzung |
| Gate = PASS nach S1–S5 | möglich | vorausgesetzt DB verfügbar |

Die 20-Punkte-Lücke ist nicht durch Implementierungsfehler entstanden, sondern durch:
1. **Fehlende Infrastruktur** (kein CI-PostgreSQL, kein Startup-Recovery)
2. **Fehlende Marker** (m4d_gate nie gesetzt)
3. **Fehlende Testpfade** (Race-Test außerhalb postgres_truth, kein Chat-Archive-E2E)
4. **Design-Schulden** (LLM-Provider als RuntimeError statt 503, kein Logout-Endpoint)

Keiner dieser Punkte ist ein fundamentales Architekturproblem. Alle sind in < 2 Wochen schließbar.
