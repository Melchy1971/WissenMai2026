# M5 Observability

Stand: 2026-05-13

M5 erweitert die bestehende JSON-Log-Observability um langfristige Betriebsmetriken. Ziel ist Trendanalyse ueber Queue, Drift, Retrieval, Backup/Restore, Cleanup und Orphans, ohne sensitive Inhalte zu loggen.

Frontend-seitige Telemetry-Governance ist getrennt in `docs/frontend-telemetry-governance.md` definiert. Dieses Dokument bleibt die Betriebs- und Langfrist-Metrikquelle; Frontend-Metriken muessen daran anschlussfaehig sein, ohne Query-, Dokument- oder Chatinhalte zu loggen.

## Metrikdefinitionen

| Metrik | Typ | Einheit | Scope | Fenster | Definition | Warnschwelle | Kritische Schwelle |
|---|---|---|---|---|---|---|---|
| `m5_queue_backlog_age_seconds` | Gauge | Sekunden | Workspace | current, p95, max | Alter des aeltesten Jobs je Queue-Status aus `created_at`, `claimed_at`, `updated_at` | aeltester running Job ueber Timeout oder p95 > 900s | aeltester running Job > 2x Timeout oder max > 3600s |
| `m5_queue_age_p95_seconds` | Gauge | Sekunden | Workspace | current | P95-Alter aller aktiven Queue-Zustaende (`pending`, `running`, `retryable`, `dead_letter`) aus Queue-Aging-Report | > 300s bei pending/retryable Druck | > 600s oder gekoppelt mit stuck running |
| `m5_workspace_queue_distribution` | Gauge | Anteil/Count | Workspace | current | Backlog-Verteilung je Workspace mit Buckets `pending`, `running`, `retryable`, `dead_letter` | ein Workspace dominiert Backlog oder hat stale pending waehrend andere laufen | Starvation mit blockierter Workspace-Fortschrittsgarantie |
| `m5_retry_frequency` | Rate | retries/hour | Workspace | 1h, 24h, 7d | Retry-Versuche je Zeitfenster, Job-Typ und Endstatus | > 5 Retries/Stunde fuer einen Workspace | steigende Retry-Rate in 3 Fenstern oder Dead-Letter-Wachstum |
| `m5_dead_letter_growth` | Counter | Jobs | Workspace | 24h | Neue Dead-Letter-Jobs im letzten 24h-Fenster aus Queue-Aging-Report | > 0 ohne Audit-Kontext | Wachstum plus fehlender Replay-/Recovery-Plan |
| `m5_drift_score` | Gauge | Score | Workspace | current, 24h, 7d | gewichteter Score aus Search-, Lifecycle-, Citation-, Queue-, Backup- und Data-Quality-Drift | > 0 ausserhalb Wartungsfenster | persistenter Drift nach Repair oder Cross-Workspace-Drift |
| `m5_retrieval_quality_trend` | Trend | score_delta | Global | latest, 7d, 30d | Trend von Precision@K, Recall@K, MRR, Citation Completeness und insufficient_context accuracy | negative 7d-Bewegung oder eine Warnschwelle unterschritten | Recall/Citation/Lifecycle-Gate unterschritten |
| `m5_backup_freshness_seconds` | Gauge | Sekunden | Global | current | Alter des letzten erfolgreich verifizierten Backups | > 6 Tage | > 7 Tage oder letzter Verify fehlgeschlagen |
| `m5_restore_success_rate` | Rate | Ratio | Global | 7d, 30d | erfolgreiche Restore-Validierungen / Restore-Validierungsversuche | < 1.0 ueber 30 Tage | letzter Restore-Check fehlgeschlagen |
| `m5_cleanup_impact` | Gauge | Entities | Workspace | dry-run, current, 7d | Dry-run Counts fuer `candidate_count`, `protected_count`, `blocked_count` | `blocked_count > 0` oder unerwartetes Candidate-Wachstum | destructive Plan ohne Backup oder Citation-Impact |
| `m5_orphan_growth_rate` | Rate | orphans/day | Workspace | 24h, 7d, 30d | Wachstum von orphan chunks, versions, files, citations oder index entries | > 0 in einem Fenster | persistent > 0 oder historische Citations betroffen |

Die maschinenlesbare Definition liegt in `backend/app/observability/m5_metrics.py`.

### Quellen und Aggregation

| Metrik | Primaere Quelle | Aggregation | Workspace-Regel |
|---|---|---|---|
| `m5_queue_backlog_age_seconds` | `background_jobs`, Queue-Aging-Report | je Workspace, Job-Status und Job-Typ; p95/max zusaetzlich | Pflicht: genau eine `workspace_id` |
| `m5_queue_age_p95_seconds` | Queue-Aging-Report Feld `queue_age_p95_seconds` | je Workspace; keine Payloads | Pflicht: genau eine `workspace_id` |
| `m5_workspace_queue_distribution` | Queue-Aging-Report Feld `workspace_queue_distribution` | je Workspace und Status-Bucket | globale Sicht erlaubt nur aggregierte Counts |
| `m5_retry_frequency` | `background_jobs.attempts`, Retry-/Replay-Audit | je Workspace, Job-Typ, Ergebnis und Zeitfenster | Pflicht: genau eine `workspace_id` |
| `m5_dead_letter_growth` | Queue-Aging-Report Feld `dead_letter_growth_24h` | je Workspace, 24h-Fenster | Pflicht: genau eine `workspace_id`; Ursache nur als Fehlerklasse |
| `m5_drift_score` | Drift-/Entropy-Report, Data-Quality-Checks | je Workspace und Drift-Art; global nur als aggregierte Summary | Workspace-Events einzeln, globale Summary ohne `workspace_id` |
| `m5_retrieval_quality_trend` | `reports/current/masterplan_status.json` und versionierte Reports | global gegen Golden Dataset; optional workspace-sliced nur ohne Querytext | Global default; workspace-sliced nur mit anonymisierten Counts |
| `m5_backup_freshness_seconds` | Backup-Manifest, Verify-/Restore-Report | global letzter erfolgreich verifizierter Backup-Zeitpunkt | Global: `workspace_id = null` |
| `m5_restore_success_rate` | Restore-Truth-/Verify-Reports | global 7d/30d Erfolgsquote | Global: `workspace_id = null` |
| `m5_cleanup_impact` | Cleanup Dry-Run Report, Cleanup-Governance-Report | je Workspace, Cleanup-Typ und Schutzstatus | Pflicht: genau eine `workspace_id`, ausser globaler Report-Cleanup |
| `m5_orphan_growth_rate` | Entropy-/Data-Quality-Report | je Workspace und Orphan-Typ ueber 24h/7d/30d | Pflicht: genau eine `workspace_id` |

Metriken duerfen aus Reports, strukturierter Laufzeitbeobachtung oder expliziten CLI-Laeufen entstehen. Ein Dashboard darf `pass` nur anzeigen, wenn die zugrunde liegende Quelle aktuell und maschinenlesbar ist.

## Logging-Erweiterungen

Neues strukturiertes Einzelmetrik-Event:

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

Neues Snapshot-Event fuer laengere Trendanalyse:

```json
{
  "event_name": "m5_observability_snapshot",
  "snapshot_id": "20260513T080000Z",
  "generated_at": "2026-05-13T08:00:00Z",
  "source_reports": {
    "longrun": "reports/current/masterplan_status.json",
    "retrieval": "reports/current/masterplan_status.json",
    "entropy": "reports/current/masterplan_status.json"
  },
  "status": "watch",
  "windows": ["current", "24h", "7d", "30d"],
  "metric_count": 8,
  "blocking_findings": [],
  "warnings": ["duplicate_cardinality_not_measured"]
}
```

Pflichtfelder fuer jedes `m5_metric_observed`:

- `event_name`
- `metric_name`
- `value`
- `unit`
- `kind`
- `aggregation_scope`
- `workspace_id`
- `window`
- `status`
- `dimensions`
- `correlation_id`
- `generated_at`
- `metric_version`
- `source`

`status` verwendet nur `ok`, `watch`, `degraded`, `blocked` oder `unknown`.

### Erlaubte Dimensionen

- `job_type`
- `job_status`
- `drift_type`
- `metric_source`
- `operation`
- `result`
- `window`
- `orphan_type`
- `cleanup_type`
- `report_type`

Dimensionen duerfen nur kontrollierte Enum-Werte enthalten. Freitext, Nutzertexte und Dateiangaben sind in Dimensionen verboten.

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
- Workspace-IDs duerfen im Dashboard als ID angezeigt werden, aber nicht mit Dokumenttiteln, Querytexten oder Dateipfaden kombiniert werden.
- Globale Trends duerfen keine Rueckrechnung auf einzelne Nutzer, Dokumente oder Queries ermoeglichen.

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

Langfristige Trendanalyse:

- Jeder Snapshot wird versioniert und fuer 30d-Trends behalten.
- 7d- und 30d-Trends vergleichen nicht nur Endwerte, sondern auch Richtung und Persistenz.
- `watch` entsteht bei unvollstaendiger Messung, negativer Tendenz oder fehlendem aktuellen Report.
- `degraded` entsteht bei wiederholter Schwellennaehe oder drei aufeinanderfolgenden negativen Fenstern.
- `blocked` entsteht bei Datenintegritaetsrisiko, Restore-/Backup-Failure, Orphan-Wachstum, Cross-Workspace-Verletzung oder Gate-relevantem Truth-Fail.
- Baselines duerfen nur mit dokumentiertem Benchmark- oder Gate-Entscheid aktualisiert werden.

## Dashboard-Konzept

### Uebersicht

Kacheln:

- Systemstatus: `ok`, `watch`, `degraded`, `blocked`
- Queue Health: Backlog Age, `queue_age_p95`, Retry Frequency, Dead Letter Growth, Workspace Distribution
- Drift: Drift Score, stale Index Entries, Lifecycle Violations
- Retrieval Quality: Precision@5, Recall@5, MRR, Citation Completeness
- Backup/Restore: Backup Freshness, Restore Success Rate
- Cleanup/Data Quality: Cleanup Impact, Orphan Growth Rate

Jede Kachel zeigt:

- aktuellen Status
- aktueller Wert
- 24h-/7d-/30d-Trend
- Quelle und Report-Zeitpunkt
- letzte erfolgreiche Verifikation
- naechste empfohlene Betriebsaktion

### Workspace-Ansicht

Anzeigen:

- Queue Age je Status und `queue_age_p95`
- Retry-Frequenz je Job-Typ
- Workspace Queue Distribution mit Starvation-Badge
- Dead-Letter Growth 24h
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
- Drilldowns fuer Retrieval zeigen Query-IDs aus dem Golden Dataset, aber keinen Querytext aus Nutzeranfragen.
- Drilldowns fuer Backup/Restore zeigen Manifest-ID, Status, Alter und Checksum-Status, aber keine Dateipfade.
- Drilldowns fuer Cleanup zeigen Candidate-/Protected-/Blocked-Counts und Schutzgruende, aber keine Dokumentinhalte.

### Statusableitung

| Dashboard-Status | Bedingung |
|---|---|
| `ok` | alle Pflichtmetriken aktuell, keine Warn- oder Blockschwelle verletzt |
| `watch` | Trend negativ, Messung unvollstaendig oder Warnschwelle erreicht |
| `degraded` | wiederholte Warnung, Quality-Trend unter Baseline oder Queue/Retry persistiert |
| `blocked` | Drift/Orphan > 0 mit Integritaetsrisiko, Backup/Restore-Failure, Truth-Gate-Fail oder sensitive Logging-Verletzung |
| `unknown` | Report fehlt, Quelle veraltet oder Metrik nicht berechenbar |

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
- Metrik-Snapshots: `geplanter M5-Observability-Report`, spaeter versionierte Snapshots unter `reports/m5_observability/`
- Longrun Quelle: `reports/current/masterplan_status.json`
- Retrieval Quelle: `reports/current/masterplan_status.json`
- Entropy Quelle: `reports/current/masterplan_status.json`
- Drift Repair Regeln: `docs/runbooks/m5-drift-repair-strategy.md`

## Gate-Bezug

Observability darf nur als `pass` gelten, wenn:

- alle acht Pflichtmetriken definiert und berechenbar sind
- Trendfenster fuer 24h, 7d und 30d auswertbar sind oder `unknown` korrekt gesetzt wird
- keine sensitiven Inhalte geloggt werden
- Workspace-Metriken genau eine `workspace_id` tragen
- globale Metriken keine `workspace_id` tragen
- Dashboard-Status aus Reports oder strukturierten Events abgeleitet wird, nicht aus manueller Einschaetzung

