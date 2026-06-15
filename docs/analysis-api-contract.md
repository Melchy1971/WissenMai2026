# API Contract — Datenanalyse (Task #11)

**Version:** 1.0.0  
**Basis-URL:** `/api/v1`  
**Auth:** Bearer-Token (JWT), Header `Authorization: Bearer <token>`  
**Scope:** Alle Endpunkte sind workspace-scoped. Die `workspace_id` wird aus dem Auth-Kontext extrahiert — kein Query-Parameter.

---

## Statusmodell

```
pending → running → completed → approved
                 ↘           ↘ rejected
                   failed
```

| Status    | Bedeutung |
|-----------|-----------|
| `pending` | Job angelegt, Verarbeitung nicht gestartet |
| `running` | Vergleich oder Zusammenfassung aktiv |
| `completed` | Verarbeitung abgeschlossen, Freigabe ausstehend |
| `failed`  | Verarbeitung fehlgeschlagen (`error_code` gesetzt) |
| `approved` | Ergebnis freigegeben, Vorschläge können übernommen werden |
| `rejected` | Ergebnis abgelehnt (`rejection_reason` gesetzt) |

**Invariante:** Kein Vorschlag aus `AnalysisResult.suggestions` wird ohne explizite Freigabe (`status = approved`) übernommen. Der Endpunkt `/approve` erzwingt diese Regel serverseitig.

---

## Rollenmatrix

| Aktion | `viewer` | `editor` | `admin` |
|--------|----------|----------|---------|
| Job-Liste lesen | ✓ | ✓ | ✓ |
| Job-Detail lesen | ✓ | ✓ | ✓ |
| Job anlegen | — | ✓ | ✓ |
| Vergleich starten | — | ✓ | ✓ |
| Zusammenfassung starten | — | ✓ | ✓ |
| Ergebnis lesen | ✓ | ✓ | ✓ |
| Freigabe erteilen / ablehnen | — | — | ✓ |

Rollen werden über `require_workspace_member(role=...)` in der Auth-Dependency geprüft.

---

## Endpunkte

---

### GET /api/v1/analysis/jobs

Gibt die paginierte Liste aller Analyse-Jobs im aktiven Workspace zurück.

**Query-Parameter**

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `limit` | integer | 20 | Max. Einträge (1–100) |
| `offset` | integer | 0 | Seitenversatz |
| `status` | string | — | Filtert auf einen Status-Wert |

**Request**  
Kein Body.

**Response 200**

```json
{
  "items": [
    {
      "id": "job-uuid",
      "workspace_id": "ws-uuid",
      "created_by_user_id": "user-uuid",
      "status": "completed",
      "title": "Vergleich Vertrag v1 vs v2",
      "base_document_id": "doc-uuid-a",
      "compare_document_id": "doc-uuid-b",
      "created_at": "2026-06-12T08:00:00Z",
      "updated_at": "2026-06-12T08:05:00Z",
      "approved_at": null,
      "approval_decision": null
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

**Fehler**

| Code | HTTP | Bedeutung |
|------|------|-----------|
| `UNAUTHORIZED` | 401 | Kein oder ungültiges Token |
| `FORBIDDEN` | 403 | Kein Workspace-Mitglied |

---

### POST /api/v1/analysis/jobs

Legt einen neuen Analyse-Job an. Status initial: `pending`.

**Mindestrolle:** `editor`

**Request Body**

```json
{
  "title": "Vergleich Vertrag v1 vs v2",
  "description": "Datenschutzrelevante Änderungen prüfen",
  "base_document_id": "doc-uuid-a",
  "compare_document_id": "doc-uuid-b"
}
```

| Feld | Pflicht | Beschreibung |
|------|---------|--------------|
| `title` | Ja | 1–256 Zeichen |
| `description` | Nein | bis 1024 Zeichen |
| `base_document_id` | Ja | Muss im Workspace vorhanden sein |
| `compare_document_id` | Nein | Zweites Dokument für Differenzanalyse |

**Response 201** — `AnalysisJobResponse` (vollständiger Job, `result: null`)

**Fehler**

| Code | HTTP | Bedeutung |
|------|------|-----------|
| `UNAUTHORIZED` | 401 | — |
| `FORBIDDEN` | 403 | Rolle < `editor` |
| `DOCUMENT_NOT_FOUND` | 404 | `base_document_id` nicht im Workspace |
| `DOCUMENT_NOT_FOUND` | 404 | `compare_document_id` nicht im Workspace |
| `VALIDATION_ERROR` | 422 | Pflichtfelder fehlen oder ungültig |

---

### GET /api/v1/analysis/jobs/{job_id}

Gibt den vollständigen Job zurück, einschließlich eingebettetem `result` sobald vorhanden.

**Path-Parameter:** `job_id` (UUID)

**Response 200** — `AnalysisJobResponse`

```json
{
  "id": "job-uuid",
  "workspace_id": "ws-uuid",
  "created_by_user_id": "user-uuid",
  "status": "completed",
  "title": "Vergleich Vertrag v1 vs v2",
  "description": "Datenschutzrelevante Änderungen prüfen",
  "base_document_id": "doc-uuid-a",
  "compare_document_id": "doc-uuid-b",
  "created_at": "2026-06-12T08:00:00Z",
  "updated_at": "2026-06-12T08:05:00Z",
  "started_at": "2026-06-12T08:01:00Z",
  "completed_at": "2026-06-12T08:05:00Z",
  "error_code": null,
  "error_message": null,
  "approved_by_user_id": null,
  "approved_at": null,
  "approval_decision": null,
  "rejection_reason": null,
  "result": null
}
```

`result` ist `null` solange `status ∈ {pending, running, failed}`.

**Fehler**

| Code | HTTP | Bedeutung |
|------|------|-----------|
| `UNAUTHORIZED` | 401 | — |
| `FORBIDDEN` | 403 | Job gehört zu anderem Workspace |
| `JOB_NOT_FOUND` | 404 | Job-ID existiert nicht |

---

### POST /api/v1/analysis/jobs/{job_id}/compare

Startet den Vergleichsschritt. Setzt `status → running`.  
Voraussetzung: `compare_document_id` im Job gesetzt, aktueller Status `pending`.

**Mindestrolle:** `editor`

**Request Body**

```json
{
  "mode": "full",
  "max_differences": 50
}
```

| Feld | Default | Beschreibung |
|------|---------|--------------|
| `mode` | `"full"` | `semantic` / `structural` / `full` |
| `max_differences` | 50 | 1–200 |

**Response 202** — `AnalysisJobResponse` mit `status: "running"`

**Fehler**

| Code | HTTP | Bedeutung |
|------|------|-----------|
| `UNAUTHORIZED` | 401 | — |
| `FORBIDDEN` | 403 | Rolle < `editor` |
| `JOB_NOT_FOUND` | 404 | — |
| `JOB_INVALID_STATE` | 409 | Status ≠ `pending` |
| `COMPARE_DOCUMENT_MISSING` | 422 | Kein `compare_document_id` im Job |

---

### POST /api/v1/analysis/jobs/{job_id}/summarize

Startet die KI-Zusammenfassung und Vorschlagsgenerierung.  
Voraussetzung: Status `pending` oder `completed` (Re-Summarize möglich).

**Mindestrolle:** `editor`

**Request Body**

```json
{
  "focus": "Datenschutzrelevante Änderungen",
  "max_suggestions": 10
}
```

| Feld | Default | Beschreibung |
|------|---------|--------------|
| `focus` | `null` | Optionaler Fokushinweis (bis 512 Zeichen) |
| `max_suggestions` | 10 | 1–50 |

**Response 202** — `AnalysisJobResponse` mit `status: "running"`

**Fehler**

| Code | HTTP | Bedeutung |
|------|------|-----------|
| `UNAUTHORIZED` | 401 | — |
| `FORBIDDEN` | 403 | Rolle < `editor` |
| `JOB_NOT_FOUND` | 404 | — |
| `JOB_INVALID_STATE` | 409 | Status ∈ `{running, approved, rejected}` |

---

### POST /api/v1/analysis/jobs/{job_id}/approve

Erteilt oder verweigert die Freigabe.  
Voraussetzung: Status `completed`.  
**Mindestrolle:** `admin`

**Request Body**

```json
{
  "decision": "approved",
  "reason": null
}
```

| Feld | Pflicht | Beschreibung |
|------|---------|--------------|
| `decision` | Ja | `approved` oder `rejected` |
| `reason` | Bedingt | Pflicht bei `decision = rejected` |

**Response 200** — `AnalysisJobResponse` mit `status: "approved"` oder `"rejected"`

**Fehler**

| Code | HTTP | Bedeutung |
|------|------|-----------|
| `UNAUTHORIZED` | 401 | — |
| `FORBIDDEN` | 403 | Rolle < `admin` |
| `JOB_NOT_FOUND` | 404 | — |
| `JOB_INVALID_STATE` | 409 | Status ≠ `completed` |
| `REJECTION_REASON_REQUIRED` | 422 | `decision = rejected` ohne `reason` |

---

### GET /api/v1/analysis/jobs/{job_id}/result

Gibt das vollständige Analyseergebnis zurück.  
Voraussetzung: Status `completed` oder `approved`.

**Response 200** — `AnalysisResult`

```json
{
  "job_id": "job-uuid",
  "summary": "Die Änderungen betreffen hauptsächlich §3 und §7...",
  "key_findings": [
    "Löschfristen in §3 von 90 auf 30 Tage verkürzt",
    "Neuer Abschnitt zu Auftragsverarbeitung in §7 hinzugefügt"
  ],
  "comparison": {
    "job_id": "job-uuid",
    "base_document_id": "doc-uuid-a",
    "compare_document_id": "doc-uuid-b",
    "differences": [
      {
        "type": "modified",
        "section": "§3 Abs. 2",
        "base_text": "Die Daten werden 90 Tage gespeichert.",
        "compare_text": "Die Daten werden 30 Tage gespeichert.",
        "significance": "high",
        "chunk_id": "chunk-uuid-1"
      }
    ],
    "similarity_score": 0.87,
    "chunks_analyzed": 42,
    "created_at": "2026-06-12T08:04:00Z"
  },
  "suggestions": [
    {
      "id": "sug-uuid-1",
      "job_id": "job-uuid",
      "category": "compliance",
      "title": "Löschfrist prüfen",
      "rationale": "Verkürzung von 90 auf 30 Tage erfordert Anpassung der internen Richtlinie...",
      "priority": "high",
      "base_text": "Die Daten werden 90 Tage gespeichert.",
      "proposed_text": "Die Daten werden 30 Tage gespeichert — interne Richtlinie anpassen."
    }
  ],
  "total_suggestions": 1,
  "approval_required": true,
  "created_at": "2026-06-12T08:05:00Z"
}
```

**Fehler**

| Code | HTTP | Bedeutung |
|------|------|-----------|
| `UNAUTHORIZED` | 401 | — |
| `FORBIDDEN` | 403 | Job nicht im eigenen Workspace |
| `JOB_NOT_FOUND` | 404 | — |
| `RESULT_NOT_READY` | 409 | Status ∈ `{pending, running, failed}` |

---

## Fehlerformat

Alle Fehlerantworten folgen dem globalen Schema:

```json
{
  "error": {
    "code": "JOB_INVALID_STATE",
    "message": "Job kann nur aus Status 'completed' freigegeben werden.",
    "details": {
      "current_status": "running",
      "required_status": "completed"
    }
  }
}
```

---

## Datenmodelle (Kurzreferenz)

### AnalysisJob (vollständig)
Alle Felder aus `AnalysisJobResponse` (siehe Schemas). `result` ist eingebettet.

### AnalysisResult
Enthält `summary`, `key_findings`, optionales `comparison`, `suggestions[]`.  
`approval_required` ist immer `true` — serverseitig unveränderlich.

### AnalysisComparison
Enthält `differences[]` (vom Typ `ComparisonDifference`), `similarity_score`, `chunks_analyzed`.

### AnalysisSuggestion
Enthält `category`, `title`, `rationale`, `priority`, optionale `base_text` / `proposed_text`.

---

## Async-Verhalten

`/compare` und `/summarize` antworten mit **202 Accepted**. Die Verarbeitung läuft asynchron.  
Der Client pollt `GET /api/v1/analysis/jobs/{job_id}` bis `status ∈ {completed, failed}`.  
Empfohlenes Poll-Intervall: 1s (erste 10s), danach 5s.

---

*Letzte Aktualisierung: 2026-06-12*
