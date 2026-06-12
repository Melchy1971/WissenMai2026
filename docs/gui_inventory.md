# GUI Inventur

**Datum:** 2026-06-12
**Quelle:** frontend/src/app/routes.jsx, frontend/src/app/AppShell.jsx
**Referenz Masterplan:** reports/current/masterplan_status.json, masterplan.md

---

## Klassifikation

| Status | Bedeutung |
|--------|-----------|
| MASTERPLAN_APPROVED | Explizit freigegeben im Masterplan / Final GUI Scope |
| FUTURE_PHASE | Noch nicht freigegeben — fehlt im Masterplan |
| LEGACY | Veraltete Funktion, kein Masterplan-Bezug, Debug/Admin-Tool |
| TEST_ONLY | Ausschliesslich fuer Tests vorhanden |
| UNKNOWN | Kein Masterplan-Bezug, Funktion unklar |

---

## Navigation (AppShell NAV_ITEMS)

| Label | Route | Komponente | Status | Masterplan-Kapitel | Phase | Gate |
|-------|-------|-----------|--------|-------------------|-------|------|
| Dashboard | /dashboard | DashboardPage | MASTERPLAN_APPROVED | Produktfunktionen / Betrieb | M4+ | — |
| Chat | /chat | ChatPage | MASTERPLAN_APPROVED | Suche (AI-Query-Interface) | M4+ | — |
| Dokumente | /documents | DocumentsPage | MASTERPLAN_APPROVED | Dokumentenverwaltung | M4+ | — |
| Tool Center | /tools | ToolCenterPage | FUTURE_PHASE | kein Bezug | — | — |
| Memory | /memory | MemoryCenterPage | FUTURE_PHASE | kein Bezug | — | — |
| Tasks | /tasks | TaskCenterPage | FUTURE_PHASE | kein Bezug | — | — |
| Projekte | /projects | ProjectCenterPage | FUTURE_PHASE | kein Bezug | — | — |
| RAG | /rag | RAGCenterPage | MASTERPLAN_APPROVED | Datenanalyse / Import | M4+ | — |
| Agents | /agents | AgentCenterPage | FUTURE_PHASE | kein Bezug | — | — |
| Collaboration | /collaboration | CollaborationCenterPage | FUTURE_PHASE | kein Bezug | — | — |
| Governance | /governance | GovernanceCenterPage | LEGACY | explizit nicht freigegeben (Governance Admin) | — | — |
| Einstellungen | /settings | SettingsPage | MASTERPLAN_APPROVED | Einstellungen | M4+ | — |
| Admin | /admin/diagnostics | AdminDiagnosticsPage | LEGACY | kein Bezug — Debug/Diagnose-Tool | — | — |

---

## Alle Routes (routes.jsx)

| Route | Komponente | Status | Entfernen? |
|-------|-----------|--------|-----------|
| /login | LoginPage | MASTERPLAN_APPROVED | nein |
| / → /dashboard | Navigate | MASTERPLAN_APPROVED | nein |
| /dashboard | DashboardPage | MASTERPLAN_APPROVED | nein |
| /documents | DocumentsPage | MASTERPLAN_APPROVED | nein |
| /documents/:id | DocumentDetailPage | MASTERPLAN_APPROVED | nein |
| /chat | ChatPage | MASTERPLAN_APPROVED | nein |
| /chat/:id | ChatPage | MASTERPLAN_APPROVED | nein |
| /data-quality | DataQualityPage | MASTERPLAN_APPROVED | nein |
| /rag | RAGCenterPage | MASTERPLAN_APPROVED | nein |
| /settings | SettingsPage | MASTERPLAN_APPROVED | nein |
| /tools | ToolCenterPage | FUTURE_PHASE | **ja** |
| /memory | MemoryCenterPage | FUTURE_PHASE | **ja** |
| /tasks | TaskCenterPage | FUTURE_PHASE | **ja** |
| /projects | ProjectCenterPage | FUTURE_PHASE | **ja** |
| /agents | AgentCenterPage | FUTURE_PHASE | **ja** |
| /collaboration | CollaborationCenterPage | FUTURE_PHASE | **ja** |
| /governance | GovernanceCenterPage | LEGACY | **ja** |
| /admin/diagnostics | AdminDiagnosticsPage | LEGACY | **ja** |

---

## Dashboard-Widgets (DashboardPage)

| Widget | Komponente | Status | Entfernen? |
|--------|-----------|--------|-----------|
| System-Gates | GateStatusCard | LEGACY (Gate Debug View) | **ja** |
| Offene Freigaben | ApprovalQueue | LEGACY (internes Approval-System) | **ja** |
| Letzte Audit-Ereignisse | AuditLogTable | LEGACY (interne Reports) | **ja** |

---

## Einstellungen-Sektionen (SettingsPage)

| Sektion | Status | Entfernen? |
|---------|--------|-----------|
| Provider (KI Provider) | MASTERPLAN_APPROVED | nein |
| Voice | FUTURE_PHASE | **ja** |
| Security | LEGACY (keine Masterplan-Freigabe) | **ja** |
| Governance | LEGACY (Governance Admin nicht freigegeben) | **ja** |
| RAG (Import/Sucheinstellungen) | MASTERPLAN_APPROVED | nein |
| Memory | FUTURE_PHASE | **ja** |
| Agents | FUTURE_PHASE | **ja** |
| Collaboration | FUTURE_PHASE | **ja** |
| UI (Benutzerprofil / Themenverwaltung) | MASTERPLAN_APPROVED | nein |

---

## Shared Components — Verwendungsanalyse

| Komponente | Genutzt von (ohne Test-Files) | Status | Entfernen? |
|-----------|------------------------------|--------|-----------|
| AgentLimitView | AgentCenterPage | FUTURE_PHASE | **ja** |
| ApprovalQueue | DashboardPage (bereinigt), ToolCenterPage, GovernanceCenterPage | LEGACY nach Bereinigung | **ja** |
| AuditLogTable | DashboardPage (bereinigt), GovernanceCenterPage | LEGACY nach Bereinigung | **ja** |
| ChangeSetDiff | GovernanceCenterPage | LEGACY | **ja** |
| CollaborationRunView | CollaborationCenterPage | FUTURE_PHASE | **ja** |
| ConflictReportView | CollaborationCenterPage | FUTURE_PHASE | **ja** |
| DataClassificationBadge | RAGCenterPage, SourceList, MemoryScoreCard | MASTERPLAN_APPROVED (RAG) | nein |
| ExecutionPlanView | AgentCenterPage | FUTURE_PHASE | **ja** |
| GateStatusCard | DashboardPage (bereinigt) | LEGACY nach Bereinigung | **ja** |
| MemoryScoreCard | MemoryCenterPage | FUTURE_PHASE | **ja** |
| PolicyDecisionView | GovernanceCenterPage, CollaborationRunView | LEGACY | **ja** |
| RiskBadge | ApprovalQueue, AuditLogTable, ConflictReportView, CollaborationRunView, ToolCenterPage | LEGACY nach Bereinigung | **ja** |
| RollbackPointList | GovernanceCenterPage | LEGACY | **ja** |
| SourceList | — (kein Page-Import) | UNKNOWN / kein Nutzer | **ja** |
| TokenBudgetView | — (kein Page-Import) | UNKNOWN / kein Nutzer | **ja** |

---

## Feature-Komponenten

| Komponente | Status | Entfernen? |
|-----------|--------|-----------|
| features/drift/DriftDashboard.jsx | M5b BLOCKED → Drift Detection nicht freigegeben | **ja** |
| features/data-quality/DataQualityDashboard.jsx | MASTERPLAN_APPROVED | nein |

---

## Ergebnis

- MASTERPLAN_APPROVED: 8 Routes, 3 Einstellungs-Sektionen, 1 Feature-Komponente
- Zu entfernen: 8 Routes, 6 Einstellungs-Sektionen, 14 Shared Components, 1 Feature-Komponente, 8 Page-Files
- Fehlende freigegebene Bereiche ohne Implementierung: Themen, Benutzer (nicht in Scope dieses Cleanup)

