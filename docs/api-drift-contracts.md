# Drift API Contract Registry

Version: 1.0.0  
Invariant: Drift Detection darf nur erkennen, nie korrigieren. Alle Endpoints sind GET-only.

---

## Invarianten (alle Contracts)

| Invariante | Wert |
|---|---|
| Auth erforderlich | JWT Bearer Token |
| Workspace-scoped | Ja — alle Ergebnisse auf `workspace_id` des Auth-Tokens beschränkt |
| Read-only | Keine POST/PUT/PATCH/DELETE Endpoints |
| Repair verboten | Keine repair_action in Request oder Response |
| Cleanup verboten | Keine cleanup_action in Request oder Response |
| Auto-Reindex verboten | Keine reindex_action |

---

## C-01: DriftRunListResponse

**Endpoint:** `GET /api/v1/drift/runs`

### Query Parameter

| Parameter | Typ | Pflicht | Default | Constraint |
|---|---|---|---|---|
| `limit` | integer | Nein | 20 | 1–100 |
| `offset` | integer | Nein | 0 | >= 0 |
| `status` | string | Nein | — | Enum: pending, running, completed, failed, completed_with_errors |

### Response Fields

**Required:** `items`, `total`, `limit`, `offset`

`items[]` Required: `run_id`, `workspace_id`, `status`, `started_at`, `created_at`  
`items[]` Optional: `triggered_by`, `detector_names`, `completed_at`, `total_findings`, `error_message`

### Error Codes

| Code | Bedeutung |
|---|---|
| 401 | Kein oder ungültiges Auth-Token |
| 403 | Unzureichende Berechtigungen |
| 422 | Ungültiger Query-Parameter |
| 500 | Interner Fehler |

---

## C-02: DriftRunDetailResponse

**Endpoint:** `GET /api/v1/drift/runs/{run_id}`

### Path Parameter

| Parameter | Typ | Pflicht |
|---|---|---|
| `run_id` | string (UUID) | Ja |

### Response Fields

**Required:** `run_id`, `workspace_id`, `status`, `started_at`, `created_at`, `findings_by_type`, `findings_by_severity`  
**Optional:** `triggered_by`, `detector_names`, `completed_at`, `total_findings`, `error_message`

`findings_by_type` Keys: DOCUMENT_DRIFT, METADATA_DRIFT, LIFECYCLE_DRIFT, SOURCE_STATUS_DRIFT  
`findings_by_severity` Keys: info, warning, error, critical

### Error Codes

| Code | Bedeutung |
|---|---|
| 401 | Kein oder ungültiges Auth-Token |
| 403 | Cross-Workspace-Zugriff |
| 404 | Run nicht gefunden oder anderer Workspace |
| 500 | Interner Fehler |

---

## C-03: DriftFindingListResponse

**Endpoint:** `GET /api/v1/drift/findings`

### Query Parameter

| Parameter | Typ | Pflicht | Default | Constraint |
|---|---|---|---|---|
| `limit` | integer | Nein | 50 | 1–200 |
| `offset` | integer | Nein | 0 | >= 0 |
| `run_id` | string | Nein | — | UUID Filter |
| `severity` | string | Nein | — | Enum (422 bei ungültigem Wert) |
| `finding_type` | string | Nein | — | Enum (422 bei ungültigem Wert) |

**Severity Enum:** info, warning, error, critical  
**Finding Type Enum:** DOCUMENT_DRIFT, METADATA_DRIFT, LIFECYCLE_DRIFT, SOURCE_STATUS_DRIFT

### Response Fields

**Required:** `items`, `total`, `limit`, `offset`  
`items[]` Required: `finding_id`, `run_id`, `workspace_id`, `finding_type`, `severity`, `created_at`  
`items[]` Optional: `entity_type`, `entity_id`, `detail`

### Error Codes

| Code | Bedeutung |
|---|---|
| 401 | Kein oder ungültiges Auth-Token |
| 403 | Unzureichende Berechtigungen |
| 422 | Ungültiger severity- oder finding_type-Wert |
| 500 | Interner Fehler |

---

## C-04: DriftSummaryResponse

**Endpoint:** `GET /api/v1/drift/summary`

### Response Fields

**Required:** `workspace_id`, `total_runs`, `total_findings`, `findings_by_type`, `findings_by_severity`, `critical_count`, `error_count`  
**Optional (null wenn kein Run):** `latest_run_id`, `latest_run_status`, `latest_run_completed_at`

### Error Codes

| Code | Bedeutung |
|---|---|
| 401 | Kein oder ungültiges Auth-Token |
| 403 | Unzureichende Berechtigungen |
| 500 | Interner Fehler |

---

## C-05: DriftErrorResponse

Standard-Fehlerumschlag bei 4xx/5xx.

**Required:** `detail`  
**Optional:** `error_code`, `message`

| Code | Bedeutung |
|---|---|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found oder Workspace-Mismatch |
| 405 | Method Not Allowed (POST/PUT/PATCH/DELETE geblockt) |
| 422 | Unprocessable Entity (ungültiger Enum-Wert) |
| 500 | Internal Server Error |

**Hinweise:**
- 405: Path existiert, aber Methode ist nicht GET
- 404: Path-Pattern existiert nicht
- Kein repair/cleanup/reindex-Inhalt in Fehler-Payloads

---

## Enum Registry

| Enum | Werte |
|---|---|
| `severity` | info, warning, error, critical |
| `finding_type` | DOCUMENT_DRIFT, METADATA_DRIFT, LIFECYCLE_DRIFT, SOURCE_STATUS_DRIFT |
| `run_status` | pending, running, completed, failed, completed_with_errors |
