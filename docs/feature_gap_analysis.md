# Feature Gap Analyse — Ruflo

**Stand:** 2026-06-15 | **Methode:** Static Code Analysis
**Quellen:** masterplan.md, Entwicklung.md, frontend/src/app/routes.jsx, backend/app/api/, backend/app/models/, backend/migrations/

---

## Legende

| Status | Bedeutung |
|---|---|
| VOLLSTÄNDIG | DB + Backend + Frontend vorhanden und funktional |
| TEILWEISE | Mindestens eine Schicht fehlt oder ist Stub |
| VORBEREITET | Schema/Struktur vorhanden, keine Logik |
| NICHT_BEGONNEN | Kein Code, keine Migration, kein Endpunkt |

| Priorität | Bedeutung |
|---|---|
| P1 | Kernfunktion, Release-relevant |
| P2 | Wichtig für produktiven Betrieb, Post-RC |
| P3 | Nice-to-have, Post-1.0 |

---

## 1. Dokumente

**Priorität:** P1 | **Status:** VOLLSTÄNDIG

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | `documents`, `document_versions`, `document_chunks` (migrations 0001, 0002) |
| Backend | PASS | GET/POST/PATCH/DELETE `/documents`, Lifecycle (archive/delete/recover), Versioning, Chunk-Abruf |
| Frontend | PASS | `DocumentsPage.jsx`, `DocumentDetailPage.jsx`, `DocumentCenterPage.jsx` |
| Import-Pipeline | PASS | Datei-Upload, MIME-Erkennung, BackgroundJob-Tracking |

**Lücken:** keine P1-Lücken.

---

## 2. Import

**Priorität:** P1 | **Status:** VOLLSTÄNDIG

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | `background_jobs` (job_type: `document_import`) |
| Backend | PASS | POST `/documents` (file upload), `import_executor`, `import_recovery_service` |
| Frontend | PASS | `ImportCenterPage.jsx` |
| Recovery | PASS | `DocumentImportRecoveryService` — Konfliktbehandlung implementiert |

**Lücken:** keine P1-Lücken.

---

## 3. OCR

**Priorität:** P2 | **Status:** VORBEREITET

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | `document_versions.ocr_used` (bool), `ki_provider`, `ki_model` — Schema komplett |
| Backend | VORBEREITET | `parser_type_from_mime_type` in `import_executor` vorhanden; kein OCR-Service |
| Frontend | VORBEREITET | Import-Pipeline erkennt MIME-Typ; keine OCR-Feedback-Anzeige |
| OCR-Engine | NICHT_BEGONNEN | Kein `ocr_service.py`, kein Provider-Binding |

**Lücken:**
- `app/services/documents/ocr_service.py` fehlt
- OCR-Ergebnis-Feedback im Import-Status fehlt
- KI-Provider-Konfiguration (API-Key-Binding) fehlt

---

## 4. Suche

**Priorität:** P1 | **Status:** TEILWEISE

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | `document_chunks.search_vector` (TSVECTOR/TSVECTOR-Variant), Index vorhanden |
| Backend | PASS | GET `/search/chunks` — Volltext-Suche mit Workspace-Scope, Pagination, Observability |
| Frontend | PASS | `SearchPage.jsx`, `/rag` → `RAGCenterPage.jsx` |
| Semantische Suche | VORBEREITET | Schema-Feld vorhanden; kein Embedding-Service |
| Filter/Facetten | NICHT_BEGONNEN | `filters=None` hardcoded in `SearchService.search_chunks()` |

**Lücken:**
- Filter nach Dokument, Datum, Tag nicht implementiert (P2)
- Semantic/Vector Search: kein Embedding-Provider (P3)
- `/search` Route zeigt im Nav als `/chat`, laut RC Blocker RCB-001/S04

---

## 5. Themen (Topics)

**Priorität:** P1 | **Status:** TEILWEISE

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | `categories`, `tags`, `document_tags` (migration 0003) inkl. `confidence`, `source` |
| ORM-Model | NICHT_BEGONNEN | Kein `categories.py` / `tags.py` Model-File in `app/models/` |
| Backend API | TEILWEISE | Nur via `AnalysisResult.suggested_topics` + Dashboard-Endpoint; kein dediziertes `/topics`-CRUD |
| Frontend | TEILWEISE | `TopicsPage.jsx` mit `useTopics` hook; Datenquelle unklar (kein API-Endpoint sichtbar) |
| Tag-CRUD | NICHT_BEGONNEN | Kein `/tags`-Endpunkt, keine Verwaltungs-API |

**Lücken:**
- ORM-Models für `categories`/`tags`/`document_tags` fehlen (P1)
- CRUD-Endpunkte `/topics`, `/tags`, `/categories` fehlen (P1)
- Manuelles Tagging-UI fehlt (P2)
- Kategorienzuweisung zu Dokumenten fehlt (P2)

---

## 6. Datenanalyse

**Priorität:** P1 | **Status:** TEILWEISE

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | `analysis_jobs`, `analysis_results`, `analysis_comparisons`, `analysis_suggestions`, Link-Tabellen |
| Backend | TEILWEISE | Job-CRUD, summarize, compare, approve, result-Abruf vorhanden; Abbruch/Retry fehlen |
| Engine | STUB | `DeterministicAnalysisStubEngine` — kein reales LLM-Binding |
| Frontend | TEILWEISE | Kein dedizierter `/analysis`-Route in aktivem Nav; nur Dashboard-Widget |
| Approval-Flow | PASS | `require_workspace_admin`, `AnalysisApprovalService`, Suggestions-Status-Maschine |

**Lücken:**
- Kein `DELETE /analysis/jobs/:id/cancel`-Endpunkt (P1)
- Kein Retry-Mechanismus für fehlerhafte Jobs (P2)
- Kein dedizierter Analysis-Frontend-Screen (P2)
- Echtes LLM-Provider-Binding fehlt (`UnconfiguredLlmProvider` im Chat-Dienst) (P1)
- Verlaufsansicht: Job-Liste paginiert vorhanden, aber kein History-Filter nach Zeitraum (P3)

---

## 7. Dashboard

**Priorität:** P1 | **Status:** TEILWEISE

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | Liest aus allen Tabellen |
| Backend | TEILWEISE | 5 Endpunkte: `/summary`, `/activity`, `/imports`, `/analysis`, `/quality`, `/topics`; kein `/drift` |
| Frontend | PASS | `DashboardPage.jsx` vorhanden |
| Drift-Widget | NICHT_BEGONNEN | Kein `GET /dashboard/drift`-Endpunkt |

**Lücken:**
- `GET /dashboard/drift` fehlt — Dashboard-Drift-Widget hat keine API-Quelle (P2)
- Dashboard-Refresh-Intervall: kein Auto-Refresh-Mechanismus sichtbar (P3)

---

## 8. Benutzer

**Priorität:** P2 | **Status:** TEILWEISE

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | `users`, `workspace_memberships`, `auth_sessions` |
| Auth | PASS | Login/Logout/Session, Password-Hash, `is_active`-Flag |
| User-CRUD | NICHT_BEGONNEN | Kein `GET/POST/PATCH /users`-Endpunkt in v1 |
| Frontend | NICHT_BEGONNEN | Keine Benutzerverwaltungs-Seite in aktiven Routen |

**Lücken:**
- User-Einladung / -Erstellung fehlt (P2)
- User-Profil-Seite fehlt (P3)
- Passwort-Änderung fehlt (P2)

---

## 9. Rollen

**Priorität:** P2 | **Status:** TEILWEISE

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | `workspace_memberships.role` (owner/admin/member), CheckConstraint |
| Auth-Guards | PASS | `require_workspace_member`, `require_workspace_admin` in allen relevanten Endpunkten |
| Rollen-Management API | NICHT_BEGONNEN | Kein `PATCH /memberships/:id/role`-Endpunkt |
| Frontend | NICHT_BEGONNEN | Keine Rollen-Verwaltungs-UI |

**Lücken:**
- Rollen-Zuweisung per API fehlt (P2)
- Workspace-Mitglied entfernen fehlt (P2)
- `SettingsPage.jsx` vermutlich Platzhalter (P2)

---

## 10. Data Quality

**Priorität:** P1 | **Status:** TEILWEISE

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | `data_quality_runs`, `data_quality_findings` (migration 0018, 0019) |
| Backend Read | PASS | GET `/data-quality/runs`, `/runs/:id`, `/findings`, `/summary` |
| Trigger | NICHT_BEGONNEN | Kein `POST /data-quality/runs` — kein Mechanismus, einen Run auszulösen |
| Frontend | PASS | `DataQualityPage.jsx` |

**Lücken:**
- `POST /data-quality/runs` fehlt — Runs können nicht manuell gestartet werden (P1)
- Kein Hintergrund-Scheduler für automatische Runs (P2)
- `data_quality_metrics`/`data_quality_snapshots` explizit auf "deferred" im Model-Kommentar (P3)

---

## 11. Drift Detection

**Priorität:** P1 | **Status:** VOLLSTÄNDIG (im definierten Scope)

| Schicht | Stand | Detail |
|---|---|---|
| DB | PASS | `drift_runs`, `drift_findings`, `drift_snapshots` (migration 0020) |
| Backend | PASS | GET `/drift/runs`, `/runs/:id`, `/findings`, `/summary` — ausschließlich Read-only |
| Frontend | PASS | `DriftPage.jsx` |
| Invarianten | EINGEHALTEN | PROHIBIT-02, PROHIBIT-06, PROHIBIT-08 — kein Repair, kein Cleanup |

**Anmerkung:** Kein Trigger-Endpunkt per Design (Drift Detection = Read-Only). M5d Repair Governance ist Post-1.0.

---

## 12. Export

**Priorität:** P2 | **Status:** NICHT_BEGONNEN

| Schicht | Stand | Detail |
|---|---|---|
| DB | NICHT_BEGONNEN | Keine Export-Tabelle, kein Audit-Event-Schema für Exports |
| Backend | NICHT_BEGONNEN | Kein `/export`-Endpunkt in keiner API-Datei |
| Frontend | NICHT_BEGONNEN | Keine Export-Route, keine Export-UI-Komponente |

**Lücken:**
- PDF-Export (P2)
- Markdown-Export (P2)
- JSON-Export (P2)
- Workspace Isolation bei Exports (Pflicht, P2)
- Audit-Event für jeden Export (Pflicht, P2)

---

## 13. API / Status / Governance

**Priorität:** P1 (Status/Audit), P2 (Governance-Persistence) | **Status:** TEILWEISE

| Schicht | Stand | Detail |
|---|---|---|
| Status/Health | PASS | `/status`, `/health` — maschinenlesbar |
| Audit | PASS | `/audit` — Audit-Log vorhanden |
| Governance API | TEILWEISE | `GET /governance/status`, `PATCH /privacy-mode`, Changeset/Rollback-Gerüst vorhanden |
| Governance-Persistence | NICHT_BEGONNEN | `_changesets`, `_rollback_points` sind In-Memory-Listen (`list[dict]`) — kein DB-Backing |
| Approvals | TEILWEISE | `app/api/v1/approvals.py` vorhanden; kein persistentes Approval-Schema in DB |

**Lücken:**
- Governance-Changesets nicht in DB persistiert — Verlust bei Neustart (P2)
- `/governance`-Route in Frontend vorhanden (`GovernancePage.jsx`) aber nicht im Nav (P2)
- `/admin/diagnostics` ohne Router-Guard (aktiver RC Blocker RCB-003, P1)

---

## 14. Monitoring / Observability

**Priorität:** P1 | **Status:** TEILWEISE

| Schicht | Stand | Detail |
|---|---|---|
| Logging | PASS | `bind_observability_context`, `log_event` in Search, Import, Chat |
| Backend-Checks (9/14) | PASS | Implementiert |
| Fehlende Komponenten | NICHT_BEGONNEN | 5 fehlen |

**Fehlende Monitoring-Komponenten (aus `observability_report`):**

| Komponente | Priorität |
|---|---|
| `request_access_log` | P1 |
| `auth_failure_counter` | P1 |
| `analysis_job_metrics` | P2 |
| `error_boundary` (Frontend) | P2 |
| `route_error_handler` (Frontend) | P2 |

---

## Zusammenfassung nach Status

| Status | Kategorien |
|---|---|
| VOLLSTÄNDIG | Dokumente, Import, Drift Detection |
| TEILWEISE | Suche, Themen, Datenanalyse, Dashboard, Benutzer, Rollen, Data Quality, API/Governance, Monitoring |
| VORBEREITET | OCR |
| NICHT_BEGONNEN | Export |

## Zusammenfassung nach Priorität

| Priorität | Offene Gaps |
|---|---|
| P1 | Topics ORM-Models + CRUD-API, Analysis LLM-Binding, Analysis Cancel-Endpunkt, Data Quality Trigger, Admin-Route Router-Guard, request_access_log, auth_failure_counter |
| P2 | OCR-Engine, Search-Filter, Dashboard Drift-Widget, User-CRUD, Rollen-Management, Export-Center (PDF/MD/JSON), Governance-Persistence, Analysis Frontend-Screen |
| P3 | Semantische Suche, Tag-History-Filter, data_quality_snapshots, User-Profil, Dashboard Auto-Refresh |

---

## Nicht-produktive Routen (undokumentiert, kein NAV-Eintrag)

Diese Routen sind in `routes.jsx` vorhanden, aber explizit aus der Nav entfernt und nicht dokumentiert:

| Route | Page | Status |
|---|---|---|
| `/tools` | — | Undokumentiert, kein Use-Case definiert |
| `/memory` | — | Undokumentiert |
| `/tasks` | — | Undokumentiert |
| `/projects` | — | Undokumentiert |
| `/agents` | — | Undokumentiert |
| `/collaboration` | `CollaborationPage.jsx` | Undokumentiert |
| `/governance` | `GovernancePage.jsx` | Im Frontend vorhanden, kein Nav-Eintrag |
| `/admin/diagnostics` | `AdminDiagnosticsPage.jsx` | Kein Router-Guard (RC Blocker RCB-003) |

**Empfehlung:** Diese Routen entweder entfernen oder durch `ProtectedRoute` mit expliziter Admin-Rollenprüfung absichern.

---

*evaluation_method: static_code_analysis | generated_at: 2026-06-15*
