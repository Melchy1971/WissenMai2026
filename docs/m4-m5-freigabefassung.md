# M4/M5 Freigabefassung

Stand: 2026-05-19

Zweck: Dieses Dokument enthaelt den aktuell freigabefaehigen Wahrheitsstand fuer M4 und die Transition nach M5. Der fruehere nicht PASS-Stand vom 2026-05-11 ist historisch und wird durch die aktuellen Reports vom 2026-05-19 ersetzt.

## Aktueller Entscheidungsstand

- M3a Frontend Foundation ist stabilisiert: `reports/current/gate_hierarchy_result.json` steht auf `nicht PASS`, Score `100.0`.
- Frontend Truth ist als Full-Suite rot (`82/82`, `0 failed`, `0 skipped`).
- PostgreSQL Truth ist rot: `138 collected`, `120 passed`, `16 failed`, `2 errors`, Exit-Code `1`.
- M4a/M4b/M4c haben positive Marker-Teilbefunde, aber keine Gesamtfreigabe, solange der Gesamt-Truth-Report rot ist.
- M4e Minimal ist dokumentiert und bleibt als Betriebsentscheidung erhalten, kompensiert aber keinen roten M4 Backend Truth.
- M4 Gesamtabschluss: `NO_GO`.
- M5-Transition aus M4: `NO_GO`.

## Aktuell beweisbare Aussagen

- Der technische Backend-Kern fuer M4a Auth und Workspace-Kontext ist vorhanden.
- Upload, Search, Chat und Diagnostics verwenden den serverseitig aufgeloesten Request-Kontext in wesentlichen Pfaden.
- M4a Markergruppe im aktuellen PostgreSQL Truth Report: Teilbefund vorhanden, Gesamtstatus bleibt blockiert. Quelle: `reports/current/masterplan_status.json`.
- M4b Markergruppe im aktuellen PostgreSQL Truth Report: Teilbefund vorhanden, Gesamtstatus bleibt blockiert. Quelle: `reports/current/masterplan_status.json`.
- M4c Markergruppe im aktuellen PostgreSQL Truth Report: Teilbefund vorhanden, Gesamtstatus bleibt blockiert. Quelle: `reports/current/masterplan_status.json`.
- M4d ist im read-only Scope als vorhandener Slice dokumentierbar.
- M4d full mit mutierenden Admin-Aktionen ist nicht freigegeben.
- M4e Minimal ist als Restore-/Backup-Entscheidung dokumentiert.

## Nachweisgrenzen

- Ein Marker-Teilscore kann den roten Gesamt-Truth-Report nicht ueberstimmen.
- M4 Gesamtabschluss ist nur moeglich, wenn M3a `>= 90`, M4a/M4b/M4c erfuellt, M4e dokumentiert und M4 Backend Truth nicht gruen ist.
- Diese Bedingungen sind aktuell nicht erfuellt.
- Gruene Aussagen aus dem 2026-05-11-Stand duerfen nur noch historisch zitiert werden.

## Korrigierte M4 Matrix am 2026-05-19

| Voraussetzung | Soll | Ist | Ergebnis |
|---|---|---|---|
| M3a Score | `>= 90` | `100.0` | nicht PASS | Quelle: `reports/current/masterplan_status.json`.
| Frontend Truth nicht gruen | Pflicht | Full-Suite `82/82`, `0 failed`, `0 skipped` | nicht PASS | Quelle: `reports/current/masterplan_status.json`.
| PostgreSQL Truth nicht gruen | Pflicht | `120/138`, `16 failed`, `2 errors`, Exit-Code `1` | FAIL |
| M4a | erfuellt | Marker `100.0%`, Gesamt-Truth rot | BLOCKED |
| M4b | erfuellt | Marker `91.7%`, Gesamt-Truth rot | BLOCKED |
| M4c | erfuellt | Marker `100.0%`, Gesamt-Truth rot | BLOCKED |
| M4d read-only | akzeptiert | Slice vorhanden | dokumentierbar, kein Gesamt-nicht PASS |
| M4e minimal | Entscheidung dokumentiert | Restore-Truth-Nachweis vorhanden | nicht PASS als Dokumentationspunkt | Quelle: `reports/current/masterplan_status.json`.
| Dokumentation aktuell | Pflicht | Reconciliation dokumentiert | nicht PASS | Quelle: `reports/current/masterplan_status.json`.

## Entscheidung

- M4 bleibt blockiert: `ja`.
- M4 technisch stabil, aber GUI blockiert: `nein`; GUI/M3a ist nicht gruen, PostgreSQL Truth ist rot.
- M4 Gesamtabschluss moeglich: `nein`.
- M5 Vorbereitung/Implementierung aus M4-Gate: `NO_GO`.

## Freigabeaussagen, die nicht verwendet werden duerfen

- M4 ist laut Status Engine nicht abgeschlossen. Quelle: `reports/current/masterplan_status.json`.
- M4 ist laut Status Engine nicht freigegeben. Quelle: `reports/current/masterplan_status.json`.
- M5 ist durch das M4-Transition-Gate erlaubt.
- M4a/M4b/M4c sind durch Marker-Teilscore allein nicht freigegeben. Quelle: `reports/current/masterplan_status.json`.
- Der historische 2026-05-11-nicht PASS ist ein aktueller Freigabenachweis. Quelle: `reports/current/masterplan_status.json`.
