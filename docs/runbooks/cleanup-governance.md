# Cleanup Governance

Stand: 2026-05-13

Cleanup ist eine potentiell destruktive Betriebsaktion. Jede Cleanup-Ausführung muss beweisen, dass aktive Daten, historische Citations und Queue-Konsistenz nicht still beschädigt werden.

## Cleanup Governance

| Regel | Pflicht | Nachweis |
|---|---|---|
| Dry Run zuerst | Jeder Cleanup führt immer zuerst `dry_run` aus, auch wenn Ausführung angefordert wurde. | `dry_run_executed = true`, `dry_run_candidate_count` |
| Audit Trail | Start und Abschluss werden strukturiert geloggt. | `audit_event_names`, `audit_event_count = 2`, `correlation_id` |
| Keine aktiven Dokumente löschen | Active Documents und active searchable Chunks dürfen nicht sinken. | `safety_constraints.active_documents_preserved` |
| Keine Citations zerstören | Citation Count darf nicht sinken; historische Snapshots sind protected. | `delta.citation_loss_detected = false`, `safety_constraints.citations_preserved` |
| Keine Queue-Konsistenz verletzen | Running Jobs blockieren Cleanup; aktive Queue-Jobs dürfen nicht sinken. | `safety_gates.active_job_refs_in_scope`, `safety_constraints.queue_consistency_preserved` |
| Vorher/Nachher Report | Jeder Cleanup erzeugt Snapshots vor und nach dem Lauf. | `snapshot_before`, `snapshot_after` |
| Drift Delta | Jeder Cleanup erzeugt ein Delta über die geschützten Zähler. | `delta`, `drift_delta` |
| Recovery Hinweis | Jeder Cleanup enthält konkrete Recovery-Hinweise. | `recovery_hints`, `recovery_required` |
| Rollback-Strategie | Jeder Report enthält Rollback-/Restore-Strategie. | `rollback_strategy` |

## Audit-Strategie

Pflichtfelder im Cleanup-Governance-Report:

- `correlation_id`
- `mode`: `dry_run`, `execute` oder `blocked`
- `governance_rules`
- `audit_event_names`
- `audit_event_count`
- `dry_run_executed`
- `safety_gates`
- `snapshot_before`
- `snapshot_after`
- `delta`
- `drift_delta`
- `safety_constraints`
- `recovery_hints`
- `rollback_strategy`

Pflicht-Events:

| Event | Status | Zeitpunkt |
|---|---|---|
| `cleanup_governance_started` | `started` | vor Safety-Gates und Dry Run |
| `cleanup_governance_completed` | `completed` oder `blocked` | nach Dry Run, optional Execute, Snapshots und Delta |

## Safety Constraints

| Constraint | Blockiert Execute? | Begründung |
|---|---|---|
| aktive Dokumente im Orphan-Scope | ja | Cleanup könnte Primärdaten löschen |
| Running Jobs im Scope | ja | Queue-Referenzen und Temp-Dateien können noch gebraucht werden |
| Citation Loss im Delta | ja für Freigabe, kritisch nach Befund | historische Antworten wären beschädigt |
| Citation-Verweise im Orphan-Scope | Warnung | `chunk_id` kann unverifizierbar werden; Citation selbst darf nicht gelöscht werden |
| Missing Backup vor destructive Cleanup | ja, operativ | Rollback hängt von Restore ab |

## Prozess

1. Cleanup nur über `CleanupGovernanceService` oder `POST /api/v1/admin/cleanup/governed`.
2. Standard bleibt `dry_run_only = true`.
3. Dry-Run-Report prüfen: Candidate Count, Protected Count, Blocked Count.
4. Safety-Gates prüfen: keine aktiven Dokumente, keine Running Jobs.
5. Vor Ausführung Backup-/Restore-Nachweis prüfen.
6. Execute nur mit separater technischer Freigabe.
7. Nach Execute: `drift_delta`, Citation Longevity, Queue Aging und Retrieval Regression bei Retrieval-relevantem Cleanup prüfen.

## Rollback-Strategie

| Cleanup-Klasse | Rollback |
|---|---|
| `stale_index_cleanup` | Governed Reindex, bevorzugt workspace-scoped |
| `expired_session_cleanup` | kein Datenrollback nötig; Nutzer melden sich neu an |
| `orphan_cleanup` | Restore aus Backup oder Reimport der Quelle; DB allein reicht nicht |
| `temp_file_cleanup` | Restore aus Filesystem-Backup oder Reupload |
| `old_report_cleanup` | Restore aus Backup oder Report neu generieren |

## Verboten

- Cleanup ohne Dry Run
- Cleanup ohne Audit Trail
- Cleanup als stille Reparatur von Drift
- Löschen historischer Citations oder Citation-Snapshots
- Cleanup während Running Jobs auf betroffenen Artefakten
- manuelles `grün` ohne maschinenlesbaren Report

