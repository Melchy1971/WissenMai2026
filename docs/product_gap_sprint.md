# Produktlücken-Sprint — Endanwender-Vollständigkeit

**Stand:** 2026-06-15  
**Dauer:** 1 Woche (5 Arbeitstage)  
**Team:** 1 Person (Solo)  
**LLM:** Ollama lokal — kein externer Key erforderlich  
**Ziel:** Anwendung aus Endanwendersicht vollständig nutzbar

---

## Nicht im Sprint

| Bereich | Grund |
|---|---|
| M5c Cleanup | PROHIBIT-06 — NO_GO bis m5c_start_gate = PASS |
| Repair | PROHIBIT-02 — dauerhaft gesperrt |
| Governance Automation | Post-1.0 Roadmap |
| Gate-Debug-Views | Nicht im Endanwender-Scope |
| Admin-Spezialseiten (/admin, /rag-center, /governance, /agents) | Nicht im Endanwender-Scope |

---

## Ausgangslage

Aus `product_e2e_truth_suite.json`:

| Szenario | Status | Ursache |
|---|---|---|
| S01 Login | PASS | — |
| S02 Import | PASS | — |
| S03 Suche | CONDITIONAL_PASS | RCB-001 NAV + kein Sprachstemming |
| S04 Thema öffnen | **FAIL** | Topics-Backend komplett fehlend |
| S05 Analyse starten | CONDITIONAL_PASS | Kein Frontend (AGAP-07), Stub-Engine |
| S06 Analyse übernehmen | CONDITIONAL_PASS | Kein Frontend, kein Audit-Log |
| S07 Export | **FAIL** | Export Center nicht implementiert |
| S08 Logout | PASS | — |

**Ziel des Sprints:** S03–S07 auf PASS bringen.

---

## Abhängigkeitsgraph

```
TEST_DATABASE_URL setzen
    └─→ Gates testbar

RCB-001/002/003 (Navigation)
    └─→ S03 Suche erreichbar
    └─→ Enduser Acceptance unblocked

P1-GAP-01 (Topics ORM: Category, Tag, DocumentTag)
    └─→ P1-GAP-02 (Topics API: GET /api/v1/topics/*)
            └─→ Topic Center Frontend (URL-Fix + Datenbindung)
            └─→ S04 PASS
            └─→ Tag-Filter in Suche (P1-GAP-04)

AGAP-02 (Cancel: Migration + Endpunkt)
    └─→ AGAP-07 (AnalysisPage.jsx) vollständig
    └─→ S05/S06 Frontend PASS

Ollama LLM-Binding
    └─→ Echte Analyseergebnisse statt Stub
    └─→ S05 qualitativ PASS

Export Center MVP (JSON + Markdown)
    └─→ S07 PASS

Dashboard W06 (DriftWidget)
    └─→ Dashboard vollständig (6/6 Widgets)
```

---

## Sprint-Plan (5 Tage)

### Tag 1 — Montag: Infrastruktur-Blocker

**Ziel:** Alle technischen Voraussetzungen für den Rest des Sprints erfüllen. Kein Feature-Code.

| Task | Datei / Ort | Aufwand |
|---|---|---|
| TEST_DATABASE_URL in .env.test setzen | .env.test | 15 min |
| pytest ausführen, Gate-Status prüfen | CI | 30 min |
| RCB-001: NAV_ITEMS /chat statt /search | frontend/src/components/AppShell.jsx | 30 min |
| RCB-002: NAV_ITEMS laut Masterplan — /data-quality hinzufügen, /topics + /import prüfen | frontend/src/components/AppShell.jsx | 45 min |
| RCB-003: AdminRoute-Wrapper für /admin/diagnostics | frontend/src/router/routes.jsx | 30 min |
| AGAP-02: Migration — 'cancelled' zu ANALYSIS_JOB_STATUS_VALUES | backend/migrations/versions/[new].py | 45 min |
| AGAP-02: cancel_job() Service-Methode | backend/app/services/analysis/service.py | 45 min |
| AGAP-02: POST /analysis/jobs/:id/cancel Endpunkt | backend/app/api/v1/analysis.py | 30 min |
| AGAP-06: AuditRecorder-Injection in get_analysis_service() | backend/app/api/v1/analysis.py | 20 min |

**Tages-Check:** pytest lokal grün, /admin gesperrt, Cancel-Endpunkt antwortet 200.

---

### Tag 2 — Dienstag: Topics Backend

**Ziel:** GET /api/v1/topics und GET /api/v1/topics/:id vollständig implementiert.

| Task | Datei / Ort | Aufwand |
|---|---|---|
| P1-GAP-01: Category ORM-Model | backend/app/models/categories.py (NEU) | 45 min |
| P1-GAP-01: Tag ORM-Model + DocumentTag Association | backend/app/models/categories.py | 30 min |
| P1-GAP-01: Relationships zu Document.workspace_id | backend/app/models/document.py | 20 min |
| P1-GAP-02: TopicItem + TopicDetailItem Schema | backend/app/schemas/topics.py (NEU) | 30 min |
| P1-GAP-02: GET /api/v1/topics (paginiert, workspace-scoped) | backend/app/api/v1/topics.py (NEU) | 60 min |
| P1-GAP-02: GET /api/v1/topics/:id (Detail + sources[] + documents[]) | backend/app/api/v1/topics.py | 60 min |
| P1-GAP-02: POST /api/v1/tags, POST /documents/:id/tags | backend/app/api/v1/topics.py | 45 min |
| Router registrieren | backend/app/api/v1/router.py | 10 min |
| API-Tests: AT-Topics-01..04 | backend/tests/api/v1/test_topics.py (NEU) | 45 min |

**Tages-Check:** GET /api/v1/topics antwortet 200 mit leerer Liste für neuen Workspace.

---

### Tag 3 — Mittwoch: Topics Frontend + Ollama LLM-Binding

**Ziel:** Topic Center im Browser nutzbar. LLM-Analyse liefert echte Ergebnisse.

**Vormittag — Topics Frontend:**

| Task | Datei / Ort | Aufwand |
|---|---|---|
| URL-Fix in topics.js: /topics/* → /api/v1/topics/* | frontend/src/api/topics.js | 10 min |
| useTopics.js: Fehlertext entfernen, echte API verdrahten | frontend/src/features/topics/useTopics.js | 20 min |
| TopicsPage: Themenliste mit Empty/Error/Loading State | frontend/src/pages/TopicsPage.jsx | 60 min |
| TopicDetailPage: name, summary, sources[], documents[], tags[] | frontend/src/pages/TopicDetailPage.jsx | 60 min |

**Nachmittag — Ollama LLM-Binding:**

| Task | Datei / Ort | Aufwand |
|---|---|---|
| Config: llm_provider, llm_model_name, llm_base_url in config.py | backend/app/core/config.py | 20 min |
| LlmAnalysisProvider: AnalysisProvider-Interface implementieren | backend/app/services/analysis/llm_provider.py (NEU) | 90 min |
| Ollama-HTTP-Aufruf: POST http://localhost:11434/api/generate | backend/app/services/analysis/llm_provider.py | 45 min |
| get_analysis_service(): Stub → LlmProvider wenn LLM_PROVIDER gesetzt | backend/app/services/analysis/service.py | 20 min |
| Chat: UnconfiguredLlmProvider → HTTP 503 statt RuntimeError | backend/app/api/v1/chat.py | 20 min |
| .env Beispiel-Eintrag (kein Key, nur Modell-Name) | .env.example | 10 min |

**Tages-Check:** Topic Center öffnet sich, zeigt Themenliste. Analyse mit Ollama liefert summary-Feld.

---

### Tag 4 — Donnerstag: AnalysisPage + Export MVP

**Ziel:** Analyse-Flow vollständig im Browser nutzbar. Export (JSON + Markdown) funktioniert.

**Vormittag — AnalysisPage.jsx (AGAP-07):**

| Task | Datei / Ort | Aufwand |
|---|---|---|
| AnalysisPage.jsx: Dokument-Auswahl (Multi-Select), Analyse-Typ | frontend/src/pages/AnalysisPage.jsx (NEU) | 60 min |
| JobStatusPanel: Polling + StatusBadge (pending/running/completed/failed/cancelled) | frontend/src/pages/AnalysisPage.jsx | 45 min |
| ResultPanel: summary, suggested_topics, suggested_tags, Konfidenz | frontend/src/pages/AnalysisPage.jsx | 45 min |
| ApproveButton: nur für workspace_admin sichtbar | frontend/src/pages/AnalysisPage.jsx | 20 min |
| CancelButton: sichtbar bei pending/running, disabled bei terminal | frontend/src/pages/AnalysisPage.jsx | 15 min |
| Route /analysis in routes.jsx eintragen | frontend/src/router/routes.jsx | 10 min |
| NAV_ITEMS: Link zu /analysis ergänzen (wenn im Masterplan) | frontend/src/components/AppShell.jsx | 10 min |

**Nachmittag — Export MVP:**

| Task | Datei / Ort | Aufwand |
|---|---|---|
| ExportRequest + ExportAuditEvent Schema | backend/app/schemas/export.py (NEU) | 20 min |
| ExportService: JSON-Export für Dokument | backend/app/services/export_service.py (NEU) | 30 min |
| ExportService: JSON-Export für Analyseergebnis | backend/app/services/export_service.py | 20 min |
| ExportService: Markdown-Export (beide Quellen) | backend/app/services/export_service.py | 45 min |
| Quellenangaben: source_references[] im Export-Payload | backend/app/services/export_service.py | 20 min |
| Audit-Event bei Export | backend/app/services/export_service.py | 15 min |
| POST /api/v1/export Endpunkt | backend/app/api/v1/export.py (NEU) | 30 min |
| Router registrieren | backend/app/api/v1/router.py | 5 min |
| ExportButton.jsx (Format-Dropdown: JSON / Markdown) | frontend/src/components/ExportButton.jsx (NEU) | 45 min |
| ExportButton in AnalysisPage + DocumentDetailPage einbauen | frontend/src/pages/ | 20 min |

**Tages-Check:** Analyse starten → Result anzeigen → Approve → Export als JSON herunterladen. Kein 500.

---

### Tag 5 — Freitag: Dashboard W06 + E2E-Test

**Ziel:** Dashboard vollständig (6/6), alle 8 Truth-Suite-Szenarien PASS oder CONDITIONAL_PASS.

**Vormittag — Dashboard W06 Drift Widget:**

| Task | Datei / Ort | Aufwand |
|---|---|---|
| DashboardDriftItem Schema | backend/app/schemas/dashboard.py | 20 min |
| list_drift() Service-Methode: latest N Runs + Finding-Counts | backend/app/services/dashboard_service.py | 45 min |
| GET /api/v1/dashboard/drift Endpunkt | backend/app/api/v1/dashboard.py | 20 min |
| DriftWidget.jsx: Severity-Chips + Link zu /drift | frontend/src/components/DriftWidget.jsx (NEU) | 45 min |
| Empty/Error/Loading State im DriftWidget | frontend/src/components/DriftWidget.jsx | 20 min |
| Kein Repair/Cleanup-Button (PROHIBIT-02/06 verifizieren) | frontend/src/components/DriftWidget.jsx | 5 min |
| DriftWidget in DashboardPage einbauen | frontend/src/pages/DashboardPage.jsx | 15 min |

**Nachmittag — Product E2E Test:**

| Task | Datei / Ort | Aufwand |
|---|---|---|
| E2E-Testsuite: S01 Login → S08 Logout durchlaufen | tests/e2e/ oder manuell | 60 min |
| Truth-Suite-Ergebnis dokumentieren | reports/current/product_e2e_truth_suite.json | 20 min |
| product_gate.json re-evaluieren | reports/current/product_gate.json | 30 min |
| Gefundene Regressions fixen (Puffer) | — | 60 min |

**Tages-Check:** product_gate.json: Status wechselt von FAIL auf BLOCKED oder PASS.

---

## Aufwandschätzung Gesamt

| Bereich | Stunden |
|---|---|
| Tag 1 Infrastruktur | ~5 h |
| Tag 2 Topics Backend | ~6 h |
| Tag 3 Topics Frontend + Ollama | ~6 h |
| Tag 4 AnalysisPage + Export | ~7 h |
| Tag 5 Dashboard W06 + E2E | ~6 h |
| **Gesamt** | **~30 h** |

Realistisch für 1 Person in 5 Tagen: 6h produktive Coding-Zeit/Tag = 30h. Kein Puffer für unerwartete Bugs eingerechnet — bei Blockern Priorität auf S04 + S07 (FAIL-Szenarien).

---

## Fallback-Priorisierung bei Zeitdruck

Falls Tag 4 oder 5 nicht vollständig abgeschlossen werden:

| Priorität | Drop-Kandidat | Begründung |
|---|---|---|
| 1 — behalten | RCB-001/002/003 | 1 Tag, blockiert Enduser Acceptance |
| 1 — behalten | Topics Backend | S04 FAIL — blockiert Truth Suite |
| 1 — behalten | Export JSON | S07 FAIL — Mindest-MVP |
| 2 — kürzen | Ollama LLM | Stub-Engine reicht für strukturellen PASS |
| 2 — kürzen | Export Markdown | JSON reicht für MVP |
| 3 — verschieben | Dashboard W06 | 5/6 Widgets reichen für Beta |
| 3 — verschieben | AGAP-06 AuditRecorder | Kein Flow-Blocker, nur Audit-Gap |

---

## Definition of Done (Sprint-Ende)

- [ ] product_e2e_truth_suite.json: 0 FAIL (alle Szenarien PASS oder CONDITIONAL_PASS)
- [ ] Topics Center im Browser öffnet sich und zeigt Themen
- [ ] Analyse starten, Ergebnis sehen, Approve — vollständig im Frontend
- [ ] Export (JSON) für Dokument und Analyse herunterladbar
- [ ] Dashboard: 6/6 Widgets ohne Fehler
- [ ] /admin/diagnostics: nur für Admins erreichbar
- [ ] NAV_ITEMS mit Masterplan synchronisiert
- [ ] Kein Repair-Button, kein Cleanup-Button im gesamten UI (PROHIBIT-02/06)
- [ ] pytest lokal: kein FAIL (nach TEST_DATABASE_URL-Fix)
