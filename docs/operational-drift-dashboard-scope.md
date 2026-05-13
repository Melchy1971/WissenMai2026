# Operational Drift Dashboard Scope

Stand: 2026-05-13

## Ziel

Das Operational Drift Dashboard zeigt kontrollierbare Betriebsdrift in produktionsnahen Systemen. Es ist eine read-only Betriebsansicht auf Reports, Metriken und Gate-Artefakte. Es erzeugt keine eigene Wahrheit und gibt keine Reparaturen frei.

Nicht-Scope:

- KI-generierte Health-Erklaerungen
- automatische Reparaturen ohne Audit
- destructive Cleanup
- direkte Reindex-/Restore-/Repair-Buttons
- Anzeige sensitiver Inhalte wie Dokumenttext, Querytext, Citation-Preview, Dateipfade oder Tokens

## Dashboard-Konzept

### Ebenen

| Ebene | Zweck | Anzeige |
|---|---|---|
| Global Overview | Gesamtzustand und blockierende Risiken | Status, letzte Report-Zeitpunkte, Blocker, Trends |
| Workspace View | workspace-spezifische Queue-, Drift-, Orphan- und Cleanup-Signale | Status je Workspace, Counts, Trends, Eskalationsstufe |
| Report Drilldown | Nachvollziehbarkeit ohne Inhalte | Report-ID, Scope, generated_at, Status, Counts, Evidence Links |
| Incident View | Betrieb bei `blocked` oder `degraded` | blockierende Metriken, Runbook-Link, letzte sichere Verifikation |

### Statuslogik

| Status | Bedeutung |
|---|---|
| `ok` | Quelle aktuell, Schwellen eingehalten, kein offener Blocker |
| `watch` | Warnschwelle erreicht, Trend negativ oder Evidenz unvollstaendig |
| `degraded` | wiederholte Warnung, Betriebsqualitaet reduziert oder Drift persistent |
| `blocked` | Integritaets-, Restore-, Isolation-, Truth- oder Datenverlust-Risiko |
| `unknown` | Quelle fehlt, Report veraltet oder Metrik nicht berechenbar |

Dashboard-Status darf nur aus maschinenlesbaren Quellen oder strukturierten Events abgeleitet werden. Wenn eine Quelle fehlt, ist der Status `unknown`, nicht `ok`.

## Drift-Metriken

| Bereich | Metrik | Datenquelle | Aktualisierungsintervall | Severity | Eskalation | Visualisierung |
|---|---|---|---|---|---|---|
| Search Drift | `stale_index_entries`, `index_db_mismatch_count` | Drift Report, Search-Index-Inconsistency API, `reports/m5_entropy/latest.json` | taeglich, nach Upload/Lifecycle/Reindex/Restore | `watch` bei > 0; `blocked` bei persistent > 0 oder Cross-Workspace-Befund | L2 bei erstem Befund; L3 wenn nach Reindex weiter vorhanden | Counter + Trendlinie 24h/7d/30d, rote Badge je Workspace |
| Lifecycle Drift | `lifecycle_searchability_violations` | PostgreSQL Truth Block, Drift Report, Lifecycle/Searchability Probe | taeglich, nach Archive/Delete/Restore/Bulk-Aktion | `blocked` bei aktiven falschen Ausschluessen oder archivierten/geloeschten searchbaren Chunks | L3 sofort; L4 bei neuer Antwort aus geloeschter Quelle | Ampel pro Lifecycle-State + Tabelle mit Counts, keine Dokumenttitel |
| Queue Drift | `stuck_running_jobs`, `queue_state_mismatch_count`, `queue_backlog_age_seconds`, `queue_age_p95`, `workspace_queue_distribution` | Queue-Aging-Report, `background_jobs`, structured queue events | taeglich, stuendlich bei Upload-Spitzen | `watch` bei Backlog > 15, `queue_age_p95` im Warnbereich oder Workspace-Starvation; `degraded` bei > 25; `blocked` bei stale running ohne Recovery | L1 ab Warnbereich; L2 bei Retry-Schleifen oder Starvation; L3 bei blockierter Queue | Age histogram + Status-Buckets + max age sparkline + Workspace-Verteilungsbalken |
| Citation Drift | `citation_status_mismatch_count`, `orphaned_citation_anchor_count`, `citation_completeness` | Citation Longevity Report, PostgreSQL Truth Block, Retrieval Benchmark | taeglich, nach Lifecycle/Rechunk/Cleanup | `watch` bei Snapshot-Abweichung; `blocked` bei verlorener historischer Citation oder falscher neuer Citation | L2 bei Drift; L3 bei Citation-Verlust; L4 bei falscher Antwortquelle | Donut fuer Statusverteilung + Drift-Count + Completeness Trend |
| Backup Freshness | `backup_freshness_seconds`, `last_verified_backup_age` | Backup Manifest, Verify-Backup Report, Restore Truth Report | taeglich, nach jedem Backup, vor Cleanup/Reindex/Migration | `watch` > 6 Tage; `blocked` > 7 Tage oder Verify fehlgeschlagen | L1 bei 6 Tagen; L3 bei 7 Tagen/Verify-Fail | Freshness gauge + letzter Verify-Zeitpunkt + Manifest-Status |
| Restore Status | `restore_success_rate`, `last_restore_status`, `restore_truth_age` | Restore Truth Report, Restore-Dry-Run Report, DR Runbook-Artefakte | woechentlich, vor M5-Gate, nach Backup-Aenderung | `watch` wenn Restore-Nachweis alt; `blocked` wenn letzter Restore fehlgeschlagen | L2 bei veraltetem Nachweis; L3/L4 bei Restore-Fail oder Datenverlustverdacht | Timeline letzter Restore-Laeufe + PASS/FAIL Badges |
| Orphan Growth | `orphan_growth_rate`, `orphan_count_by_type` | Entropy Audit, Data-Quality Report, referenzielle Probes | taeglich, woechentlich im Trend | `watch` bei Wachstum > 0; `blocked` bei persistentem Wachstum oder Citation-Bezug | L2 bei Wachstum; L3 bei Persistenz; L4 bei Datenverlustverdacht | Stacked area nach Orphan-Typ + delta per day |
| Retrieval Quality Trend | `retrieval_quality_score_delta`, `precision_at_5`, `recall_at_5`, `mrr`, `insufficient_context_accuracy` | `reports/m5_retrieval/latest.json`, Golden Query Benchmark | woechentlich, nach Retrieval/Ranking/Index-Aenderung | `watch` bei negativer 7d-Bewegung; `degraded` bei Schwellennaehe; `blocked` bei Lifecycle Violations > 0 | L2 bei Regression; L3 bei Gate-Unterschreitung | Multi-line trend + Schwellenband + Query-ID Drilldown ohne Querytext |
| Queue Retry Trend | `retry_rate_per_hour`, `dead_letter_growth_24h`, `retry_loop_count` | Queue-Aging-Report, `background_jobs.attempt_count`, Replay-Audit | taeglich, stuendlich bei Stoerung | `watch` bei > 5 Retries/Stunde oder Dead-Letter-Wachstum; `degraded` bei steigender Rate in 3 Fenstern; `blocked` bei Dead-Letter-Wachstum ohne Audit | L1 bei Warnung; L2 bei Retry Loop; L3 bei nicht auditierbarem Replay | Rate chart 1h/24h/7d + Dead-Letter counter |
| Cleanup Impact | `cleanup_candidate_count`, `protected_count`, `blocked_count`, `cleanup_applied_count` | Cleanup Dry-Run Report, Cleanup Governance Report, PostgreSQL Cleanup Truth Block | woechentlich, vor Storage-Reduktion, nach Orphan-Befund | `watch` bei Candidate-Wachstum; `blocked` bei `blocked_count > 0` oder Citation-/Queue-Impact | L2 bei blocked candidates; L3 bei destructive Plan ohne Backup; L4 bei Datenverlust | Candidate/protected/blocked stacked bars + Dry-Run/Execute label |

## Eskalationsmodell

| Stufe | Dashboard-Bedingung | Aktion |
|---|---|---|
| L0 Normal | Alle Pflichtmetriken `ok`; Reports aktuell; keine negative 7d-Tendenz | Routinebetrieb, Reports versionieren |
| L1 Watch | Einzelne Warnschwelle, fehlender Trend, Backup nahe Altersgrenze, Queue Backlog > 15 | Woechentlichen Check vorziehen, Befund dokumentieren |
| L2 Degraded | Wiederholte Warnung, Retrieval-Regression, Retry-Schleife, Cleanup-Kandidaten wachsen | Mutierende Wartung pausieren, Root Cause isolieren, Dry-Run-/Audit-Report erzeugen |
| L3 Blocked | Truth-Gate-Fail, Drift > 0 mit Integritaetsrisiko, Backup/Restore-Fail, Orphan Growth persistent, Cleanup blocked_count > 0 | Gate stoppen, Schreib-/Repair-Aktionen einfrieren, Recovery-/DR-Runbook starten |
| L4 Incident | Cross-Workspace-Leak, Datenverlustverdacht, Restore nicht moeglich, falsche Citation aus geloeschter Quelle in neuer Antwort | Sofortige Eskalation, forensische Reports sichern, Restore-/Rollback-Entscheidung mit Zweitreview |

## Visualisierungsregeln

- Jede Kachel zeigt Quelle, `generated_at`, Scope und Status.
- Jede globale Metrik zeigt `workspace_id = null`; workspace-spezifische Metriken zeigen genau eine `workspace_id`.
- Trends verwenden 24h, 7d und 30d, wenn verfuegbar.
- Fehlende Reports werden als `unknown` visualisiert.
- `blocked` steht immer vor aggregierten Durchschnittswerten.
- Drilldowns zeigen IDs, Counts, Status und Runbook-Links, aber keine Inhalte.
- Repair-Hinweise sind Links auf Runbooks oder Dry-Run-Reports, keine direkten Mutationsaktionen.

## Gate-Bezug

Das Dashboard darf keine Freigabeentscheidung alleine treffen. Es darf nur Gate-Artefakte anzeigen und deren maschinenlesbaren Status zusammenfassen.

Ein Dashboard-`ok` ist ungueltig, wenn:

- ein aktueller `postgres_truth`-Report rot ist
- ein Restore-/Backup-Gate fehlt oder rot ist
- eine Drift-Metrik `blocked` meldet
- Pflichtmetriken fehlen
- sensitive Inhalte in Metriken oder Drilldowns auftauchen
