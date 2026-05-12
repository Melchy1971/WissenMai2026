# M5 Observability

Stand: 2026-05-12

M5 erweitert die bestehende JSON-Log-Observability um langfristige Betriebsmetriken. Ziel ist Trendanalyse ueber Queue, Drift, Retrieval, Backup/Restore, Cleanup und Orphans, ohne sensitive Inhalte zu loggen.

## Metrikdefinitionen

| Metrik | Typ | Einheit | Scope | Fenster | Definition | Warnschwelle | Kritische Schwelle |
|---|---|---|---|---|---|---|---|
| `m5_queue_backlog_age_seconds` | Gauge | Sekunden | Workspace | current, p95, max | Alter des aeltesten Jobs je Queue-Status aus `created_at`, `claimed_at`, `updated_at` | aeltester running Job ueber Timeout oder p95 > 900s | aeltester running Job > 2x Timeout oder max > 3600s |
| `m5_retry_frequency` | Rate | retries/hour | Workspace | 1h, 24h, 7d | Retry-Versuche je Zeitfenster, Job-Typ und Endstatus | > 5 Retries/Stunde fuer einen Workspace | steigende Retry-Rate in 3 Fenstern oder Dead-Letter-Wachstum |
| `m5_drift_score` | Gauge | Score | Workspace | current, 24h, 7d | gewichteter Score aus Search-, Lifecycle-, Citation-, Queue-, Backup- und Data-Quality-Drift | > 0 ausserhalb Wartungsfenster | persistenter Drift nach Repair oder Cross-Workspace-Drift |
| `m5_retrieval_quality_trend` | Trend | score_delta | Global | latest, 7d, 30d | Trend von Precision@K, Recall@K, MRR, Citation Completeness und insufficient_context accuracy | negative 7d-Bewegung oder eine Warnschwelle unterschritten | Recall/Citation/Lifecycle-Gate unterschritten |
| `m5_backup_freshness_seconds` | Gauge | Sekunden | Global | current | Alter des letzten erfolgreich verifizierten Backups | > 6 Tage | > 7 Tage oder letzter Verify fehlgeschlagen |
| `m5_restore_success_rate` | Rate | Ratio | Global | 7d, 30d | erfolgreiche Restore-Validierungen / Restore-Validierungsversuche | < 1.0 ueber 30 Tage | letzter Restore-Check fehlgeschlagen |
| `m5_cleanup_impact` | Gauge | Entities | Workspace | dry-run, current, 7d | Dry-run Counts fuer `candidate_count`, `protected_count`, `blocked_count` | `blocked_count > 0` oder unerwartetes Candidate-Wachstum | destructive Plan ohne Backup oder Citation-Impact |
| `m5_orphan_growth_rate` | Rate | orphans/day | Workspace | 24h, 7d, 30d | Wachstum von orphan chunks, versions, files, citations oder index entries | > 0 in einem Fenster | persistent > 0 oder historische Citations betroffen |

Die maschinenlesbare Definition liegt in `backend/app/observability/m5_metrics.py`.

## Logging-Erweiterungen

Neues strukturiertes Event:

```json
{
  "event_name": "m5_metric_observed",
  "metric_name": "m5_queue_backlog_age_seconds",
  "value": 120,
  "unit": "seconds",
  "kind": "gauge",
  "aggregation_scope": "workspace",
  "workspace_id": "workspace-...",
  "window": "current",
  "status": "ok",
  "dimensions": {
    "job_status": "running"
  },
  "correlation_id": "..."
}
```

### Erlaubte Dimensionen

- `job_type`
- `job_status`
- `drift_type`
- `metric_source`
- `operation`
- `result`
- `window`

### Verbotene Felder

Nicht loggen:

- Dokumenttexte
- Chunktexte
- Queries
- Dateipfade
- Dateinamen
- komplette freie Metadaten
- Tokens oder Secrets
- `user_id` in M5-Aggregationsmetriken
- Citation-Quote-Previews

Workspace-Aggregation:

- Workspace-Metriken tragen genau eine `workspace_id`.
- Globale Metriken muessen `workspace_id = null` setzen.
- Keine Metrik darf mehrere Workspaces in einem Event mischen.
- Cross-Workspace-Auswertungen erfolgen nur ueber aggregierte Dashboard-Queries, nicht ueber ein einzelnes Roh-Event.

## Trendanalyse

Trendfenster:

- kurzfristig: 1h oder aktueller Lauf
- taeglich: 24h
- woechentlich: 7d
- release-/readiness-relevant: 30d

Trendregeln:

- Ein einzelner Ausreisser erzeugt `watch`, wenn kein Datenintegritaetsrisiko besteht.
- Persistenz ueber 3 Fenster eskaliert auf `degraded`.
- Drift, Orphans, Backup-Failures oder Cross-Workspace-Leaks eskalieren sofort auf `blocked`.
- Retrieval-Qualitaet wird gegen die letzte gruen akzeptierte Golden-Baseline verglichen.
- Cleanup bleibt dry-run-basiert; Impact-Trends duerfen keine Loeschfreigabe ersetzen.

## Dashboard-Konzept

### Uebersicht

Kacheln:

- Systemstatus: `ok`, `watch`, `degraded`, `blocked`
- Queue Health: Backlog Age, Retry Frequency, Dead Letter Count
- Drift: Drift Score, stale Index Entries, Lifecycle Violations
- Retrieval Quality: Precision@5, Recall@5, MRR, Citation Completeness
- Backup/Restore: Backup Freshness, Restore Success Rate
- Cleanup/Data Quality: Cleanup Impact, Orphan Growth Rate

### Workspace-Ansicht

Anzeigen:

- Queue Age je Status
- Retry-Frequenz je Job-Typ
- Drift Score je Drift-Art
- Cleanup Dry-Run Counts
- Orphan Growth Rate

Nicht anzeigen:

- Dokumenttext
- Querytext
- Citation-Preview
- Dateipfade
- Nutzeridentitaeten

### Global-Ansicht

Anzeigen:

- Retrieval Quality Trend
- Backup Freshness
- Restore Success Rate
- Gesamtzahl Workspaces in `watch/degraded/blocked`
- Top-N Workspaces nach aggregiertem Health-Risiko, ohne Inhalte

### Drilldown-Regeln

- Drilldown darf IDs und Counts zeigen, aber keine Inhalte.
- Repair-Links zeigen auf Dry-Run-/Audit-Reports, nicht direkt auf destructive Actions.
- Jede mutierende Folgeaktion braucht separates Runbook, Audit und Freigabe.

## Alerting

| Alert | Bedingung | Stufe | Aktion |
|---|---|---|---|
| Queue Age hoch | `m5_queue_backlog_age_seconds` im Warnbereich | L1 Watch | Queue Health Check vorziehen |
| Queue blockiert | kritische Queue Age oder Dead-Letter-Wachstum | L2/L3 | Uploads pausieren, Replay/Repair-Runbook |
| Drift sichtbar | `m5_drift_score > 0` ausserhalb Wartung | L2 | Drift-Check wiederholen, Repair Dry-Run |
| Drift persistent | Drift nach Repair oder Cross-Workspace-Drift | L3/L4 | Schreibbetrieb stoppen, Incident-Pfad |
| Retrieval Regression | Golden-Baseline unterschritten | L2 | Retrieval Benchmark isolieren, Index/Data Quality pruefen |
| Backup alt | Backup-Freshness > 6 Tage | L1 | Backup verifizieren oder neu erzeugen |
| Backup kritisch | Backup-Freshness > 7 Tage oder Verify failed | L3 | Gate stoppen, Backup/DR-Runbook |
| Cleanup Risiko | `blocked_count > 0` | L2 | Cleanup blockieren, Schutzregeln pruefen |
| Orphan Growth | Growth Rate > 0 | L2/L3 | Data Quality Audit, nicht destruktiver Repair-Plan |

## Implementierungsanker

- Metrikdefinitionen: `backend/app/observability/m5_metrics.py`
- Strukturierte Logs: `backend/app/observability/logging.py`
- Longrun Quelle: `reports/m5_longrun/latest.json`
- Retrieval Quelle: `reports/m5_retrieval/latest.json`
- Entropy Quelle: `reports/m5_entropy/latest.json`
- Drift Repair Regeln: `docs/runbooks/m5-drift-repair-strategy.md`
