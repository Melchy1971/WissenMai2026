# GUI Component Cleanup

**Datum:** 2026-06-12

---

## Verbleibende Komponenten (VERWENDET)

### Pages (8)
| Datei | Genutzt in | Status |
|-------|-----------|--------|
| ChatPage.jsx | /chat, /chat/:id | aktiv |
| DashboardPage.jsx | /dashboard | aktiv |
| DataQualityPage.jsx | /data-quality | aktiv |
| DocumentDetailPage.jsx | /documents/:id | aktiv |
| DocumentsPage.jsx | /documents | aktiv |
| LoginPage.jsx | /login | aktiv |
| RAGCenterPage.jsx | /rag | aktiv |
| SettingsPage.jsx | /settings | aktiv |

### Shared Components (4)
| Datei | Genutzt in | Status |
|-------|-----------|--------|
| DataClassificationBadge.jsx | RAGCenterPage | aktiv |
| PrivacyModeBanner.jsx | AppShell | aktiv |
| SecretInput.jsx | SettingsPage | aktiv |
| SettingsSection.jsx | SettingsPage | aktiv |

### Document Components (5)
| Datei | Genutzt in | Status |
|-------|-----------|--------|
| ChunkPreviewList.jsx | DocumentDetailPage | aktiv |
| DocumentMetaCard.jsx | DocumentDetailPage | aktiv |
| DocumentTable.jsx | DocumentsPage | aktiv |
| SearchResultList.jsx | ChatPage | aktiv |
| VersionList.jsx | DocumentDetailPage | aktiv |

### Chat Components (3)
| Datei | Genutzt in | Status |
|-------|-----------|--------|
| ChatComposer.jsx | ChatPage | aktiv |
| ChatMessageThread.jsx | ChatPage | aktiv |
| ChatSessionList.jsx | ChatPage | aktiv |

### Status Components (5)
| Datei | Genutzt in | Status |
|-------|-----------|--------|
| EmptyState.jsx | mehrere Pages | aktiv |
| ErrorBoundary.jsx | App.jsx | aktiv |
| ErrorState.jsx | mehrere Pages | aktiv |
| LoadingState.jsx | mehrere Pages | aktiv |
| StatusBadge.jsx | mehrere Pages | aktiv |

### Features (1)
| Datei | Genutzt in | Status |
|-------|-----------|--------|
| DataQualityDashboard.jsx | DataQualityPage | aktiv |

---

## Gelöschte Komponenten (14 Shared + 8 Pages + 8 API-Files + 1 Feature)

### Pages (8 gelöscht)
AdminDiagnosticsPage.jsx, AgentCenterPage.jsx, CollaborationCenterPage.jsx,
GovernanceCenterPage.jsx, MemoryCenterPage.jsx, ProjectCenterPage.jsx,
TaskCenterPage.jsx, ToolCenterPage.jsx

### Shared Components (14 gelöscht)
AgentLimitView.jsx, ApprovalQueue.jsx, AuditLogTable.jsx, ChangeSetDiff.jsx,
CollaborationRunView.jsx, ConflictReportView.jsx, ExecutionPlanView.jsx,
GateStatusCard.jsx, MemoryScoreCard.jsx, PolicyDecisionView.jsx, RiskBadge.jsx,
RollbackPointList.jsx, SourceList.jsx, TokenBudgetView.jsx

### Features (1 gelöscht)
features/drift/DriftDashboard.jsx (M5b BLOCKED — nicht freigegeben)

### API-Files (8 gelöscht)
admin.js, agents.js, collaboration.js, governance.js, memory.js,
projects.js, tasks.js, tools.js

