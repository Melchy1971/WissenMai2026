# Final GUI Scope

**Datum:** 2026-06-15 (aktualisiert)
**Masterplan-Referenz:** reports/current/masterplan_status.json (progress_percent=42.0, M5a/M5b BLOCKED, M5c PREPARED)
**Gate-Referenz:** reports/current/m5b_production_readiness_gate.json (BLOCKED), reports/current/m5c_start_gate.json (BLOCKED)
**RC-Entscheidung:** reports/current/release_candidate_decision.json (BLOCKED — root: TEST_DATABASE_URL)

---

## Freigegebene Bereiche

| Bereich | Route(s) | Komponente | Begründung |
|---------|---------|-----------|-----------|
| Dashboard | /dashboard | DashboardPage | Kernfunktion — Systemüberblick |
| Suche / Chat | /chat, /chat/:id | ChatPage | Kernfunktion — AI-Query-Interface ("Suche" im Masterplan) |
| Dokumente | /documents, /documents/:id | DocumentsPage, DocumentDetailPage | Kernfunktion — Dokumentenverwaltung |
| Datenanalyse / Import | /rag | RAGCenterPage | Kernfunktion — Import und Analyse (Masterplan: Import + Datenanalyse) |
| Data Quality | /data-quality | DataQualityPage | M5a-Scope — freigegeben als Data Quality Dashboard |
| Einstellungen | /settings | SettingsPage | Kernfunktion — Konfiguration |
| Login | /login | LoginPage | Auth — erforderlich |

### Drift Detection

Drift Detection (M5b) ist implementiert und erreichbar unter `/drift` via `DriftPage` → `drift_v2/DriftDashboard`. Formale Freigabe blockiert: M5b Production Readiness Gate BLOCKED (cascade aus M5a, root: TEST_DATABASE_URL).

| Bereich | Route | Komponente | Status |
|---------|-------|-----------|--------|
| Drift Detection | /drift | DriftPage → drift_v2/DriftDashboard | Implementiert, Read-Only, formale Freigabe ausstehend |

Nachweis: `reports/current/drift_v2_ui_truth_report.json` PASS (29/29), `reports/current/drift_v2_import_audit.json` PASS.
**Cleanup/Repair in Drift: NO_GO** — PROHIBIT-02, PROHIBIT-06.

---

## Nicht freigegebene Bereiche

| Bereich | Begründung | Kategorie |
|---------|-----------|----------|
| Tool Center (/tools) | Kein Masterplan-Bezug in freigegebenen Phasen | FUTURE_PHASE |
| Memory (/memory) | Kein Masterplan-Bezug | FUTURE_PHASE |
| Tasks (/tasks) | Kein Masterplan-Bezug | FUTURE_PHASE |
| Projekte (/projects) | Kein Masterplan-Bezug | FUTURE_PHASE |
| Agents (/agents) | Kein Masterplan-Bezug | FUTURE_PHASE |
| Collaboration (/collaboration) | Kein Masterplan-Bezug | FUTURE_PHASE |
| Governance (/governance) | Explizit nicht freigegeben (Governance Admin = kein Masterplan-Bezug) | LEGACY |
| Admin Diagnostics (/admin/diagnostics) | Debug-Tool, kein Produktionsbestandteil | LEGACY |
| Drift Detection | M5b BLOCKED — Freigabe erst bei M5b Production Readiness PASS | BLOCKED_GATE |

---

## Erlaubte Dashboard-Widgets

| Widget | Datenquelle | Zulässig |
|--------|------------|---------|
| Systemstatus | /api/v1/status | ja |
| Dokumentanzahl | /api/v1/documents?summary=true | ja |
| Importstatus | /api/v1/jobs?type=import | ja |
| Suchaktivität | /api/v1/search/activity | ja |
| Data Quality Score | /api/v1/data-quality/summary | ja |
| Drift Status | /api/v1/drift/status | NEIN — M5b BLOCKED |
| Letzte Analysen | /api/v1/data-quality/runs?limit=5 | ja |
| Wichtige Warnungen | /api/v1/status (warnings field) | ja |

Verboten: GateStatusCard, ApprovalQueue, AuditLogTable, Debug-Widgets, interne Reports.

---

## Erlaubte Einstellungs-Sektionen

| Sektion | Inhalt | Zulässig |
|---------|--------|---------|
| Provider (KI Provider) | model, base_url, timeout, api_key | ja |
| RAG (Import / Sucheinstellungen) | chunk_size, chunk_overlap, min_score, max_chunks | ja |
| UI (Benutzerprofil / Themenverwaltung) | dark_mode, compact_view, language | ja |
| Voice | — | NEIN — nicht freigegeben |
| Security | — | NEIN — nicht freigegeben |
| Governance | — | NEIN — explizit nicht freigegeben |
| Memory | — | NEIN — nicht freigegeben |
| Agents | — | NEIN — nicht freigegeben |
| Collaboration | — | NEIN — nicht freigegeben |

---

## Fehlende Masterplan-Bereiche (ohne Implementierung — kein Cleanup erforderlich)

| Bereich | Status |
|---------|--------|
| Themen (Topics) | Kein entsprechendes UI vorhanden — zukünftige Phase |
| Benutzer (User Management) | Kein entsprechendes UI vorhanden — zukünftige Phase |

Diese Bereiche sind im Masterplan vorgesehen, aber nicht implementiert. Kein Cleanup erforderlich, keine Dummy-Seiten anlegen.

