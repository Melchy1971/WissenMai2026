# M5 Drift Repair Strategy

Stand: 2026-05-12

Dieses Dokument definiert die Repair-Strategie fuer M5-Drift. Es gibt keinen allgemeinen Auto-Repair frei. Drift Repair ist dry-run-first, auditierbar, nicht destruktiv und muss nach jedem Eingriff durch denselben Drift-Check verifiziert werden, der den Befund erzeugt hat.

## Repair-Strategie

| Drift-Art | Automatische Reparatur? | Manuelle Reparatur? | Dry Run? | Risiko | Recovery moeglich? |
|---|---|---|---|---|---|
| Search Index Drift | Nein fuer produktive Mutation; erlaubt ist nur automatische Erkennung und Repair-Plan-Erzeugung | Ja, bevorzugt workspace- oder document-scoped Reindex nach Backup-Verifikation | Pflicht; zeigt betroffene Workspaces, Dokumente, Chunks und geplante Indexaenderungen | Mittel bis hoch: falscher Reindex kann Search/Retrieval verfaelschen, darf aber keine Primaerdaten loeschen | Ja; Index ist rekonstruierbar, Recovery ueber erneuten Reindex aus DB-Quelle |
| Lifecycle Drift | Nein | Ja, nur wenn Sollzustand aus DB-Historie, Audit-Log oder expliziter Operator-Entscheidung eindeutig ist | Pflicht; zeigt aktuelle und erwartete `lifecycle_status`, `is_searchable`, `deleted_at`, `source_status` | Hoch: falscher Lifecycle-Repair kann Dokumente sichtbar/unsichtbar machen | Teilweise; Soft-Delete ist historisch nachvollziehbar, aber falsche Statuskorrekturen koennen fachlich unklar sein |
| Citation Drift | Nein | Ja, aber nur fuer Metadaten wie fehlenden oder falschen `source_status`; historische Snapshot-Inhalte bleiben unveraendert | Pflicht; zeigt Citation, Message, Dokument, Live-Status und vorgeschlagene Metadatenkorrektur | Hoch: Citations sind Vertrauens- und Historienartefakte | Teilweise; Snapshot-Felder duerfen nicht still rekonstruiert werden, fehlender Status kann auditierbar repariert werden |
| Queue Drift | Nein fuer stillen Replay; automatische Markierung als repair-candidate ist erlaubt | Ja, stale `running -> retryable`, `dead_letter -> pending` Replay nur mit Lock und Audit-Eintrag | Pflicht ausser bei klar definiertem Timeout-Recovery im Wartungsfenster | Hoch: falscher Replay kann doppelte Imports, Duplicate-Wachstum oder verlorene Fehlerursachen erzeugen | Ja, wenn Jobs idempotent sind und Audit/Result-State erhalten bleiben |
| Backup Drift | Nein | Ja, durch Backup neu erzeugen, Backup verwerfen oder Restore-Pfad wechseln; defekte Artefakte nicht reparieren | Pflicht ueber `validate` und `verify-backup`; Restore-Dry-Run fuer Freigabe | Sehr hoch: falsche Backup-Annahme gefaehrdet Recovery | Ja durch neues gueltiges Backup; defekte Backups werden nicht "geheilt", sondern ersetzt oder gesperrt |
| Data Quality Drift | Nein | Ja, nur nach klassifiziertem Befund: fehlende Anchors, Duplicate-Konflikt, Orphan, kaputte Version/Chunk-Beziehung | Pflicht; liefert Kandidaten, Schutzgrund, Referenzen und erwarteten Effekt | Hoch: Data-Quality-Repair kann Primaerdaten, Chunks oder historische Verweise betreffen | Teilweise; nur reversible oder aus Quelle rekonstruierbare Korrekturen duerfen ohne Spezialfreigabe ausgefuehrt werden |

## Safety Constraints

- Repair darf keine Primaerdaten loeschen.
- Repair darf keine Originaldatei entfernen, solange irgendein Dokument, Backup, Citation oder Audit-Eintrag darauf verweist.
- Repair darf historische Chat-Citation-Snapshots nicht still ueberschreiben.
- Repair darf `workspace_id`-Grenzen nicht erweitern oder erraten.
- Repair darf keine globalen Reindex-, Replay- oder Cleanup-Aktionen starten, wenn ein kleinerer Scope ausreicht.
- Repair muss vor jeder Mutation einen Dry-Run-Report erzeugen.
- Repair muss nach jeder Mutation denselben Drift-Check erneut ausfuehren.
- Repair muss bei Backup-, Lifecycle-, Citation- und Data-Quality-Drift ein aktuelles verifiziertes Backup voraussetzen.
- Repair muss idempotent sein oder eine eindeutige Wiederholungssperre besitzen.
- Repair darf bei unklarer Ursache nur `blocked` melden, nicht raten.

## Audit-Anforderungen

Jeder Repair-Vorgang muss einen Audit-Eintrag erzeugen. Mindestfelder:

| Feld | Bedeutung |
|---|---|
| `repair_id` | Eindeutige ID fuer Dry-Run und Ausfuehrung |
| `drift_type` | Search Index, Lifecycle, Citation, Queue, Backup oder Data Quality |
| `mode` | `dry_run` oder `execute` |
| `requested_by` | Operator, technischer Reviewer oder Systemprozess fuer read-only Plan |
| `approved_by` | Pflicht fuer jede Mutation ausser klar definierter Timeout-Recovery |
| `workspace_id` | Scope; `global` nur mit expliziter Begruendung |
| `affected_entities` | Dokumente, Chunks, Jobs, Citations, Backup-Artefakte oder Constraints |
| `before_state_hash` | Hash oder strukturierte Zusammenfassung vor Repair |
| `planned_change` | Konkrete Aktion, nicht nur Freitext |
| `backup_reference` | Pflicht bei mutierendem Repair mit Daten-/Lifecycle-/Citation-Bezug |
| `result` | `planned`, `applied`, `blocked`, `failed`, `rolled_back` |
| `after_state_hash` | Pflicht nach Mutation |
| `verification_report` | Link auf erneuten Drift-/Truth-/Smoke-Check |
| `error_class` | Falls blockiert oder fehlgeschlagen |

## Freigaberegeln

- `automatic = detect_only`: System darf Drift erkennen und Repair-Kandidaten planen.
- `automatic = execute` ist fuer M5 initial nicht freigegeben.
- Manuelle Ausfuehrung braucht:
  - aktuellen Dry-Run
  - Scope-Begrenzung
  - Backup-Verifikation, falls Datenzustand betroffen ist
  - Audit-Eintrag
  - Nachpruefung
- Full Reindex, Bulk Lifecycle Repair, Citation Snapshot Repair und destructive Data Quality Repair brauchen separate Freigabe.

## Recovery-Pfade

| Repair-Bereich | Primaerer Recovery-Pfad | Sekundaerer Recovery-Pfad |
|---|---|---|
| Search Index | erneuter Reindex aus DB-Quelle | Restore falls DB selbst inkonsistent ist |
| Lifecycle | Status aus Audit-/Domain-Quelle korrigieren | Restore oder manuelle fachliche Entscheidung |
| Citation | `source_status` reparieren, Snapshot erhalten | historische Citation als `missing` markieren, nicht loeschen |
| Queue | Retry/Replay mit Lock und Idempotenz | Job blockieren und manuellen Importentscheid treffen |
| Backup | neues Backup erzeugen und verifizieren | letztes gueltiges Backup verwenden |
| Data Quality | nicht destruktive Strukturkorrektur | Restore oder spezialisiertes Migrations-/Repair-Skript |

## Stop-Regeln

- Stop, wenn Dry-Run mehr Entitaeten betrifft als erwartet.
- Stop, wenn `workspace_id` uneindeutig ist.
- Stop, wenn Backup-Verifikation fehlt oder fehlschlaegt.
- Stop, wenn historische Citations geloescht oder umgeschrieben wuerden.
- Stop, wenn Repair nach Ausfuehrung denselben oder neuen Drift erzeugt.
- Stop, wenn Audit-Eintrag nicht geschrieben werden kann.
