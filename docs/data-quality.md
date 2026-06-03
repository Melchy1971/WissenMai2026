# Data Quality Architektur (M5)

Alle Aussagen, Status und Gates werden ausschliesslich aus maschinenlesbaren Reports abgeleitet:

- Architektur: Siehe `app/models/data_quality.py`, `app/services/data_quality_runner.py`, `app/services/duplicate_detector.py`
- Findings-Modell: Siehe `DataQualityFinding`, `DataQualityRun` (`app/models/data_quality.py`)
- Score: Siehe `data_quality_runner.py` (`_calculate_score`)
- APIs: Siehe `app/api/v1/data_quality.py`, `app/schemas/data_quality.py`
- Dashboard: Siehe `frontend/src/features/data-quality/DataQualityDashboard.jsx`
- M5a Start-Gate: Siehe `reports/current/m5a_start_gate.json`
- Duplicate Detector Gate: Siehe `reports/current/m5a_duplicate_detector_gate.json`
- Metadata Detector Gate: Siehe `reports/current/m5a_metadata_detector_gate.json`
- M5a Gesamtgate: Siehe `reports/current/m5a_data_quality_gate.json`
- M5a Lifecycle Integrity Slice Gate: Siehe `reports/current/m5a_lifecycle_integrity_gate.json`
- Parent-Gate-Hierarchie: Siehe `docs/gate_hierarchy.json`
- CLI: `python scripts/run_data_quality.py --workspace <id>`

## M5a Start-Gate

`reports/current/m5a_start_gate.json` entscheidet nur ueber den Slice-Start. Die M5a-Gesamtfreigabe entsteht nicht aus diesem Start-Gate, sondern aus `reports/current/m5a_data_quality_gate.json` und der Parent-Gate-Hierarchie in `docs/gate_hierarchy.json`.

## Implementierter Scope (M5a Slice-Artefakte)

### Datenmodell (Minimal)

Tabellen `data_quality_runs` und `data_quality_findings` — in Scope.
Tabellen `data_quality_metrics` und `data_quality_snapshots` — deferred.

Migration: `backend/migrations/versions/20260601_0018_m5a_data_quality_minimal.py`, an Kette `20260508_0014` angehaengt.

Felder `data_quality_runs`: `id`, `workspace_id`, `status`, `started_at`, `finished_at`, `total_findings`, `quality_score`, `created_by`.

Felder `data_quality_findings`: `id`, `run_id`, `workspace_id`, `finding_type`, `severity`, `document_id` (nullable), `version_id` (nullable), `chunk_id` (nullable), `title`, `description`, `remediation`, `created_at`.

Constraints: `ck_dq_runs_status`, `ck_dq_findings_severity`, FK auf `workspaces.id` und `users.id`, Cascade-Delete.

Indexe: `workspace_id`, `run_id`, `severity`, `finding_type`.

### Duplicate Detector V1

Erkennt Dokumente mit gleichem `content_hash` innerhalb eines Workspace. Nur aktive Dokumente (`lifecycle_status = active`). Erzeugt Findings vom Typ `DUPLICATE_DOCUMENT`, Severity `warning`.

Remediation: `"Dokumente prüfen und ggf. zusammenführen"`. Keine automatische Reparatur.

**Einschraenkung:** `UniqueConstraint(workspace_id, content_hash)` in der `documents`-Tabelle verhindert in einer schema-konformen DB das Auftreten neuer Duplikate. Der Detector ist fuer historische Daten und Import-Edge-Cases ausgelegt.

### Metadata Quality Detector V1 (Slice 2)

Implementierung: `backend/app/services/metadata_quality_detector.py`

Regeln:

- MQ-1: leerer/Whitespace-Titel → `MISSING_METADATA` (error)
- MQ-2: fehlende/leere `tags` → `MISSING_METADATA` (warning)
- MQ-3: fehlende/leere `category` → `MISSING_METADATA` (warning)
- MQ-4: fehlende/leere `doc_type` → `MISSING_METADATA` (warning)
- MQ-5: fehlende/leere `summary` → `MISSING_METADATA` (info)

Invarianten:

- read-only, keine Dokumentmutation
- workspace-scoped
- nur aktive Dokumente (`lifecycle_status = active`)
- MQ-2..5 nur bei gesetzter `current_version_id`

Nachweise:

- Unit: `backend/tests/test_metadata_quality_detector.py`
- PostgreSQL Truth: `backend/tests/postgres_truth/test_m5a_metadata_quality_truth.py`
- Gate-Nachweis: `reports/current/m5a_metadata_detector_gate.json`

### Lifecycle Integrity Detector V1 (Slice 3)

Implementierung: `backend/app/services/lifecycle_integrity_detector.py`

Abgedeckte Pruefungen:

- archived Dokumente nicht in Search
- deleted Dokumente nicht in Search
- active Dokumente auffindbar
- archived/deleted nicht im neuen Retrieval
- lifecycle_status konsistent mit citation source_status

Nachweise:

- Unit: `backend/tests/test_lifecycle_integrity_detector.py`
- PostgreSQL Truth: `backend/tests/postgres_truth/test_m5a_lifecycle_integrity_truth.py`
- Slice-Gate-Nachweis: `reports/current/m5a_lifecycle_integrity_gate.json`

### Runner

`DataQualityRunner.from_session(session, workspace_id).run()` — startet einen Run, fuehrt Detectoren aus, berechnet Placeholder-Score, schliesst Run ab. Idempotent per `run_id`. Fehler setzen Status auf `failed`.

Keine Dokumentmutationen. Workspace-scoped.

### Read-Only API

Endpunkte unter `/api/v1/data-quality/`:

- `GET /runs` — paginierte Run-Liste
- `GET /runs/{run_id}` — Run-Detail mit Findings-Counts
- `GET /findings` — paginierte Findings mit Filtern: `severity`, `finding_type`, `document_id`, `run_id`
- `GET /summary` — Workspace-Summary mit Score, Counts, Breakdowns

Alle Endpunkte erfordern Auth. Workspace-Isolation durch `require_workspace_member`. Kein POST, kein DELETE, keine Mutationen.

### Dashboard

Route `/data-quality` im Frontend. Zeigt: letzten Run, Quality-Score, Anzahl Findings, Findings nach Severity, Findings nach Typ, Findings-Tabelle mit Filtern und Pagination.

Keine Repair-Buttons, keine Delete-Actions, keine Lifecycle-Aenderungen.

## Scope-Grenzen

Nicht in diesem Slice und ohne separate Governance ausser Scope:

- Cleanup-, Merge- oder Repair-Actions
- Automatische Behebung von Findings
- `data_quality_metrics`, `data_quality_snapshots`
- Lifecycle-Aenderungen durch Data-Quality-Prozesse

## Report-Format (aktuell)

```json
{
  "report_schema_version": 1,
  "report_name": "data_quality_report",
  "generated_by": "run_data_quality_cli",
  "generated_at": "<timestamp>",
  "run_id": "<uuid>",
  "workspace_id": "<uuid>",
  "status": "completed",
  "total_findings": 0,
  "quality_score": "<score>",
  "findings": []
}
```

## Gate-Bezug

- Duplicate Detector Slice: Status siehe `reports/current/m5a_duplicate_detector_gate.json`.
- Metadata Detector Slice: Status siehe `reports/current/m5a_metadata_detector_gate.json`.
- Lifecycle Integrity Slice: Status siehe `reports/current/m5a_lifecycle_integrity_gate.json`.
- Slice-Regel: Ein Slice-Gate bewertet nur den jeweiligen Slice und ersetzt keinen M5a-Gesamt-`PASS`.
- M5a Gesamtgate: Status siehe `reports/current/m5a_data_quality_gate.json`.
- Parent-Gate-Regel: M5a darf nur Gesamt-`PASS` sein, wenn das Parent-Gate `m5a` nach `docs/gate_hierarchy.json` `PASS` ist.
