# Data Quality Architektur (M5)

Alle Aussagen, Status und Gates werden ausschliesslich aus maschinenlesbaren Reports abgeleitet:

- Architektur: Siehe `app/models/data_quality.py`, `app/services/data_quality_runner.py`, `app/services/duplicate_detector.py`
- Findings-Modell: Siehe `DataQualityFinding`, `DataQualityRun` (`app/models/data_quality.py`)
- Score: Siehe `data_quality_runner.py` (`_calculate_score`)
- APIs: Siehe `app/api/v1/data_quality.py`, `app/schemas/data_quality.py`
- Dashboard: Siehe `frontend/src/features/data-quality/DataQualityDashboard.jsx`
- M5a Start-Gate: Siehe `reports/current/m5a_start_gate.json`
- Duplicate Detector Gate: Siehe `reports/current/m5a_duplicate_detector_gate.json`
- CLI: `python scripts/run_data_quality.py --workspace <id>`

## M5a Start-Gate

`reports/current/m5a_start_gate.json` entscheidet, ob M5a ueber Vorbereitung hinausgehen darf. Status: `GO`. Implementierungsstart ist freigegeben.

## Implementierter Scope (M5a Duplicate Detector Slice)

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
  "quality_score": 100.0,
  "findings": []
}
```

## Gate-Bezug

Duplicate Detector Gate: `reports/current/m5a_duplicate_detector_gate.json`. Gilt als PASS bei Score >= 90 (8/8 Kriterien).

Ausstehend bis PostgreSQL-Truth-Lauf: `operations_selftest_report.json` und `reindex_recovery_report.json` benoetigen laufenden System-Stack.
