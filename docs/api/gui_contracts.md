# GUI API Contracts

Alle GUI-Komponenten kommunizieren ausschließlich über diese Endpunkte.
Die GUI greift nie direkt auf Dateien zu, führt nie direkt Tools aus.
Jede Response folgt dem Result-Pattern: `{ok, data}` oder `{ok:false, error:{code,message,status}}`.

## Pflicht-Endpunkte

| Methode | Pfad | Zweck |
|---------|------|-------|
| GET | /api/v1/status | System-Status, Privacy Mode, Gates |
| GET | /api/v1/governance/status | Governance-Status, Admin-Flag |
| GET | /api/v1/security/status | Security-Konfiguration |
| GET | /api/v1/approvals | Ausstehende Freigaben |
| PATCH | /api/v1/approvals/:id | Approve/Reject |
| GET | /api/v1/audit | Audit-Log (SECRET gefiltert) |
| GET | /api/v1/governance/changesets | Change Sets |
| POST | /api/v1/governance/rollback | Rollback (Admin only) |
| GET | /api/v1/governance/rollback-points | Rollback-Punkte |
| GET | /api/v1/governance/policy-decisions | Policy-Entscheidungen |
| GET | /api/v1/agents/executions | Ausführungshistorie |
| GET | /api/v1/collaboration/runs | Collaboration Runs |
| GET | /api/v1/collaboration/teams | Teams |
| GET | /api/v1/collaboration/conflicts | Konflikte |
| GET | /api/v1/settings | Alle Settings-Sektionen |
| PATCH | /api/v1/settings | Settings-Update (sektionsweise) |
| PATCH | /api/v1/settings/secrets | Secret-Felder updaten |
| GET | /api/v1/tools | Tool-Liste |
| PATCH | /api/v1/tools/:id/toggle | Tool aktivieren/deaktivieren |
| GET | /api/v1/tools/:id/health | Health-Check |
| GET | /api/v1/memory | Memory-Einträge (kein SECRET) |
| GET | /api/v1/memory/search | Memory-Suche |
| GET | /api/v1/memory/review-queue | Review-Queue |
| GET | /api/v1/memory/conflicts | Memory-Konflikte |
| GET | /api/v1/rag/documents | RAG-Dokumente |
| POST | /api/v1/rag/documents/:id/reindex | Reindex |
| POST | /api/v1/rag/retrieve | Retrieval-Test |
| GET | /api/v1/agents | Agent-Liste |
| GET | /api/v1/agents/:id | Agent-Detail |
| GET | /api/v1/tasks | Task-Liste |
| POST | /api/v1/tasks | Task erstellen |
| PATCH | /api/v1/tasks/:id | Task-Status |
| GET | /api/v1/projects | Projekt-Liste |
| POST | /api/v1/projects | Projekt erstellen |
| GET | /api/v1/projects/:id | Projekt-Detail |

## Sicherheitsregeln

- Kein Endpoint gibt Secrets zurück
- Kein Endpoint liest Dateien direkt
- Riskante Endpunkte (HIGH/CRITICAL) erzeugen Approval statt Direkt-Ausführung
- Alle Responses Result-Pattern
- SECRET-Dokumente werden nicht als Prompt-Kontext verwendet
- Auth Token wird niemals geloggt

## Response-Formate

### Erfolg (Liste)
```json
{ "items": [...], "total": 42, "page": 1 }
```

### Fehler
```json
{ "error": { "code": "NOT_FOUND", "message": "Ressource nicht gefunden", "status": 404 } }
```

### Settings
```json
{
  "provider": { "model": "gpt-4", "timeout_seconds": 30, "max_retries": 3 },
  "rag": { "chunk_size": 500, "chunk_overlap": 50, "min_score": 0.7, "max_chunks": 10 },
  "agents": { "max_steps": 50, "max_tool_calls": 20, "max_runtime_seconds": 600 },
  "governance": { "approval_expiry_minutes": 60 },
  "collaboration": { "max_agents": 5, "revision_cycles": 3 },
  "security": { "require_approval_for_high": true, "block_critical_by_default": true },
  "memory": { "max_entries": 1000, "decay_rate": 0.1, "auto_review": true },
  "voice": { "enabled": false, "provider": "azure", "language": "de" },
  "ui": { "dark_mode": false, "compact_view": false, "language": "de" }
}
```
