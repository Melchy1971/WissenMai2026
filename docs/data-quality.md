# M5 Data Quality

Stand: 2026-05-11

## Status

- Phase: Vorbereitung
- Implementierung: nicht gestartet
- Freigabestatus: nicht freigegeben
- Truth-Status: nicht als gruen behauptet, bis ein aktueller PostgreSQL-Truth-Report den entsprechenden M5-Block belegt

Statuslogik:

- Dieses Dokument beschreibt nur die Vorbereitung fuer M5.
- Die formale M5-Implementierungsfreigabe ist erreicht, aber dieser Slice ist damit noch nicht automatisch gestartet.
- Solange das Transition Gate nach M5 nicht explizit als Startfreigabe genutzt wird, markiert dieses Dokument keinen Implementierungsbeginn.
- Dokumentierte Regeln, Schweregrade und Pruefideen sind kein Nachweis einer produktiven Umsetzung.

## Zweck

- Definiert den Dokumentationsrahmen fuer M5 Data Quality.
- Verankert nur vorbereitete Regeln, Bewertungslogik und offene Nachweisbedarfe.
- Behauptet keine produktive Pruef- oder Reparaturfunktion.

## Scope in Vorbereitung

- Dateninvarianten fuer Dokumente, Versionen, Chunks und Citations
- Severity-Modell fuer Fehler und Warnungen
- Pruefstrategie fuer spaetere Read-only-Nachweise
- Truth-Test-Anker fuer spaetere PostgreSQL-Nachweise

## Aktuell vorbereitete Regeln

- Dokument ohne Version = Fehler
- Version ohne Chunks = Fehler ausser `failed import`
- Chunk ohne `source_anchor` = Fehler
- orphaned chunks = Fehler
- orphaned versions = Fehler
- duplicate `content_hash` = Fehler
- dangling citations = Warnung oder Fehler je `source_status`

## Statuslogik fuer spaetere Fortschreibung

- `Vorbereitung`: Regeln, Metriken und Gate-Bezug sind dokumentiert; keine Implementierungsbehauptung.
- `Nachweis vorbereitet`: Test- und Reportformat sind definiert; weiterhin keine gruene Aussage ohne PostgreSQL-Truth-Lauf.
- `Nachweis gruen`: darf erst dokumentiert werden, wenn ein aktueller PostgreSQL-Truth-Report den M5-Block `data_quality` grün belegt.

## Platzhalter fuer Nachweise

- Truth-Test-Block: `data_quality`
- geplanter Report-Bezug: `reports/postgres_truth_report.json`
- geplanter Detailnachweis: noch nicht implementiert

## Nicht-Scope

- keine automatische Datenreparatur
- keine produktive Cleanup-Freigabe
- keine mutierenden Admin-Aktionen
- keine Behauptung eines laufenden M5-Betriebs
