# Architekturreview — PRI-7

Stand: 2026-06-17
Scope: Frontend, Backend, Datenmodell, API Design, Provider Integration, Export Pipeline, Analyse Pipeline, Dashboard, Testarchitektur, Dokumentation

---

## 1. Frontend Architektur

**Struktur:** `api/` → `features/` → `pages/` → `components/`. Klare Layering, Hooks in Features.

**Stärken:**
- API-Layer vollständig separiert (`api/*.js`)
- Feature-Hooks (`useAnalysis.js`, `useExport.js`, `useDocumentCenter.js`) kapseln State
- `ErrorBoundary`, `ErrorState`, `LoadingState` konsistent verwendet
- `AdminRoute`-Guard korrekt implementiert (PRI-6)

**Probleme:**
- `DriftWidgetPanel.jsx` (465 Zeilen) — Große Komponente. 6 Widget-Typen + Datenabruf in einer Datei. → TD-008
- **Zwei parallele Drift-Implementierungen:** `features/dashboard/DriftWidgetPanel.jsx` UND `features/drift_v2/DriftDashboard.jsx` — unterschiedliche State-Modelle, partiell doppelter Code. → TD-009
- `TopicsWidgetPanel.jsx` (325 Zeilen) — SVG-Chart-Code inline, nicht extrahiert.
- Kein React Query / SWR — jeder Page-Mount triggert neue API-Calls; kein Deduplication, kein Stale-while-revalidate.

---

## 2. Backend Architektur

**Struktur:** FastAPI → `api/v1/*.py` → `services/` → `repositories/` → `models/`. Korrekte Schichtung.

**Stärken:**
- Repository-Pattern konsequent durchgezogen (DocumentRepository, SearchRepository, etc.)
- Pydantic Schemas für alle API-Grenzen
- Advisory Lock Service für konkurrierende Job-Claims
- Observability-Modul vorhanden (`observability/middleware.py`, `logging.py`, `drift_metrics.py`)

**Probleme:**
- **Zwei Import-Pfade** (TD-005): `import_service.py` + `services/importing/pipeline.py` + `services/documents/import_executor.py` — unklar welcher kanonisch ist.
- `backup_restore.py` (693 Zeilen) — God Service (TD-006).
- `diagnostics.py` (528 Zeilen) — God Service (TD-007).
- Kein einheitliches Job-Interface (TD-015) — drei separate Job-Systeme.

---

## 3. Datenmodell

**Modelle:** Workspace → User → WorkspaceMembership → Document → DocumentVersion → Chunk → AnalysisJob → AnalysisResult → Topic → Export → DriftRun.

**Stärken:**
- Workspace-Isolation auf allen Modellen (`workspace_id` vorhanden)
- CheckConstraints für Status-Enums direkt im Schema
- TSVECTOR-Spalte auf Chunks für FTS

**Probleme:**
- **Kein GIN-Index** auf `chunks.search_vector` (TD-004) — FTS läuft ohne Indexnutzung.
- `AnalysisJob` lazy-loaded Relationships (TD-003) — N+1 bei Job-Listings.
- `documents.tags`-Tabelle via Raw SQL im DashboardService — kein ORM-Modell. Inkonsistenz.
- Kein `updated_at`-Index auf Topics/Chunks für inkrementelle Sync-Queries.

---

## 4. API Design

**Standard:** REST + JSON, konsistente Fehlercodes via `ApiError`-Hierarchie, workspace_id als Kontext.

**Stärken:**
- Einheitliche Error-Handler (`api/error_handlers.py`)
- Konsequente `workspace_id`-Filterung in allen Queries
- Audit-Trail-Endpunkt vorhanden (`/api/v1/audit`)

**Probleme:**
- **Keine Cursor-Pagination** (TD-011) — nur limit/offset. Skaliert nicht über 50k Einträge.
- `analysis.py` (457 Zeilen) und `export.py` (454 Zeilen) — Tendenz zu dicken Routen-Dateien.
- Kein API-Versioning-Header (`Accept: application/vnd.ruflo.v1+json`).
- Kein standardisiertes Antwort-Envelope für Listen (`{"data": [...], "meta": {...}}`).

---

## 5. Provider Integration

**Implementierte Provider:** OpenAI, Gemini, Ollama (via `ai_providers/`). Registry-Pattern. Base-Interface.

**Stärken:**
- `ProviderRegistry` mit dynamic loading
- Provider-spezifische Fehlertypen (`ai_providers/errors.py`)
- Fallback auf Stub-Engine (`analysis_stub_engine.py`) für Tests

**Probleme:**
- Kein Timeout/Circuit-Breaker für Provider-Calls — hängende Requests blockieren Worker.
- Kein Health-Check-Endpoint pro Provider.
- `ki_provider.py` (Top-Level) neben `ai_providers/` — welcher ist kanonisch?

---

## 6. Export Pipeline

**Flow:** ExportJob → ExportService → ExportRenderer (Markdown/JSON/PDF) → File-System.

**Stärken:**
- ExportRenderer als Protocol (austauschbar)
- Klare Status-Transitions (QUEUED → RUNNING → COMPLETED/FAILED)
- Only-APPROVED-Guard korrekt implementiert

**Probleme:**
- PDF-Export nur als Dry-Run (RCL-EXP-01) — kein produktiver PDF-Renderer.
- Keine Export-Job-Cleanup-Logik — abgelaufene Export-Files akkumulieren im FS.
- Kein Progress-Event für lange Exports (nur pending/running/completed).

---

## 7. Analyse Pipeline

**Flow:** CreateJob → AnalysisJobService → AnalysisProvider (KI/Stub) → AnalysisResult → ApprovalService → TopicImportService.

**Stärken:**
- PROHIBIT-08 strikt implementiert (kein Auto-Approve)
- ApprovalPolicy trennt Berechtigung von Business-Logik
- Retry-Limit (RETRY_LIMIT=2) hardcoded

**Probleme:**
- `RETRY_LIMIT = 2` hardcoded statt konfigurierbar (settings).
- Keine Dead-Letter-Queue für dauerhaft fehlgeschlagene Jobs.
- Kein Timeout auf KI-Provider-Calls (blockiert Thread unbegrenzt).

---

## 8. Dashboard

**Implementiert:** Summary-Widgets, Import-Liste, Drift-Status, Topics-Widgets, Quality-Score.

**Stärken:**
- Workspace-scoped alle Queries
- Drift-Status aus DriftRun-Tabelle (kein direkter Zugriff)

**Probleme:**
- 5 separate Queries für ActivityFeed — kein UNION ALL (TD-002).
- `tags`-Raw-SQL statt ORM.
- Kein Caching (TD-010) — jeder Reload triggert 8+ Queries.
- W06 Drift-Summary-Widget fehlt (GA-UX-01).

---

## 9. Testarchitektur

**Stand:** Contract-Tests, Unit-Tests, Regression-Tests für GP-Flows. AdminRouteGuard-Test neu (PRI-6).

**Stärken:**
- Contract-Tests mit definierten Matchers (`analysis-api-contract.md`)
- AdminRouteGuard mit 3 Regression-Cases
- Data Quality Tests vorhanden

**Probleme:**
- Keine Integration-Tests gegen echte DB (SCGB-01 external).
- Keine Performance-Tests (Last, p95-Latenz unter Load).
- Keine Accessibility-Tests (WCAG 2.1 AA nicht validiert).
- Test-Coverage-Report nicht als CI-Gate konfiguriert.

---

## 10. Dokumentation

**Stand:** 150+ Markdown-Dateien, strukturierte JSON-Reports, ADRs, Runbooks.

**Stärken:**
- Maschinenlesbare Gate-Reports als Wahrheitsquelle
- ADR-Format vorhanden (`docs/adr/`)
- Runbooks für 8 Fehlerszenarien

**Probleme:**
- API-Dokumentation (`docs/api.md`) nicht synchron mit aktuellem OpenAPI-Schema.
- Keine automatische Doku-Generierung (kein Sphinx/mkdocs).
- `docs/` Verzeichnis mit 150+ Dateien ohne klare Navigations-Hierarchie.

---

## Priorisierte Handlungsempfehlungen

| Priorität | ID | Maßnahme | Aufwand |
|-----------|-----|----------|---------|
| 1 | TD-004 | GIN-Index auf search_vector | XS |
| 1 | TD-013 | CSP-Header implementieren | S |
| 2 | TD-001 | Unified Search: DB-seitige Pagination | M |
| 2 | TD-011 | Cursor Pagination API | L |
| 3 | TD-002 | Dashboard Activity: UNION ALL | S |
| 3 | TD-003 | AnalysisJob lazy-load → selectinload | S |
| 3 | TD-012 | Topic-Tag N+1 | S |
| 4 | TD-010 | Response Caching | L |
| 5 | TD-015 | Einheitliches Job-Interface | XL |

Vollständiges Register: `reports/current/technical_debt_register.json`
