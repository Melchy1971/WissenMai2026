# Restore Truth Report

Stand: 2026-05-11

## Ziel

Echter isolierter Backup/Restore-Truth-Test fuer die minimale M4e-Architektur.

Geprueft wurde, ob eine leere Zielumgebung aus einem real erzeugten Backup vollstaendig rekonstruierbar ist, inklusive Reindex und Restore-Nachpruefungen.

## Testaufbau

- PostgreSQL lief lokal im Docker-Container `wissenmai2026-testdb-1`.
- Da `pg_dump` und `psql` lokal nicht im PATH vorhanden waren, wurden temporaere Wrapper auf die Container-Binaries gelegt.
- Zwei temporaere Datenbanken wurden verwendet:
  - `wissen_restore_src`
  - `wissen_restore_dst`
- Auf beiden Datenbanken wurde das Schema per `alembic upgrade head` vorbereitet.
- Die Quelldatenbank wurde mit repraesentativen Restore-Daten befuellt:
  - 2 Workspaces
  - 1 Benutzer mit Memberships
  - 3 Dokumente
  - Lifecycle-Mix: `active`, `archived`, `deleted`
  - Versionen und Chunks
  - 1 Chat-Session
  - 1 Chat-Message
  - 1 Citation
  - 1 Queue-Job
  - technische Originaldatei-Ablage ueber `backup_original`

## Backup/Restore-Ablauf

1. Backup gegen `wissen_restore_src` erzeugt.
2. Leere Zielumgebung `wissen_restore_dst` vorbereitet.
3. Restore-Pipeline gegen `wissen_restore_dst` ausgefuehrt.
4. Search-Rebuild und Restore-Nachpruefungen ausgefuehrt.
5. `postgres_truth`-Smoke-Subset ueber die Restore-Pipeline ausgefuehrt.

## Restore-Truth-Ergebnis

Gesamtstatus: PASS

### Vorher/Nachher-Paritaet

| Metrik | Quelle | Ziel nach Restore | Ergebnis |
|---|---:|---:|---|
| Workspaces | 2 | 2 | PASS |
| Dokumente | 3 | 3 | PASS |
| Chunks | 1 | 1 | PASS |
| Chat Sessions | 1 | 1 | PASS |
| Citations | 1 | 1 | PASS |
| Queue Jobs | 1 | 1 | PASS |

### Fachliche Pruefungen

| Pruefung | Ergebnis |
|---|---|
| gleiche Dokumentanzahl | PASS |
| gleiche Chunkanzahl | PASS |
| gleiche Search-Ergebnisse | PASS |
| gleiche Citations | PASS |
| gleiche Lifecycle States | PASS |
| Queue konsistent | PASS |
| Restore auf leere Zielumgebung | PASS |
| Reindex nach Restore | PASS |
| `postgres_truth` Smoke-Subset | PASS |

## Datenverlustanalyse

Ergebnis: kein nachweisbarer Datenverlust im getesteten Restore-Scope.

Beobachtungen:

- Alle geprueften Kernobjekte waren nach Restore in gleicher Anzahl vorhanden.
- Search-Verhalten fuer den geprueften Truth-Term blieb fachlich konsistent.
- Historical Citation-Beziehungen blieben erhalten.
- Lifecycle-Zustaende blieben konsistent.
- Queue-Zustand blieb im geprueften Scope rekonstruierbar.

Bewertung:

- Kein Verlust in den geprueften Datenklassen nachweisbar.
- Keine Abweichung zwischen Quell- und Zielumgebung bei den geprueften Paritaetsmetriken.

## Driftanalyse

Ergebnis: keine driftrelevante Abweichung im Restore-Ziel nachgewiesen.

Beobachtungen:

- Restore-Pipeline lief inklusive Search-Rebuild erfolgreich durch.
- Die anschliessende Drift-Pruefung war fuer den Restore-Pfad nicht blockierend.
- Search-Ergebnisse blieben fuer den geprueften Wahrheitsfall stabil.

Bewertung:

- Kein Hinweis auf Lifecycle-/Search-Drift im geprueften Restore-Zustand.
- Keine Hinweise auf orphaned Daten im geprueften Scope.

## Einschränkungen

- Der Test lief auf einem bewusst kleinen, aber realen Restore-Datensatz.
- Die Paritaetspruefung war auf die geprueften Kernmetriken und den vorhandenen Truth-Smoke-Scope fokussiert, nicht auf einen kompletten Full-Suite-Lauf aller `postgres_truth`-Tests.
- Lokale Host-Binaries fuer `pg_dump` und `psql` waren nicht vorhanden; der Test lief deshalb korrekt ueber Container-Wrappers.

## Schlussfolgerung

Die minimale M4e-Backup/Restore-Architektur ist im echten isolierten Restore-Test fuer den geprueften Scope funktionsfaehig.

Fuer den getesteten Datensatz gilt:

- Backup real erzeugbar
- Leere Zielumgebung real wiederherstellbar
- Search nach Restore wieder funktionsfaehig
- `postgres_truth`-Smoke-Subset nach Restore gruen
- kein nachweisbarer Datenverlust
- keine nachweisbare Drift im geprueften Scope
