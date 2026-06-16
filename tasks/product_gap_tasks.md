# Product Gap Sprint — Task List

**Sprint:** Endanwender-Vollständigkeit  
**Zeitraum:** 1 Woche (Solo)  
**Status-Legende:** `[ ]` offen · `[~]` in Arbeit · `[x]` erledigt · `[!]` geblockt

---

## Tag 1 — Infrastruktur-Blocker

### T01 — TEST_DATABASE_URL setzen
- **Datei:** `.env.test`
- **Änderung:** `TEST_DATABASE_URL=postgresql://...` eintragen
- **Aufwand:** 15 min
- **Verifizierung:** `pytest --co -q` sammelt Tests ohne "no module" Fehler
- **Status:** `[ ]`

### T02 — RCB-001: NAV_ITEMS /chat statt /search
- **Datei:** `frontend/src/components/AppShell.jsx`
- **Änderung:** NAV-Eintrag `path: '/search'` → `path: '/chat'`, Label anpassen
- **Aufwand:** 30 min
- **Verifizierung:** Browser: Suche-Link führt zu /chat
- **Status:** `[ ]`

### T03 — RCB-002: NAV_ITEMS mit Masterplan synchronisieren
- **Datei:** `frontend/src/components/AppShell.jsx`
- **Änderung:** /data-quality in NAV aufnehmen; /topics + /import aus NAV entfernen oder Masterplan-Entscheidung PO einholen
- **Aufwand:** 45 min
- **Abhängigkeit:** PO-Entscheidung zu NAV_ITEMS
- **Status:** `[ ]`

### T04 — RCB-003: AdminRoute-Guard für /admin/diagnostics
- **Datei:** `frontend/src/router/routes.jsx`
- **Änderung:** Route `/admin/diagnostics` in `<AdminRoute>` wrappen
- **Aufwand:** 30 min
- **Verifizierung:** Als member eingeloggt → /admin öffnet → Redirect zu /dashboard
- **Status:** `[ ]`

### T05 — AGAP-02: Migration 'cancelled' Status
- **Datei:** `backend/migrations/versions/[DATUM]_analysis_cancelled_status.py` (NEU)
- **Änderung:** CheckConstraint auf analysis_jobs.status um 'cancelled' erweitern
- **SQL:** `ALTER TABLE analysis_jobs DROP CONSTRAINT ck_analysis_jobs_status; ALTER TABLE analysis_jobs ADD CONSTRAINT ... CHECK (status IN ('pending','running','completed','failed','approved','cancelled'));`
- **Aufwand:** 30 min
- **Status:** `[ ]`

### T06 — AGAP-02: cancel_job() Service-Methode
- **Datei:** `backend/app/services/analysis/service.py`
- **Änderung:** `cancel_job(job_id, workspace_id)` — Transition pending|running → cancelled; completed|approved → InvalidStateError; cancelled → idempotent 200
- **Aufwand:** 30 min
- **Abhängigkeit:** T05
- **Status:** `[ ]`

### T07 — AGAP-02: POST /analysis/jobs/:id/cancel Endpunkt
- **Datei:** `backend/app/api/v1/analysis.py`
- **Änderung:** Endpunkt mit require_workspace_member; ruft cancel_job() auf
- **Aufwand:** 20 min
- **Abhängigkeit:** T06
- **Status:** `[ ]`

### T08 — AGAP-06: AuditRecorder-Injection
- **Datei:** `backend/app/api/v1/analysis.py`
- **Änderung:** `get_analysis_service()` — approval_audit_recorder nicht None; AuditRecorder-Instanz übergeben
- **Aufwand:** 20 min
- **Status:** `[ ]`

---

## Tag 2 — Topics Backend

### T09 — P1-GAP-01: Category, Tag, DocumentTag ORM-Models
- **Datei:** `backend/app/models/categories.py` (NEU)
- **Inhalt:** SQLAlchemy-Models für categories, tags, document_tags; Relationships zu Document und Workspace
- **Aufwand:** 60 min
- **Verifizierung:** `from app.models.categories import Tag` ohne ImportError
- **Status:** `[ ]`

### T10 — P1-GAP-01: Document-Relationship ergänzen
- **Datei:** `backend/app/models/document.py`
- **Änderung:** `tags = relationship("Tag", secondary="document_tags", backref="documents")`
- **Aufwand:** 15 min
- **Abhängigkeit:** T09
- **Status:** `[ ]`

### T11 — P1-GAP-02: Topics Schemas
- **Datei:** `backend/app/schemas/topics.py` (NEU)
- **Inhalt:** TopicItem, TopicDetailItem, TopicListResponse, TagItem, DocumentTagRequest
- **Aufwand:** 30 min
- **Status:** `[ ]`

### T12 — P1-GAP-02: GET /api/v1/topics (Liste)
- **Datei:** `backend/app/api/v1/topics.py` (NEU)
- **Inhalt:** Aggregation aus analysis_results.suggested_topics (JSONB) gruppiert nach name; workspace-scoped; paginiert
- **Aufwand:** 60 min
- **Abhängigkeit:** T09, T11
- **Status:** `[ ]`

### T13 — P1-GAP-02: GET /api/v1/topics/:id (Detail)
- **Datei:** `backend/app/api/v1/topics.py`
- **Inhalt:** Detail-Endpunkt mit sources[] (aus Analysis-Results), documents[] (Join über source_documents), tags[]
- **Aufwand:** 60 min
- **Abhängigkeit:** T12
- **Status:** `[ ]`

### T14 — P1-GAP-02: POST /api/v1/tags + POST /documents/:id/tags
- **Datei:** `backend/app/api/v1/topics.py`
- **Inhalt:** Tag erstellen (require_workspace_member); Tag einem Dokument zuordnen; DELETE /documents/:id/tags/:tag_id
- **Aufwand:** 45 min
- **Abhängigkeit:** T09, T11
- **Status:** `[ ]`

### T15 — Topics-Router registrieren
- **Datei:** `backend/app/api/v1/router.py`
- **Änderung:** `api_router.include_router(topics_router, prefix="/topics")`
- **Aufwand:** 10 min
- **Abhängigkeit:** T12
- **Status:** `[ ]`

### T16 — API-Tests Topics
- **Datei:** `backend/tests/api/v1/test_topics.py` (NEU)
- **Tests:** GET /topics leer, GET /topics mit Daten, GET /topics/:id 404, POST /tags, POST /documents/:id/tags
- **Aufwand:** 45 min
- **Abhängigkeit:** T15
- **Status:** `[ ]`

---

## Tag 3 — Topics Frontend + Ollama LLM-Binding

### T17 — Topics.js URL-Fix
- **Datei:** `frontend/src/api/topics.js`
- **Änderung:** Alle Pfade von `/topics/*` auf `/api/v1/topics/*` korrigieren
- **Aufwand:** 10 min
- **Status:** `[ ]`

### T18 — TopicsPage: Themenliste
- **Datei:** `frontend/src/pages/TopicsPage.jsx`
- **Inhalt:** Liste der Themen aus GET /api/v1/topics; Empty State; Loading Skeleton; Error State
- **Aufwand:** 60 min
- **Abhängigkeit:** T15, T17
- **Status:** `[ ]`

### T19 — TopicDetailPage: Detail-Ansicht
- **Datei:** `frontend/src/pages/TopicDetailPage.jsx`
- **Inhalt:** name, summary, sources[] als Quellen-Liste, documents[] als Dokument-Links, tags[] als Chips
- **Aufwand:** 60 min
- **Abhängigkeit:** T18
- **Status:** `[ ]`

### T20 — Ollama: Config-Felder
- **Datei:** `backend/app/core/config.py`
- **Änderung:** `llm_provider: str = ""`, `llm_model_name: str = "llama3"`, `llm_base_url: str = "http://localhost:11434"`
- **Aufwand:** 20 min
- **Status:** `[ ]`

### T21 — Ollama: LlmAnalysisProvider implementieren
- **Datei:** `backend/app/services/analysis/llm_provider.py` (NEU)
- **Inhalt:** Klasse implementiert AnalysisProvider-Interface; POST http://localhost:11434/api/generate; JSON-Prompt mit Dokument-Chunks; Response → AnalysisResult
- **Aufwand:** 90 min
- **Abhängigkeit:** T20
- **Status:** `[ ]`

### T22 — Ollama: get_analysis_service() Provider-Switch
- **Datei:** `backend/app/services/analysis/service.py`
- **Änderung:** Wenn `settings.llm_provider == "ollama"` → LlmAnalysisProvider; sonst Stub
- **Aufwand:** 20 min
- **Abhängigkeit:** T21
- **Status:** `[ ]`

### T23 — Chat: UnconfiguredLlmProvider → HTTP 503
- **Datei:** `backend/app/api/v1/chat.py`
- **Änderung:** RuntimeError durch HTTP 503 `{"error_code": "LLM_NOT_CONFIGURED"}` ersetzen
- **Aufwand:** 20 min
- **Status:** `[ ]`

### T24 — .env.example Ollama-Eintrag
- **Datei:** `.env.example`
- **Inhalt:** `LLM_PROVIDER=ollama`, `LLM_MODEL_NAME=llama3`, `LLM_BASE_URL=http://localhost:11434`
- **Aufwand:** 10 min
- **Status:** `[ ]`

---

## Tag 4 — AnalysisPage + Export MVP

### T25 — AnalysisPage.jsx: Job-Erstellung + Polling
- **Datei:** `frontend/src/pages/AnalysisPage.jsx` (NEU)
- **Inhalt:** Dokument-Multi-Select, Analyse-Typ-Auswahl, optionaler Prompt, Job starten, StatusBadge mit Polling (2s), terminal states stoppen Polling
- **Aufwand:** 75 min
- **Status:** `[ ]`

### T26 — AnalysisPage.jsx: Result-Anzeige + Approve + Cancel
- **Datei:** `frontend/src/pages/AnalysisPage.jsx`
- **Inhalt:** ResultPanel (summary, suggested_topics, suggested_tags), ApproveButton (nur workspace_admin), CancelButton (pending/running)
- **Aufwand:** 60 min
- **Abhängigkeit:** T25
- **Status:** `[ ]`

### T27 — Route /analysis registrieren
- **Datei:** `frontend/src/router/routes.jsx`
- **Änderung:** Route `/analysis` → `<AnalysisPage />`
- **Aufwand:** 10 min
- **Abhängigkeit:** T25
- **Status:** `[ ]`

### T28 — Export: Schema + ExportService (JSON)
- **Datei:** `backend/app/schemas/export.py` (NEU), `backend/app/services/export_service.py` (NEU)
- **Inhalt:** ExportRequest (source_type, source_id, format), JSON-Export für Dokument + Analyseergebnis mit source_references[]
- **Aufwand:** 45 min
- **Status:** `[ ]`

### T29 — Export: Markdown-Format
- **Datei:** `backend/app/services/export_service.py`
- **Inhalt:** Markdown-Template: # Titel, Meta-Block, Textinhalt-Sektionen, ## Quellen
- **Aufwand:** 45 min
- **Abhängigkeit:** T28
- **Status:** `[ ]`

### T30 — Export: Audit-Event + POST /export Endpunkt
- **Datei:** `backend/app/api/v1/export.py` (NEU)
- **Inhalt:** POST /api/v1/export → Workspace-Guard → ExportService → Binary-Stream-Response; Audit-Event loggen
- **Aufwand:** 35 min
- **Abhängigkeit:** T28, T29
- **Status:** `[ ]`

### T31 — Export-Router registrieren
- **Datei:** `backend/app/api/v1/router.py`
- **Änderung:** `api_router.include_router(export_router, prefix="/export")`
- **Aufwand:** 5 min
- **Abhängigkeit:** T30
- **Status:** `[ ]`

### T32 — ExportButton.jsx
- **Datei:** `frontend/src/components/ExportButton.jsx` (NEU)
- **Inhalt:** Format-Dropdown (JSON / Markdown), POST /api/v1/export, Browser-Download via Blob-URL
- **Aufwand:** 45 min
- **Abhängigkeit:** T31
- **Status:** `[ ]`

### T33 — ExportButton in AnalysisPage + DocumentDetailPage
- **Datei:** `frontend/src/pages/AnalysisPage.jsx`, `frontend/src/pages/DocumentDetailPage.jsx`
- **Aufwand:** 20 min
- **Abhängigkeit:** T32
- **Status:** `[ ]`

---

## Tag 5 — Dashboard W06 + E2E-Test

### T34 — Dashboard W06: DashboardDriftItem Schema + Service
- **Datei:** `backend/app/schemas/dashboard.py`, `backend/app/services/dashboard_service.py`
- **Inhalt:** DashboardDriftItem (latest_run_id, status, total_findings, critical_count, high_count, started_at); list_drift() mit SQL-Aggregation über drift_runs + drift_findings
- **Aufwand:** 60 min
- **Status:** `[ ]`

### T35 — Dashboard W06: GET /dashboard/drift Endpunkt
- **Datei:** `backend/app/api/v1/dashboard.py`
- **Aufwand:** 20 min
- **Abhängigkeit:** T34
- **Status:** `[ ]`

### T36 — Dashboard W06: DriftWidget.jsx
- **Datei:** `frontend/src/components/DriftWidget.jsx` (NEU)
- **Inhalt:** Severity-Chips (critical/high/medium), Run-Status-Badge, Link zu /drift, Empty/Error/Loading State; KEIN Repair/Cleanup-Button (PROHIBIT-02/06)
- **Aufwand:** 60 min
- **Abhängigkeit:** T35
- **Status:** `[ ]`

### T37 — DriftWidget in DashboardPage
- **Datei:** `frontend/src/pages/DashboardPage.jsx`
- **Aufwand:** 15 min
- **Abhängigkeit:** T36
- **Status:** `[ ]`

### T38 — Product E2E Truth Suite ausführen
- **Szenarien:** S01 Login → S02 Import → S03 Suche → S04 Thema → S05 Analyse → S06 Approve → S07 Export → S08 Logout
- **PASS-Kriterien:** Kein manueller Eingriff, keine Debug-Seite, keine Gate-Seite, keine technische ID sichtbar
- **Output:** `reports/current/product_e2e_truth_suite.json` aktualisieren
- **Aufwand:** 60 min
- **Abhängigkeit:** T01–T37
- **Status:** `[ ]`

### T39 — product_release_gate.json re-evaluieren
- **Datei:** `reports/current/product_release_gate.json`
- **Aufwand:** 30 min
- **Abhängigkeit:** T38
- **Status:** `[ ]`

---

## Reihenfolge-Übersicht (Abhängigkeitskette)

```
T01 (DB) → [T16 Tests]
T05 → T06 → T07 (Cancel)
T08 (AuditRecorder)
T09 → T10, T11
T11 + T09 → T12 → T13, T14
T12 → T15 → T16
T15 + T17 → T18 → T19
T20 → T21 → T22
T23, T24
T25 → T26 → T27
T28 → T29 → T30 → T31 → T32 → T33
T34 → T35 → T36 → T37
[T01..T37] → T38 → T39
```

---

## Nicht in diesem Sprint

- M5c Cleanup (PROHIBIT-06)
- Repair (PROHIBIT-02)
- Governance Automation
- Gate-Debug-Views
- Admin-Spezialseiten (/admin, /rag-center, /governance, /agents, /collaboration)
- PDF-Export (P2)
- Benutzerverwaltung per API (P2)
- Data Quality Trigger (P2)
- Semantic Search (P3)
