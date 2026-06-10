# M5b Drift Detection — Reporting Architektur

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; keine Implementierung erlaubt, siehe `reports/current/m5b_implementation_gate.json`).

Maschinenlesbares Schema: `reporting_architecture.json`.

---

## Überblick

Die Reporting-Architektur definiert 4 Report-Typen. Jeder Report ist gate-kompatibel: Schema-Version, `generated_by` und `timestamp` sind Pflichtfelder in jedem Report. Reports sind read-only nach Erzeugung; kein Report mutiert Datenbankzustand.

| Report | Zweck | Gate-relevant |
|--------|-------|---------------|
| `drift_report.json` | Vollständige Finding-Liste pro Run und Workspace | ja |
| `drift_summary.json` | Aggregierte Kennzahlen pro Run | ja |
| `drift_history.json` | Trend-Daten über mehrere Runs | nein (diagnostisch) |
| `drift_gate_report.json` | Gate-Entscheidungsgrundlage; minimal, auswertbar | ja (primär) |

---

## Pflichtfelder (alle Reports)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `report_schema_version` | integer | Schema-Versions-Integer; Pflicht für Schema-Registry-Kompatibilität |
| `report_name` | string | Eindeutiger Name des Report-Typs |
| `generated_by` | string | Erzeugendes System oder Prozess; kein Leerstring |
| `timestamp` | ISO 8601 | Erzeugungszeitpunkt; unveränderlich nach Erstellung |
| `workspace_id` | UUID | Workspace-Scope; unveränderlich |
| `run_id` | UUID | FK auf DriftRun |
| `status` | string (enum) | Gesamtstatus des Reports: `ok`, `watch`, `blocked`, `error` |

---

## Report: drift_report.json

**Zweck:** Vollständige, geordnete Liste aller Drift-Findings eines Runs für einen Workspace. Primärquelle für Operator-Analyse.

**Schema-Version:** 1

**Struktur:**

```json
{
  "report_schema_version": 1,
  "report_name": "drift_report",
  "generated_by": "<system>",
  "timestamp": "<iso8601>",
  "workspace_id": "<uuid>",
  "run_id": "<uuid>",
  "status": "ok | watch | blocked | error",
  "total_findings": 0,
  "findings": [
    {
      "drift_id": "<uuid>",
      "drift_type": "<enum>",
      "severity": "<enum>",
      "entity_type": "<enum>",
      "entity_id": "<uuid>",
      "expected_state": {},
      "actual_state": {},
      "remediation_hint": "<string>",
      "created_at": "<iso8601>"
    }
  ],
  "gate_effect": "GO | GO_WITH_WATCH_FLAG | NO_GO | NO_GO_FREEZE"
}
```

**Ordnung der Findings:** `severity` absteigend (critical → error → warning → info), dann `drift_type` alphabetisch.

**Gate-Auswirkung:** Dieser Report ist Gate-relevant; Gate-Validator liest `gate_effect` aus diesem Report.

---

## Report: drift_summary.json

**Zweck:** Aggregierte Kennzahlen pro Run. Maschinenlesbar für Monitoring und Trendanalyse.

**Schema-Version:** 1

**Struktur:**

```json
{
  "report_schema_version": 1,
  "report_name": "drift_summary",
  "generated_by": "<system>",
  "timestamp": "<iso8601>",
  "workspace_id": "<uuid>",
  "run_id": "<uuid>",
  "status": "ok | watch | blocked | error",
  "metrics": {
    "total_checks": 0,
    "total_drifts": 0,
    "critical_drifts": 0,
    "warning_drifts": 0,
    "drift_rate": 0.0,
    "retrieval_drift_rate": 0.0,
    "lifecycle_drift_rate": 0.0,
    "source_status_drift_rate": 0.0
  },
  "findings_by_type": {
    "DOCUMENT_DRIFT": 0,
    "CHUNK_DRIFT": 0,
    "METADATA_DRIFT": 0,
    "LIFECYCLE_DRIFT": 0,
    "SOURCE_STATUS_DRIFT": 0,
    "SEARCH_INDEX_DRIFT": 0,
    "RETRIEVAL_DRIFT": 0
  },
  "findings_by_severity": {
    "info": 0,
    "warning": 0,
    "error": 0,
    "critical": 0
  }
}
```

**Metriken-Referenz:** `drift_metrics.schema.json`

---

## Report: drift_history.json

**Zweck:** Trend-Daten über mehrere DriftRuns eines Workspace. Diagnostisch; nicht für Gate-Entscheidungen verwendet.

**Schema-Version:** 1

**Struktur:**

```json
{
  "report_schema_version": 1,
  "report_name": "drift_history",
  "generated_by": "<system>",
  "timestamp": "<iso8601>",
  "workspace_id": "<uuid>",
  "status": "ok | watch",
  "runs_included": 0,
  "trend_summary": {
    "drift_rate_trend": "stable | increasing | decreasing",
    "retrieval_drift_trend": "stable | increasing | decreasing",
    "lifecycle_drift_trend": "stable | increasing | decreasing",
    "consecutive_negative_retrieval_runs": 0,
    "growing_index_divergence": false
  },
  "run_history": [
    {
      "run_id": "<uuid>",
      "run_timestamp": "<iso8601>",
      "total_drifts": 0,
      "critical_drifts": 0,
      "drift_rate": 0.0,
      "gate_effect": "<enum>"
    }
  ]
}
```

**Gate-Auswirkung:** Kein direkter Gate-Effekt. Trend-Indikatoren können Eskalation zu CRITICAL-Finding triggern (via `drift_severity_matrix.json` Eskalationsregeln).

---

## Report: drift_gate_report.json

**Zweck:** Minimale, auswertbare Gate-Entscheidungsgrundlage. Enthält nur gate-relevante Felder; kein vollständiges Finding-Listing.

**Schema-Version:** 1

**Struktur:**

```json
{
  "report_schema_version": 1,
  "report_name": "drift_gate_report",
  "generated_by": "<system>",
  "timestamp": "<iso8601>",
  "workspace_id": "<uuid>",
  "run_id": "<uuid>",
  "gate": "m5b_drift_gate",
  "gate_decision": "GO | GO_WITH_WATCH_FLAG | NO_GO | NO_GO_FREEZE",
  "criteria": [
    {
      "criterion_id": "DGC-01",
      "name": "no_critical_findings",
      "passed": true,
      "value": 0,
      "threshold": 0,
      "severity_effect": "NO_GO_FREEZE if failed"
    },
    {
      "criterion_id": "DGC-02",
      "name": "no_error_findings",
      "passed": true,
      "value": 0,
      "threshold": 0,
      "severity_effect": "NO_GO if failed"
    },
    {
      "criterion_id": "DGC-03",
      "name": "no_lifecycle_drift",
      "passed": true,
      "value": 0.0,
      "threshold": 0.0,
      "severity_effect": "NO_GO if failed"
    },
    {
      "criterion_id": "DGC-04",
      "name": "no_phantom_chunks",
      "passed": true,
      "value": 0,
      "threshold": 0,
      "severity_effect": "NO_GO_FREEZE if failed"
    },
    {
      "criterion_id": "DGC-05",
      "name": "retrieval_baseline_delta_within_threshold",
      "passed": true,
      "value": 0.0,
      "threshold": 0.05,
      "severity_effect": "NO_GO if exceeded"
    }
  ],
  "blockers": [],
  "watch_flags": []
}
```

**Priorisierung:** Der Gate-Validator liest primär `drift_gate_report.json`; `drift_report.json` ist die Detailquelle für Blocker-Analyse.

---

## Schema Registry

Alle 4 Reports sind in der Schema Registry registriert. Registrierungspflicht: `report_schema_version` muss mit der Registry-Version übereinstimmen. Ein Report mit abweichender `report_schema_version` wird vom Gate-Validator abgelehnt.

| Report | Registry-Key | Aktuelle Version |
|--------|-------------|-----------------|
| drift_report.json | drift_report | 1 |
| drift_summary.json | drift_summary | 1 |
| drift_history.json | drift_history | 1 |
| drift_gate_report.json | drift_gate_report | 1 |

Schema-Registry-Referenz: `schemas/` (Verzeichnis; autoritative Schemata).

---

## Speicherort

| Zustand | Pfad |
|---------|------|
| Aktueller Run | `reports/current/` |
| Historische Runs | `reports/archive/<run_id>/` (Planungsartefakt; Struktur DRAFT) |

`reports/current/` enthält immer den letzten vollständigen Run. Kein Test und kein Prozess außer dem Gate-Validator darf `reports/current/` direkt mutieren.

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `reporting_architecture.json` | Maschinenlesbares Schema |
| `drift_governance.schema.json` | PROHIBIT-08 (kein direktes Schreiben in reports/current/) |
| `drift_metrics.schema.json` | Metriken-Felder in drift_summary.json |
| `drift_severity_matrix.json` | Gate-Effekt-Definitionen |
| `reports/current/m5b_gate_criteria.json` | Gate-Authority |
