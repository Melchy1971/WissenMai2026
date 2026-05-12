# M5 Drift Detection

Stand: 2026-05-11

## Status

- Phase: Vorbereitung
- Implementierung: nicht gestartet
- Freigabestatus: nicht freigegeben
- Truth-Status: nicht als gruen behauptet, bis ein aktueller PostgreSQL-Truth-Report den entsprechenden M5-Block belegt

Statuslogik:

- Dieses Dokument beschreibt nur den Vorbereitungsrahmen fuer Drift Detection in M5.
- Die formale M5-Implementierungsfreigabe ist erreicht, aber dieser Slice ist damit noch nicht automatisch gestartet.
- Ein dokumentiertes Drift-Konzept ist kein Beleg fuer einen aktiven Drift-Service oder einen freigegebenen Repair-Pfad.
- Eine gruene Drift-Aussage ist erst zulaessig, wenn ein aktueller PostgreSQL-Truth-Report den M5-Block `drift_detection` belegt.

## Zweck

- Definiert Drift-Arten, Bewertungslogik und spaetere Nachweisstruktur fuer M5.
- Hält den Bereich bewusst read-only in der Dokumentation, bis eine explizite Freigabe erfolgt.

## Scope in Vorbereitung

- DB vs Search Index
- Lifecycle vs Searchbarkeit
- Citation Snapshot vs Live Status
- Queue State vs tatsaechlicher Worker-Zustand
- Backup Manifest vs aktuelle Daten
- Retrieval-Qualitaet ueber Zeit

## Vorbereitete Leitplanken

- Drift Detection bleibt im ersten M5-Slice read-only.
- Repair wird getrennt dokumentiert und nicht durch dieses Dokument freigegeben.
- Die Repair-Strategie ist separat beschrieben in [docs/runbooks/m5-drift-repair-strategy.md](H:/WissenMai2026/docs/runbooks/m5-drift-repair-strategy.md).
- SQLite dient spaeter nur als Fast Feedback, nicht als Gate-Quelle.

## Statuslogik fuer spaetere Fortschreibung

- `Vorbereitung`: Drift-Arten, Schwellen, Severity und Metriken sind definiert.
- `Nachweis vorbereitet`: Truth-Test-Block und Reportformat sind vorbereitet.
- `Nachweis gruen`: darf erst dokumentiert werden, wenn ein aktueller PostgreSQL-Truth-Report den M5-Block `drift_detection` grün belegt.

## Platzhalter fuer Nachweise

- Truth-Test-Block: `drift_detection`
- geplanter Report-Bezug: `reports/postgres_truth_report.json`
- geplanter Detailreport: noch nicht implementiert

## Nicht-Scope

- kein aktiver Reindex- oder Repair-Start
- keine automatische Snapshot-Korrektur
- keine produktive Drift-Reparatur per Web-Admin
- keine Behauptung eines gestarteten M5-Betriebs
