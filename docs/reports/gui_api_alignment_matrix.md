# GUI–Backend API Alignment Matrix

Stand: 2026-06-10

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| ✅ | Implementiert und aligned |
| ⚠️ | Vorhanden, aber Response-Format abweichend |
| ❌ | Fehlt im Backend |

## Alignment-Matrix

| Endpunkt | GUI nutzt | Backend hat | Status | Prio |
|----------|-----------|-------------|--------|------|
| GET /api/v1/status | callApi('/api/v1/status') | /status (basic) | ⚠️ privacy_mode, gates fehlen | HIGH |
| GET /api/v1/governance/status | GovernanceCenterPage | — | ❌ | HIGH |
| GET /api/v1/security/status | AppShell | — | ❌ | MEDIUM |
| GET /api/v1/approvals | DashboardPage, GovernanceCenterPage | — | ❌ | HIGH |
| PATCH /api/v1/approvals/:id | ApprovalQueue | — | ❌ | HIGH |
| GET /api/v1/audit | DashboardPage, GovernanceCenterPage | — | ❌ | HIGH |
| GET /api/v1/governance/changesets | GovernanceCenterPage | — | ❌ | HIGH |
| POST /api/v1/governance/rollback | RollbackPointList | — | ❌ | HIGH |
| GET /api/v1/governance/rollback-points | GovernanceCenterPage | — | ❌ | HIGH |
| GET /api/v1/governance/policy-decisions | GovernanceCenterPage | — | ❌ | MEDIUM |
| PATCH /api/v1/governance/privacy-mode | GovernanceCenterPage | — | ❌ | HIGH |
| GET /api/v1/agents/executions | AgentCenterPage | — | ❌ | MEDIUM |
| GET /api/v1/collaboration/runs | CollaborationCenterPage | — | ❌ | MEDIUM |
| GET /api/v1/collaboration/teams | CollaborationCenterPage | — | ❌ | MEDIUM |
| GET /api/v1/collaboration/conflicts | CollaborationCenterPage | — | ❌ | MEDIUM |
| GET /api/v1/settings | SettingsPage | — | ❌ | CRITICAL |
| PATCH /api/v1/settings | SettingsPage | — | ❌ | CRITICAL |
| PATCH /api/v1/settings/secrets | SettingsPage | — | ❌ | CRITICAL |
| GET /api/v1/tools | ToolCenterPage | ✅ (tools.py) | ✅ | — |
| PATCH /api/v1/tools/:id/toggle | ToolCenterPage | ⚠️ nur enable flag | ⚠️ | MEDIUM |
| GET /api/v1/tools/:id/health | ToolCenterPage | — | ❌ | LOW |
| GET /api/v1/memory | MemoryCenterPage | ✅ | ✅ | — |
| GET /api/v1/memory/search | MemoryCenterPage | ⚠️ andere Route | ⚠️ | MEDIUM |
| GET /api/v1/memory/review-queue | MemoryCenterPage | — | ❌ | MEDIUM |
| GET /api/v1/memory/conflicts | MemoryCenterPage | — | ❌ | LOW |
| GET /api/v1/rag/documents | RAGCenterPage | ✅ | ✅ | — |
| POST /api/v1/rag/documents/:id/reindex | RAGCenterPage | — | ❌ | MEDIUM |
| POST /api/v1/rag/retrieve | RAGCenterPage | ✅ | ✅ | — |
| GET /api/v1/agents | AgentCenterPage | ✅ | ✅ | — |
| GET /api/v1/agents/:id | AgentCenterPage | ✅ | ✅ | — |
| GET /api/v1/tasks | TaskCenterPage | ✅ | ✅ | — |
| POST /api/v1/tasks | TaskCenterPage | ✅ | ✅ | — |
| PATCH /api/v1/tasks/:id | TaskCenterPage | ✅ | ✅ | — |
| GET /api/v1/projects | ProjectCenterPage | ✅ | ✅ | — |
| POST /api/v1/projects | ProjectCenterPage | ✅ | ✅ | — |
| GET /api/v1/projects/:id | ProjectCenterPage | ✅ | ✅ | — |

## Blocker-Liste

| ID | Endpunkt | Risiko |
|----|----------|--------|
| B-01 | GET/PATCH /api/v1/settings | Settings GUI zeigt Fehler-State |
| B-02 | GET /api/v1/approvals | Approval-Workflow nicht funktionsfähig |
| B-03 | GET /api/v1/audit | Audit-Log leer |
| B-04 | GET /api/v1/governance/status | Governance-Page: Error-State |
| B-05 | PATCH /api/v1/governance/privacy-mode | Privacy-Mode nicht schaltbar |
| B-06 | GET /api/v1/governance/changesets | Change Sets nicht abrufbar |

## Maßnahmen

Alle Blocker erfordern minimale Backend-Stub-Implementierungen, die:
1. Das Result-Pattern zurückgeben
2. Keine Secrets exponieren
3. Riskante Aktionen als Approval weiterleiten
