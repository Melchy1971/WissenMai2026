# Workspace-Architektur — PRI-7

Stand: 2026-06-17
Quelle: `reports/current/multi_user_readiness_report.json`

---

## V1-Constraint

Single-User, keine Loginpflicht. Workspace und User-IDs sind in der Datenbank vorhanden, werden aber in V1 nicht enforced. Enforcement folgt in V2.

---

## Datenmodell (IST)

```
Workspace
  └── id, name, created_at

Document          → workspace_id, owner_user_id
Topic             → workspace_id
AnalysisJob       → workspace_id
BackgroundJob     → workspace_id
Export            → workspace_id
DriftRun          → workspace_id
```

Alle primären Entitäten tragen `workspace_id`. `owner_user_id` ist auf `Document` vorhanden.

---

## Repository-Filter (IST)

| Repository | workspace_id Filter | Konsistent |
|-----------|--------------------|-----------:|
| DocumentRepository | ✅ list_documents(), get_document() | Ja |
| TopicRepository | ✅ list_topics() | Ja |
| AnalysisJobRepository | ✅ | Ja |
| ExportRepository | ✅ | Ja |
| SearchRepository | ⚠️ search_unified ohne Guard | **Nein (MU-01)** |
| DriftRepository | ⚠️ nicht alle Methoden | **Nein (MU-02)** |

---

## Lücken

### MU-01: SearchRepository — workspace_id fehlt in search_unified

```python
# IST (search.py):
async def search_unified(self, query: str, limit: int) -> list[SearchResult]:
    topics = await self._search_topics(query)
    docs = await self._search_documents(query)
    # kein workspace_id-Filter

# SOLL:
async def search_unified(self, query: str, workspace_id: str, limit: int) -> list[SearchResult]:
    topics = await self._search_topics(query, workspace_id=workspace_id)
    docs = await self._search_documents(query, workspace_id=workspace_id)
```

### MU-02: DriftRepository — workspace_id nicht konsistent

Methoden `list_drift_runs()` und `get_drift_summary()` prüfen `workspace_id` nicht überall. In V1 unkritisch, da Single-User. In V2 zu korrigieren.

### MU-03: Audit-Log fehlt

Für V2 benötigt: Tabelle `audit_log` mit `(id, workspace_id, user_id, action, resource_type, resource_id, timestamp, ip_address)`.

---

## UserContext-Service (SOLL für V2)

```python
class UserContext:
    user_id: str
    workspace_id: str
    role: str  # admin | member

class WorkspaceContext:
    workspace_id: str
    settings: dict

# Middleware (V2):
async def workspace_scope_middleware(request: Request, call_next):
    token = request.headers.get("Authorization")
    user = await auth_service.verify(token)
    request.state.user_context = UserContext(
        user_id=user.id,
        workspace_id=user.workspace_id,
        role=user.role
    )
    return await call_next(request)
```

In V1: `DEFAULT_USER_ID` und `DEFAULT_WORKSPACE_ID` aus ENV.

---

## Gesamturteil

**MULTI_USER_PREPARED** — Architektur ist für V2 vorbereitet. Keine V1-GA-Blocker. Offene Punkte (MU-01, MU-02, MU-03) sind V2-Pre-Launch-Anforderungen.
