# GUI Cleanup — Vorher/Nachher Diff Report

**Datum:** 2026-06-12
**Grundlage:** docs/gui_inventory.md, docs/gui_route_audit.md, docs/gui_component_cleanup.md
**Nachweis:** reports/current/gui_truth_report.json — PASS (12/12)

---

## 1. Navigation: Vorher vs. Nachher

### Vorher — 13 NAV_ITEMS (AppShell)

| Label | Route | Kategorie |
|-------|-------|-----------|
| Dashboard | /dashboard | MASTERPLAN_APPROVED |
| Chat | /chat | MASTERPLAN_APPROVED |
| Dokumente | /documents | MASTERPLAN_APPROVED |
| Tool Center | /tools | FUTURE_PHASE |
| Memory | /memory | FUTURE_PHASE |
| Tasks | /tasks | FUTURE_PHASE |
| Projekte | /projects | FUTURE_PHASE |
| RAG | /rag | MASTERPLAN_APPROVED |
| Agents | /agents | FUTURE_PHASE |
| Collaboration | /collaboration | FUTURE_PHASE |
| Governance | /governance | LEGACY |
| Einstellungen | /settings | MASTERPLAN_APPROVED |
| Admin | /admin/diagnostics | LEGACY |

### Nachher — 6 NAV_ITEMS (AppShell)

| Label | Route | Masterplan-Bereich |
|-------|-------|-------------------|
| Dashboard | /dashboard | Dashboard / Betrieb |
| Suche | /chat | AI-Query-Interface |
| Dokumente | /documents | Dokumentenverwaltung |
| Datenanalyse | /rag | Import / Datenanalyse |
| Data Quality | /data-quality | Data Quality Score |
| Einstellungen | /settings | Einstellungen |

**Reduktion:** 13 → 6 NAV_ITEMS (−7, −54%)

---

## 2. Entfernte Menüpunkte — Detail

| Name | Route | Grund | Masterplan-Referenz | Phase | Gate |
|------|-------|-------|---------------------|-------|------|
| Tool Center | /tools | Kein Masterplan-Bezug — keine freigegebene Funktion im Produktscope | masterplan.md: nicht gelistet | — | — |
| Memory | /memory | Kein Masterplan-Bezug — Memory-System nicht Teil des Produktscopes | masterplan.md: nicht gelistet | — | — |
| Tasks | /tasks | Kein Masterplan-Bezug — Task-Management nicht Teil des Produktscopes | masterplan.md: nicht gelistet | — | — |
| Projekte | /projects | Kein Masterplan-Bezug — Projektverwaltung nicht Teil des Produktscopes | masterplan.md: nicht gelistet | — | — |
| Agents | /agents | Kein Masterplan-Bezug — Agent-Framework nicht Teil des Produktscopes | masterplan.md: nicht gelistet | — | — |
| Collaboration | /collaboration | Kein Masterplan-Bezug — Collaboration-System nicht Teil des Produktscopes | masterplan.md: nicht gelistet | — | — |
| Governance | /governance | Explizit nicht freigegeben: "Governance Admin ohne Masterplan-Bezug" | masterplan.md: nicht freigegebene Bereiche | — | — |
| Admin | /admin/diagnostics | Debug/Diagnose-Tool — kein Produktfeature, kein Masterplan-Bezug | masterplan.md: nicht freigegebene Bereiche | — | — |

**Hinweis:** "Drift Detection" fehlt in der finalen Navigation, da `m5b_production_readiness_gate` BLOCKED. Freigabe erst bei Gate PASS. Quelle: `reports/current/m5b_production_readiness_gate.json`.

---

## 3. Routen: Vorher vs. Nachher

### Vorher — 18 Routen (routes.jsx)

| Route | Komponente | Status |
|-------|-----------|--------|
| /login | LoginPage | APPROVED |
| / → /dashboard | Navigate | APPROVED |
| /dashboard | DashboardPage | APPROVED |
| /chat | ChatPage | APPROVED |
| /chat/:id | ChatPage | APPROVED |
| /documents | DocumentsPage | APPROVED |
| /documents/:id | DocumentDetailPage | APPROVED |
| /data-quality | DataQualityPage | APPROVED |
| /rag | RAGCenterPage | APPROVED |
| /settings | SettingsPage | APPROVED |
| /tools | ToolCenterPage | FUTURE_PHASE |
| /memory | MemoryCenterPage | FUTURE_PHASE |
| /tasks | TaskCenterPage | FUTURE_PHASE |
| /projects | ProjectCenterPage | FUTURE_PHASE |
| /agents | AgentCenterPage | FUTURE_PHASE |
| /collaboration | CollaborationCenterPage | FUTURE_PHASE |
| /governance | GovernanceCenterPage | LEGACY |
| /admin/diagnostics | AdminDiagnosticsPage | LEGACY |

### Nachher — 10 Routen (routes.jsx)

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

**Reduktion:** 18 → 10 Routen (−8, −44%)

---

## 4. Entfernte Komponenten

### Pages (8 entfernt)

| Datei | Zugehörige Route | Grund |
|-------|-----------------|-------|
| AdminDiagnosticsPage.jsx | /admin/diagnostics | LEGACY — Debug-Tool ohne Masterplan-Bezug |
| AgentCenterPage.jsx | /agents | FUTURE_PHASE — kein Masterplan-Bezug |
| CollaborationCenterPage.jsx | /collaboration | FUTURE_PHASE — kein Masterplan-Bezug |
| GovernanceCenterPage.jsx | /governance | LEGACY — Governance Admin explizit nicht freigegeben |
| MemoryCenterPage.jsx | /memory | FUTURE_PHASE — kein Masterplan-Bezug |
| ProjectCenterPage.jsx | /projects | FUTURE_PHASE — kein Masterplan-Bezug |
| TaskCenterPage.jsx | /tasks | FUTURE_PHASE — kein Masterplan-Bezug |
| ToolCenterPage.jsx | /tools | FUTURE_PHASE — kein Masterplan-Bezug |

### Shared Components (14 entfernt)

| Datei | Letzte Nutzer | Grund |
|-------|--------------|-------|
| AgentLimitView.jsx | AgentCenterPage | FUTURE_PHASE-Abhängigkeit entfallen |
| ApprovalQueue.jsx | DashboardPage, GovernanceCenterPage | LEGACY — Gate Debug View, internes Approval-System |
| AuditLogTable.jsx | DashboardPage, GovernanceCenterPage | LEGACY — interne Reports, kein Produktfeature |
| ChangeSetDiff.jsx | GovernanceCenterPage | LEGACY — Governance entfernt |
| CollaborationRunView.jsx | CollaborationCenterPage | FUTURE_PHASE-Abhängigkeit entfallen |
| ConflictReportView.jsx | CollaborationCenterPage | FUTURE_PHASE-Abhängigkeit entfallen |
| ExecutionPlanView.jsx | AgentCenterPage | FUTURE_PHASE-Abhängigkeit entfallen |
| GateStatusCard.jsx | DashboardPage | LEGACY — Gate Debug View, kein Produktfeature |
| MemoryScoreCard.jsx | MemoryCenterPage | FUTURE_PHASE-Abhängigkeit entfallen |
| PolicyDecisionView.jsx | GovernanceCenterPage | LEGACY — Governance entfernt |
| RiskBadge.jsx | ApprovalQueue, AuditLogTable u.a. | LEGACY — alle Nutzer entfernt |
| RollbackPointList.jsx | GovernanceCenterPage | LEGACY — Governance entfernt |
| SourceList.jsx | kein aktiver Nutzer | UNKNOWN — orphan |
| TokenBudgetView.jsx | kein aktiver Nutzer | UNKNOWN — orphan |

### Feature-Komponenten (1 entfernt)

| Datei | Grund |
|-------|-------|
| features/drift/DriftDashboard.jsx | M5b BLOCKED — `m5b_production_readiness_gate` BLOCKED, Drift Detection nicht freigegeben. Freigabe erst bei Gate PASS. |

### API-Dateien (8 entfernt)

| Datei | Zugehörige Seite |
|-------|----------------|
| api/admin.js | AdminDiagnosticsPage |
| api/agents.js | AgentCenterPage |
| api/collaboration.js | CollaborationCenterPage |
| api/governance.js | GovernanceCenterPage |
| api/memory.js | MemoryCenterPage |
| api/projects.js | ProjectCenterPage |
| api/tasks.js | TaskCenterPage |
| api/tools.js | ToolCenterPage |

---

## 5. Dashboard-Bereinigung

### Entfernte Widgets

| Widget | Komponente | Grund |
|--------|-----------|-------|
| System-Gates | GateStatusCard | Gate Debug View — internes Entwicklungswerkzeug, kein Produktfeature |
| Offene Freigaben | ApprovalQueue | Internes Approval-System — kein Produktfeature |
| Letzte Audit-Ereignisse | AuditLogTable | Interne Reports — kein Produktfeature |

### Finale Dashboard-Widgets (7)

1. Systemstatus (Stat-Cards: Backend, Datenbank, KI-Provider)
2. Dokumentanzahl
3. Importstatus (letzter Job)
4. Suchaktivität
5. Data Quality Score
6. Letzte Analysen (Tabelle)
7. Wichtige Warnungen

---

## 6. Einstellungen-Bereinigung

### Entfernte Sektionen (6)

| Sektion | Grund |
|---------|-------|
| Voice | FUTURE_PHASE — kein Masterplan-Bezug |
| Security | LEGACY — keine Masterplan-Freigabe |
| Governance | LEGACY — Governance Admin explizit nicht freigegeben |
| Memory | FUTURE_PHASE — kein Masterplan-Bezug |
| Agents | FUTURE_PHASE — kein Masterplan-Bezug |
| Collaboration | FUTURE_PHASE — kein Masterplan-Bezug |

### Finale Einstellungs-Sektionen (3)

1. KI Provider
2. Import / Sucheinstellungen
3. Benutzerprofil / Darstellung

---

## 7. Komplexitätsreduktion (Zusammenfassung)

| Kategorie | Vorher | Nachher | Reduktion |
|-----------|--------|---------|-----------|
| NAV_ITEMS | 13 | 6 | −7 (−54%) |
| Routen | 18 | 10 | −8 (−44%) |
| Pages | 16 | 8 | −8 (−50%) |
| Shared Components | 18 | 4 | −14 (−78%) |
| Feature-Komponenten | 2 | 1 | −1 (−50%) |
| API-Dateien | ~13 | ~5 | −8 (−62%) |
| Einstellungs-Sektionen | 9 | 3 | −6 (−67%) |
| Dashboard-Widgets | ~10 | 7 | −3 |

---

## 8. Finale GUI-Struktur

```
Navigation
├── Dashboard          → /dashboard   (Systemstatus, Docs, Import, DQ, Analysen)
├── Suche              → /chat        (AI-Query-Interface)
├── Dokumente          → /documents   (Liste + Detailansicht)
├── Datenanalyse       → /rag         (Import / RAG / Chunking)
├── Data Quality       → /data-quality (DQ Score, Regeln, Runs)
└── Einstellungen      → /settings    (Provider, Import/Suche, Profil)

Auth
└── /login

Sub-Routen
├── /chat/:id
└── /documents/:id

Ausstehend (nicht implementiert, kein Cleanup-Scope)
├── Themen             → Masterplan-Bereich vorhanden, keine Route
└── Benutzer           → Masterplan-Bereich vorhanden, keine Route

Gesperrt bis Gate
└── Drift Detection    → freigegeben erst bei m5b_production_readiness_gate PASS
```

---

## 9. Gate-Konformität

- Keine Feature Flags
- Keine Hidden Routes
- Keine Disabled-State-Menüpunkte
- Alle entfernten Bereiche vollständig gelöscht (keine toten Imports)
- Drift Detection: ausschliesslich durch Gate-Status gesteuert, nicht durch UI-Toggle

**Nachweis:** `reports/current/gui_truth_report.json` — PASS (12/12)
`legacy_routes=0, debug_routes=0, test_routes=0, unknown_routes=0`
