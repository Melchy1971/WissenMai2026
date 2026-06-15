# Dashboard V3 API Contract

Stand: 2026-06-12

Alle Endpunkte sind workspace-scoped, auth-pflichtig und read-only. Responses enthalten keine Gate-/Debug-Daten und keine internen Reports.

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/v1/dashboard/summary` | Aggregierte Dashboard-Kennzahlen |
| GET | `/api/v1/dashboard/activity` | Letzte sichtbare Workspace-Aktivitaeten |
| GET | `/api/v1/dashboard/imports` | Import-Uebersicht |
| GET | `/api/v1/dashboard/analysis` | Analyse-Uebersicht |
| GET | `/api/v1/dashboard/quality` | Quality-Uebersicht |
| GET | `/api/v1/dashboard/topics` | Themen-Uebersicht |

## Summary Schema

```json
{
  "document_count": 0,
  "new_imports_count": 0,
  "open_analysis_count": 0,
  "topic_count": 0,
  "quality_score": null,
  "drift_status": "unknown"
}
```

## Pydantic Schemas

Implementiert in `backend/app/schemas/dashboard.py`:

- `DashboardSummary`
- `DashboardListResponse`

