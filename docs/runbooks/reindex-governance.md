# Reindex Governance

Stand: 2026-05-13

Reindex ist eine mutierende Betriebsaktion mit direkter Wirkung auf Search, RAG-Ranking, Lifecycle-Sichtbarkeit und Recovery-Nachweise. Jeder Reindex ist deshalb ein kontrollierter Governance-Vorgang, kein stiller Repair-Schritt.

## Governance-Regeln

| Regel | Pflicht | Nachweis |
|---|---|---|
| Tracking | Jeder Reindex braucht eine `correlation_id`. Fehlt sie im Request, erzeugt der Governed-Reindex-Service eine UUID. | Feld `correlation_id` im `ReindexGovernanceReport` |
| Audit | Jeder Reindex erzeugt Start- und Completion-Event. | `audit_event_names = ["reindex_governance_started", "reindex_governance_completed"]`, `audit_event_count = 2` |
| Drift Snapshot | Vor und nach dem Reindex wird Search-Drift gemessen. | `drift_score_before`, `drift_score_after`, `drift_delta`, `drift_snapshot_before_taken`, `drift_snapshot_after_taken` |
| Lifecycle Check | Nach dem Reindex wird Lifecycle/Searchability-Konsistenz geprüft. | `lifecycle_ok`, `lifecycle_inconsistency_count` |
| Retrieval Regression | Nach jedem Reindex ist der Retrieval-Benchmark mit Trigger `reindex` Pflicht. | `regression_check_required = true`, `retrieval_regression_trigger = "reindex"` |
| Scope-Minimierung | `document` vor `workspace`, `workspace` vor `full`, sofern der Befund das erlaubt. | `reindex_type`, `workspace_id`, `document_id`, `reason` |
| Report-Wahrheit | Reindex-Status darf nur aus maschinenlesbarem Report und nachgelagerten Checks abgeleitet werden. | `ReindexGovernanceReport`, Retrieval-Regression-Report, Drift-Report |

## Reindex-Typen

| Typ | Scope | Zulassung | Verbotene Parameter | Typischer Anlass |
|---|---|---|---|---|
| `document` | ein Dokument | Wenn Drift oder Rechunking auf ein Dokument begrenzt ist | ohne `document_id` | Dokument-Rechunk, einzelner Lifecycle-Fix |
| `workspace` | ein Workspace | Wenn mehrere Dokumente eines Workspaces betroffen sind | ohne `workspace_id`, mit `document_id` | Workspace-Drift, Restore eines Workspaces |
| `full` | gesamter Index | Nur Wartungsfenster, Restore-Folge oder Index-Migration | mit `workspace_id` oder `document_id` | globaler Restore, Indexschema-Wechsel |

## Audit-Regeln

Pflichtfelder im Audit-Kontext:

- `correlation_id`
- `reindex_type`
- `workspace_id` oder `null`
- `document_id` oder `null`
- `reason`
- `started_at`
- `completed_at`
- `duration_ms`
- `status`

Pflicht-Events:

| Event | Zeitpunkt | Status | Zweck |
|---|---|---|---|
| `reindex_governance_started` | nach Constraint-Prüfung und Lock-Erwerb, vor Drift-Snapshot | `started` | beweist kontrollierten Start |
| `reindex_governance_completed` | nach Rebuild, Drift-Snapshot und Lifecycle-Prüfung | `completed` | beweist kontrollierten Abschluss |

Verboten:

- Reindex ohne `ReindexGovernanceService.run_governed_reindex`
- Repair-Reindex ohne Audit-Event
- manuelle Dokumentation eines grünen Reindex ohne Report
- Reindex als Ersatz für ungeklärte Lifecycle-, Workspace- oder Citation-Fehler

## Safety Constraints

| Constraint | Regel | Eskalation |
|---|---|---|
| Keine parallelen Full-Reindexe | `full` nutzt globalen Reindex-Lock `__global__`. Ein zweiter Full-Reindex muss blockieren. | L3 Blocked bei Lock-Bypass |
| Kein untracked Repair-Reindex | Jeder Repair-Reindex muss über Governed-Reindex laufen. | L3 Blocked, wenn Audit fehlt |
| Scope-Korrektheit | `full` ohne IDs, `workspace` genau mit `workspace_id`, `document` mit `document_id`. | Request ablehnen |
| Drift nachher nicht ignorieren | `drift_score_after > 0` ist kein grüner Abschluss. | Drift-Repair-Runbook, kein weiteres mutierendes Repair ohne Review |
| Lifecycle verletzt | `lifecycle_ok = false` blockiert Freigabe. | Schreib-/Reindex-Fenster pausieren, Ursache isolieren |
| Retrieval Regression offen | Reindex bleibt operativ `pending_validation`, bis Retrieval Regression Check gelaufen ist. | Keine Baseline-Aktualisierung, keine Freigabe |
| Backup/Restore-Kontext | Full-Reindex vor riskanten Datenoperationen nur mit aktuellem Backup-/Restore-Nachweis. | L3 bei fehlendem Nachweis |

## Pflichtprozess

1. Anlass und kleinsten Scope bestimmen.
2. Backup-/Restore-Nachweis prüfen, wenn `full` oder restore-naher Reindex.
3. Governed Reindex starten, niemals direkten Repair-Reindex.
4. Report prüfen: Audit-Events, Drift-Snapshots, Lifecycle-Konsistenz.
5. Danach Retrieval Regression Check mit Trigger `reindex` ausführen.
6. Drift Detection nachgelagert erneut bewerten.
7. Status nur dann `completed_validated`, wenn Drift, Lifecycle und Retrieval Regression grün sind.

## Freigabestatus

| Status | Bedeutung |
|---|---|
| `blocked` | Constraint verletzt, Lock nicht verfügbar, Audit fehlt oder Scope ungültig |
| `completed_pending_validation` | Reindex technisch abgeschlossen, Retrieval Regression noch offen |
| `completed_validated` | Reindex, Drift Detection, Lifecycle Check und Retrieval Regression grün |
| `failed` | Reindex oder Nachprüfung fehlgeschlagen |

