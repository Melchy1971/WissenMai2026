# M5 Cleanup

Stand: 2026-05-11

## Status

- Phase: Vorbereitung
- Implementierung: nicht gestartet
- Freigabestatus: nicht freigegeben
- Truth-Status: nicht als gruen behauptet, bis ein aktueller PostgreSQL-Truth-Report den entsprechenden M5-Block belegt

Statuslogik:

- Dieses Dokument beschreibt nur den Vorbereitungsrahmen fuer M5 Cleanup.
- Die formale M5-Implementierungsfreigabe ist erreicht, aber dieser Slice ist damit noch nicht automatisch gestartet.
- Cleanup gilt hier ausschliesslich als dry-run-faehiger Planungs- und Bewertungsbereich.
- Solange kein freigegebener Mutationspfad und kein gruener PostgreSQL-Nachweis vorliegen, darf keine produktive Cleanup-Implementierung behauptet werden.

## Zweck

- Definiert Cleanup-Kandidaten, Safety Constraints und Dry-Run-Format fuer M5.
- Stellt sicher, dass Vorbereitung nicht mit Loeschfreigabe verwechselt wird.

## Scope in Vorbereitung

- orphaned chunks
- orphaned versions
- stale index entries
- alte `dead_letter` jobs
- alte reports
- temporaere Upload-Dateien
- abgelaufene Sessions

## Verbindliche Vorbereitungsregeln

- Dry Run zuerst
- keine Loeschung ohne Report
- keine Chat-Citation zerstoeren
- keine Originaldatei loeschen, wenn referenziert

## Statuslogik fuer spaetere Fortschreibung

- `Vorbereitung`: Kandidaten, Schutzregeln und Reportformat sind dokumentiert.
- `Nachweis vorbereitet`: Dry-Run-Logik und Truth-Bezug sind beschrieben.
- `Nachweis gruen`: darf erst dokumentiert werden, wenn ein aktueller PostgreSQL-Truth-Report den M5-Block `cleanup_dry_run` grün belegt.
- `Mutationspfad freigegeben`: darf erst nach eigener expliziter Freigabe und separater Dokumentation behauptet werden.

## Platzhalter fuer Nachweise

- Truth-Test-Block: `cleanup_dry_run`
- geplanter Report-Bezug: `reports/postgres_truth_report.json`
- geplanter Dry-Run-Report: noch nicht implementiert

## Nicht-Scope

- keine produktive Loeschung
- kein automatischer Cleanup
- keine stille Mutation von Referenzen, Citations oder Originaldateien
- keine Behauptung eines gestarteten M5-Cleanup-Betriebs
