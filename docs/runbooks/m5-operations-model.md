# M5 Operations Model

Stand: 2026-05-12

Dieses Betriebsmodell definiert wiederkehrende M5-Checks fuer den lokalen produktionsnahen Betrieb. Es ist ein Betriebs- und Readiness-Modell, keine Freigabe fuer neue GUI-Admin-Aktionen oder automatische Reparaturen.

Nachweisanker:

- `reports/m5_longrun/latest.json`
- `reports/m5_longrun_summary.md`
- `reports/m5_retrieval/latest.json`
- `reports/m5_retrieval_summary.md`
- `reports/m5_entropy/latest.json`
- `reports/m5_entropy_audit.md`
- `reports/postgres_truth/latest.json`
- `reports/restore_truth_report.md`

## Operations Model

| Bereich | Trigger | Verantwortlichkeit | Eskalationsschwelle | Recovery-Pfad |
|---|---|---|---|---|
| Taegliche Checks | Tagesstart, nach Deploy, nach Import-/Queue-Stoerung | Operator oder lokale Adminrolle | Health/Diagnostics nicht erreichbar; DB nicht erreichbar; neue Fehlerklasse; Queue-Backlog > 15; `m5_entropy.status = blocked` | Betrieb einfrieren, Diagnose sichern, Queue Health pruefen, bei Daten-/Indexdrift woechentlichen Check vorziehen |
| Woechentliche Checks | Einmal pro Kalenderwoche, vor M5-Readiness-Entscheid, nach groesserem Datenimport | Operator mit technischer Review-Rolle | `m5_longrun.status != pass`; `m5_retrieval.status != pass`; `m5_entropy.status = blocked`; neues `postgres_truth` failed/errors/skipped | Longrun, Retrieval Benchmark und Entropy Audit neu ausfuehren; Abweichung isolieren; Fix nur ueber dedizierten Recovery-Pfad |
| Backup-Verifikation | Nach jedem Backup, woechentlich, vor Cleanup/Reindex/Restore, vor riskanten Datenoperationen | Operator; Review durch zweite Person bei Restore | `verify-backup.status != ok`; Backup aelter als 7 Tage; Restore-Dry-Run fehlt; Manifest-/Checksum-Abweichung | Backup nicht freigeben; neues Backup erzeugen; `verify-backup`; bei Restorebedarf DR-Runbook nutzen |
| Drift Detection | Taeglich read-only; nach Lifecycle-Bulk-Aktion, Restore, Reindex oder Queue-Recovery | Operator; technische Review bei Drift | `stale_index_growth > 0`; DB-vs-Index-Abweichung; Lifecycle/Searchability-Verletzung; Citation-Drift | Mutierende Aktionen stoppen; Ursache isolieren; workspace-scoped Reindex nur nach Freigabe; danach Drift-Check wiederholen |
| Queue Health | Taeglich; nach Upload-Spitzen; nach Retry-/Dead-Letter-Ereignissen | Operator | Running Job ueber Timeout; `queue_backlog > 25`; Dead-Letter-Wachstum; Replay ohne Audit-Spur; wiederholte Retry-Schleife | Stale running nach retryable ueberfuehren; Dead-Letter-Replay mit Lock; Audit pruefen; bei Persistenz Uploads pausieren |
| Reindex-Policy | Nur nach Drift, Restore, Index-Migration oder expliziter Betriebsfreigabe | Technische Review-Rolle; Operator fuehrt aus | Reindex laeuft ohne Backup-Verifikation; Drift bleibt nach Reindex; archivierte/geloeschte Dokumente bleiben searchbar | Backup validieren; workspace- oder document-scoped Reindex bevorzugen; Full Reindex nur im Wartungsfenster; Retrieval/Drift nachpruefen |
| Cleanup-Zyklen | Woechentlicher Dry-Run; vor Storage-Reduktion; nach Orphan- oder Duplicate-Befund | Operator; technische Freigabe fuer destructive Cleanup | `blocked_count > 0`; unerwartetes Candidate-Wachstum; historische Citations betroffen; kein aktuelles Backup | Nur Dry-Run akzeptieren; Regeln korrigieren; Backup verifizieren; destructive Cleanup erst nach separater Freigabe |
| Truth-Test-Zyklen | Vor M5-Gate, nach Migrationsaenderung, nach Auth/Workspace/Queue/Lifecycle/Retrieval-Fix | Entwickler oder technische Review-Rolle | `failed > 0`; `errors > 0`; `skipped > 0`; `exit_code != 0`; Setup-/Migration-Errors | Setup-Errors zuerst auf 0; Migration-State verifizieren; postgres_truth erneut ausfuehren; Gate erst nach komplett gruen |

## Betriebschecklisten

### Taegliche Checkliste

- [ ] Admin Diagnostics read-only abrufen und DB-Erreichbarkeit pruefen.
- [ ] Queue-Buckets pruefen: `pending`, `running`, `retryable`, `dead_letter`.
- [ ] Running Jobs auf Timeout oder fehlendes `claimed_at`/`updated_at` pruefen.
- [ ] Drift-Indikatoren pruefen: stale Indexeintraege, orphan growth, Lifecycle/Searchability.
- [ ] Letzten Backup-Status und Backup-Alter pruefen.
- [ ] Fehlerquote und neue Fehlerklassen gegen Vortag vergleichen.
- [ ] Bei Abweichung: Befund mit Zeitpunkt, Workspace und Reportquelle dokumentieren.

### Woechentliche Checkliste

- [ ] `python -m app.cli m5 longrun-simulation --cycles 28 --restore-every 7` ausfuehren.
- [ ] `python -m app.cli m5 retrieval-benchmark` ausfuehren.
- [ ] `python -m app.cli m5 entropy-audit` ausfuehren.
- [ ] Backup erzeugen oder letztes Backup verifizieren.
- [ ] Restore-Dry-Run oder Restore-Truth-Nachweis auf Aktualitaet pruefen.
- [ ] Cleanup Dry-Run auswerten: `candidate_count`, `protected_count`, `blocked_count`.
- [ ] Duplicate Growth bewerten; bis zur Live-DB-Cardinality-Pruefung bleibt dieser Punkt mindestens `watch`.
- [ ] `postgres_truth` gegen echte PostgreSQL-Testdatenbank ausfuehren, wenn Gate- oder Releaseentscheidung ansteht.

### Backup-Verifikation

- [ ] Backup-Manifest vorhanden.
- [ ] Checksums vorhanden und gueltig.
- [ ] DB-Dump lesbar.
- [ ] Pflichtdateien vorhanden.
- [ ] Config-Snapshot vorhanden.
- [ ] Restore-Dry-Run oder Restore-Test erfolgreich.
- [ ] Nach Restore: Reindex, Drift-Check und Truth-Smoke erfolgreich.

### Queue Health

- [ ] Kein `running` Job jenseits des Timeouts.
- [ ] `retryable` Jobs haben naechsten Retry-Zeitpunkt.
- [ ] `dead_letter` Jobs sind auditiert und haben klare Ursache.
- [ ] Replay laeuft mit Lock und erzeugt Audit-Spur.
- [ ] Backlog bleibt unter `25`; Warnbereich beginnt bei `15`.

### Reindex-Policy

- [ ] Reindex nur mit dokumentiertem Anlass.
- [ ] Vor Reindex: Backup-Verifikation aktuell.
- [ ] Scope klein halten: document oder workspace vor full.
- [ ] Nach Reindex: Drift-Check, Retrieval Benchmark und relevante Search-Smokes.
- [ ] Kein Reindex als stiller Ersatz fuer ungeklaerte Lifecycle- oder Workspace-Fehler.

### Cleanup-Zyklen

- [ ] Standard ist Dry-Run.
- [ ] `blocked_count` muss `0` sein.
- [ ] Historische Citations und Backup-Artefakte sind protected.
- [ ] Destructive Cleanup nur nach Backup-Verifikation und separater Freigabe.
- [ ] Nach Cleanup: Drift-Check, Citation-Check und Entropy Audit.

### Truth-Test-Zyklen

- [ ] Preflight: DB erreichbar, Alembic current == head, Tabellen und Constraints vorhanden.
- [ ] Setup-/Collect-Errors zuerst beheben.
- [ ] `pytest -m postgres_truth tests/postgres_truth -vv` vollstaendig gruen.
- [ ] `failed = 0`, `errors = 0`, `skipped = 0`, `exit_code = 0`.
- [ ] Report-Deltas pruefen: neue Failures und geloeste Tests dokumentieren.

## Eskalationsmodell

| Stufe | Bedeutung | Schwelle | Aktion |
|---|---|---|---|
| L0 Normal | Betrieb innerhalb Baseline | Alle Checks gruen; Entropy `pass` oder kontrolliertes `watch`; keine Gate-Fehler | Routine fortsetzen, Reports versionieren |
| L1 Watch | Frueher Trend oder unvollstaendige Messung | Queue-Backlog > 15; Entropy `watch`; Duplicate-Cardinality nicht gemessen; Backup-Alter naehert sich 7 Tagen | Woechentlichen Check vorziehen, Befund dokumentieren, keine mutierenden Repairs ohne Freigabe |
| L2 Degraded | Betrieb beeintraechtigt, aber Datenintegritaet nicht verletzt | Retrieval unter Warnschwelle; `m5_longrun.status = degraded`; wiederholte Retry-Schleifen; Cleanup-Kandidaten wachsen | Upload-/Cleanup-/Reindex-Fenster pausieren, Root Cause isolieren, Recovery-Pfad ausfuehren |
| L3 Blocked | Gate oder Datenintegritaet verletzt | `failed/errors/skipped > 0`; Drift > 0; orphan growth > 0; Backup verify failed; `m5_entropy.status = blocked` | Gate stoppen, Betrieb einfrieren, Backup sichern, DR-/Recovery-Runbook anwenden |
| L4 Incident | Wiederherstellbarkeit oder Workspace-Isolation gefaehrdet | Cross-Workspace-Leak, Datenverlustverdacht, Restore nicht moeglich, falsche Citations aus geloeschten Quellen in neuer Antwort | Sofortige Eskalation, Schreibbetrieb stoppen, forensische Reports sichern, Restore-/Rollback-Entscheidung |

## Mindestregeln

- Keine automatische Reparatur nur aufgrund eines einzelnen Drift-Befunds im ersten M5-Slice.
- Keine destructive Cleanup-Aktion ohne aktuelles verifiziertes Backup.
- Keine M5-Gate-Entscheidung bei `postgres_truth` Failures, Errors oder Skips.
- Keine Reindex-Policy, die Workspace-Isolation oder Lifecycle-Regeln umgeht.
- Historical Citations bleiben als Snapshots erhalten; Repair darf sie nicht still ueberschreiben.
