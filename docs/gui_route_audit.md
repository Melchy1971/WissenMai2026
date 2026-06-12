# GUI Route Audit

**Datum:** 2026-06-12
**Quelle:** frontend/src/app/routes.jsx (nach Bereinigung)

---

## Aktive Routen (MASTERPLAN_APPROVED)

| Route | Komponente | Masterplan-Bereich |
|-------|-----------|-------------------|
| /login | LoginPage | Auth |
| / → /dashboard | Navigate | Redirect |
| /dashboard | DashboardPage | Dashboard |
| /chat | ChatPage | Suche |
| /chat/:id | ChatPage | Suche |
| /documents | DocumentsPage | Dokumente |
| /documents/:id | DocumentDetailPage | Dokumente |
| /rag | RAGCenterPage | Datenanalyse / Import |
| /data-quality | DataQualityPage | Data Quality |
| /settings | SettingsPage | Einstellungen |

**Gesamt aktive Routen:** 10 (inkl. Redirect und Auth)

---

## Entfernte Routen

| Route | Komponente | Grund | Kategorie |
|-------|-----------|-------|----------|
| /tools | ToolCenterPage | Kein Masterplan-Bezug | FUTURE_PHASE |
| /memory | MemoryCenterPage | Kein Masterplan-Bezug | FUTURE_PHASE |
| /tasks | TaskCenterPage | Kein Masterplan-Bezug | FUTURE_PHASE |
| /projects | ProjectCenterPage | Kein Masterplan-Bezug | FUTURE_PHASE |
| /agents | AgentCenterPage | Kein Masterplan-Bezug | FUTURE_PHASE |
| /collaboration | CollaborationCenterPage | Kein Masterplan-Bezug | FUTURE_PHASE |
| /governance | GovernanceCenterPage | Explizit nicht freigegeben | LEGACY |
| /admin/diagnostics | AdminDiagnosticsPage | Debug-Tool | LEGACY |

**Gesamt entfernte Routen:** 8

---

## Ergebnis

- legacy_routes: 0
- debug_routes: 0
- test_routes: 0
- unknown_routes: 0
- future_phase_routes: 0 (Dateien gelöscht)

Alle nicht freigegebenen Routen vollständig entfernt. Keine Feature Flags. Keine Hidden Routes.

