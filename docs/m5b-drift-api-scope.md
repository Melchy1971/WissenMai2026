# M5b Drift Detection — Read-Only API Scope

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; keine Implementierung erlaubt, siehe `reports/current/m5b_implementation_gate.json`).

Maschinenlesbares Schema: `openapi_drift_scope.json`.

---

## Kernprinzip

Die Drift Detection API ist vollständig read-only. Sie liefert Drift Runs, Findings, Summaries und Gate-Ergebnisse. Sie führt keine Mutationen durch. Kein Endpoint setzt `lifecycle_status`, `is_searchable`, löst Reindex aus oder ruft Repair-Aktionen auf.

---

## Endpoints

### GET /api/v1/drift/runs

Listet abgeschlossene DriftRuns des aktuellen Workspace.

**Query Parameters:**

| Parameter | Typ | Pflicht | Default | Constraint |
|-----------|-----|---------|---------|-----------|
| `limit` | integer | nein | 20 | 1..100 |
| `offset` | integer | nein | 0 | >= 0 |

**Response (200):**

```json
{
  "workspace_id": "uuid",
  "total": 42,
  "runs": [
    {
      "run_id": "uuid",
      "started_at": "ISO8601",
      "completed_at": "ISO8601",
      "status": "completed",
      "total_checks": 150,
      "total_drifts": 3,
      "critical_drifts": 0,
      "error_drifts": 2,
      "warning_drifts": 1
    }
  ]
}
```

**Fehlercodes:**

| Code | HTTP | Bedingung |
|------|------|-----------|
| `WORKSPACE_REQUIRED` | 400 | workspace_id fehlt im Auth-Kontext |
| `INVALID_PAGINATION` | 400 | limit/offset ungültig |
| `SERVICE_UNAVAILABLE` | 503 | Drift Report Store nicht erreichbar |

---

### GET /api/v1/drift/runs/{run_id}

Liefert den vollständigen DriftRun inkl. aller Findings.

**Path Parameter:** `run_id` (UUID)

**Response (200):**

```json
{
  "run_id": "uuid",
  "workspace_id": "uuid",
  "started_at": "ISO8601",
  "completed_at": "ISO8601",
  "status": "completed",
  "report_schema_version": 1,
  "metrics": {
    "total_checks": 150,
    "total_drifts": 3,
    "drift_rate": 0.02,
    "critical_drifts": 0,
    "error_drifts": 2,
    "warning_drifts": 1,
    "lifecycle_drift_rate": 0.0,
    "source_status_drift_rate": 0.013,
    "retrieval_drift_rate": 0.0
  },
  "findings": [
    {
      "drift_id": "uuid",
      "entity_type": "document",
      "entity_id": "uuid",
      "drift_type": "SOURCE_STATUS_DRIFT",
      "severity": "error",
      "detected_at": "ISO8601",
      "remediation_hint": "Quelle prüfen; letzter erfolgreicher Sync liegt außerhalb des Toleranzfensters."
    }
  ],
  "gate_decision": "NO_GO"
}
```

**Fehlercodes:**

| Code | HTTP | Bedingung |
|------|------|-----------|
| `DRIFT_RUN_NOT_FOUND` | 404 | run_id nicht im Workspace |
| `WORKSPACE_REQUIRED` | 400 | |

---

### GET /api/v1/drift/findings

Listet Findings über alle Runs des Workspace, mit Filter- und Paginierungsunterstützung.

**Query Parameters:**

| Parameter | Typ | Pflicht | Default | Erlaubte Werte |
|-----------|-----|---------|---------|----------------|
| `limit` | integer | nein | 50 | 1..200 |
| `offset` | integer | nein | 0 | >= 0 |
| `severity` | string | nein | — | info, warning, error, critical |
| `drift_type` | string | nein | — | DOCUMENT_DRIFT, CHUNK_DRIFT, METADATA_DRIFT, LIFECYCLE_DRIFT, SOURCE_STATUS_DRIFT, SEARCH_INDEX_DRIFT, RETRIEVAL_DRIFT |
| `run_id` | uuid | nein | — | Filtert auf einen bestimmten Run |

**Response (200):**

```json
{
  "workspace_id": "uuid",
  "total": 12,
  "findings": [
    {
      "drift_id": "uuid",
      "run_id": "uuid",
      "entity_type": "document",
      "entity_id": "uuid",
      "drift_type": "LIFECYCLE_DRIFT",
      "severity": "error",
      "detected_at": "ISO8601",
      "remediation_hint": "string"
    }
  ]
}
```

**Fehlercodes:**

| Code | HTTP | Bedingung |
|------|------|-----------|
| `WORKSPACE_REQUIRED` | 400 | |
| `INVALID_PAGINATION` | 400 | |
| `INVALID_FILTER` | 400 | Unbekannter severity oder drift_type Wert |

---

### GET /api/v1/drift/summary

Liefert die aktuelle Drift Summary des letzten abgeschlossenen Runs.

**Query Parameters:** keine (workspace aus Auth-Kontext)

**Response (200):**

```json
{
  "workspace_id": "uuid",
  "run_id": "uuid",
  "generated_at": "ISO8601",
  "report_schema_version": 1,
  "metrics": {
    "total_checks": 150,
    "total_drifts": 3,
    "drift_rate": 0.02,
    "critical_drifts": 0,
    "error_drifts": 2,
    "warning_drifts": 1,
    "lifecycle_drift_rate": 0.0,
    "source_status_drift_rate": 0.013,
    "retrieval_drift_rate": 0.0
  },
  "gate_decision": "NO_GO",
  "gate_report_ref": "drift_gate_report.json"
}
```

**Fehlercodes:**

| Code | HTTP | Bedingung |
|------|------|-----------|
| `WORKSPACE_REQUIRED` | 400 | |
| `DRIFT_SUMMARY_NOT_FOUND` | 404 | Kein Run für Workspace vorhanden |

---

## Nicht-Scope (verbotene Endpoints)

| Endpoint | Warum verboten |
|----------|----------------|
| `POST /api/v1/drift/repair` | PROHIBIT-06 |
| `POST /api/v1/drift/reindex` | PROHIBIT-03 |
| `PATCH /api/v1/drift/findings/{id}` | PROHIBIT-05: kein Auto-Close |
| `DELETE /api/v1/drift/runs/{id}` | Immutabilitäts-Invariante |
| `PUT /api/v1/drift/lifecycle` | PROHIBIT-01 |
| `POST /api/v1/drift/cleanup` | PROHIBIT-02/03 |

---

## Workspace-Scoping

Alle Endpoints sind workspace-scoped. Die `workspace_id` stammt ausschließlich aus dem serverseitigen Auth-Kontext. Kein Endpoint akzeptiert `workspace_id` aus Query-String oder Request Body als Vertrauensquelle.

Cross-Workspace-Queries sind nicht erlaubt (Quelle: PROHIBIT-07, `drift_governance.schema.json`).

---

## Authentifizierung

Alle Endpoints erfordern gültige Authentifizierung. Unauthentifizierte Requests erhalten HTTP 401. Workspace-Zugriff ohne Membership ergibt HTTP 403.

---

## Fehlerstandard

Einheitliches Error-Envelope (konsistent mit bestehendem API-Fehlerstandard):

```json
{
  "error": {
    "code": "DRIFT_RUN_NOT_FOUND",
    "message": "Drift run not found in workspace",
    "details": {}
  }
}
```

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `openapi_drift_scope.json` | Maschinenlesbares Schema |
| `reporting_architecture.json` | Report-Typen und Pflichtfelder |
| `drift_governance.schema.json` | PROHIBIT-Regeln |
| `drift_entity_mapping.json` | entity_type-Werte |
| `drift_severity_matrix.json` | Severity-Werte |
