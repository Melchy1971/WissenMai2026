# M4/M5 Freigabefassung

Stand: 2026-05-18

Zweck: Dieses Dokument enthaelt den aktuell freigabefaehigen Wahrheitsstand fuer M4 und die Transition nach M5. Der fruehere PASS-Stand vom 2026-05-11 ist historisch und wird durch die aktuellen Reports vom 2026-05-18 ersetzt.

## Aktueller Entscheidungsstand

- M3a ist nicht stabilisiert: `reports/m3a_gate_result.json` steht auf `BLOCKED`, Score `70`.
- Frontend Truth ist im Auth-Bootstrap-Slice gruen (`22/22`), aber global nicht neu gruen nachgewiesen; der letzte Full-Suite-Lauf bleibt rot (`80 collected`, `58 passed`, `22 failed`, `0 skipped`).
- PostgreSQL Truth ist rot: `138 collected`, `120 passed`, `16 failed`, `2 errors`, Exit-Code `1`.
- M4a/M4b/M4c haben positive Marker-Teilbefunde, aber keine Gesamtfreigabe, solange der Gesamt-Truth-Report rot ist.
- M4e Minimal ist dokumentiert und bleibt als Betriebsentscheidung erhalten, kompensiert aber keine roten Gates.
- M4 Gesamtabschluss: `No-Go`.
- M5-Transition aus M4: `No-Go`.

## Aktuell beweisbare Aussagen

- Der technische Backend-Kern fuer M4a Auth und Workspace-Kontext ist vorhanden.
- Upload, Search, Chat und Diagnostics verwenden den serverseitig aufgeloesten Request-Kontext in wesentlichen Pfaden.
- M4a Markergruppe im aktuellen PostgreSQL Truth Report: `100.0%`.
- M4b Markergruppe im aktuellen PostgreSQL Truth Report: `91.7%`.
- M4c Markergruppe im aktuellen PostgreSQL Truth Report: `100.0%`.
- M4d ist im read-only Scope als vorhandener Slice dokumentierbar.
- M4d full mit mutierenden Admin-Aktionen ist nicht freigegeben.
- M4e Minimal ist als Restore-/Backup-Entscheidung dokumentiert.

## Nachweisgrenzen

- Ein Marker-Teilscore kann den roten Gesamt-Truth-Report nicht ueberstimmen.
- M4 Gesamtabschluss ist nur moeglich, wenn M3a `>= 90`, M4a/M4b/M4c erfuellt, M4e dokumentiert und alle Truth Reports gruen sind.
- Diese Bedingungen sind aktuell nicht erfuellt.
- Gruene Aussagen aus dem 2026-05-11-Stand duerfen nur noch historisch zitiert werden.

## Korrigierte M4 Matrix am 2026-05-18

| Voraussetzung | Soll | Ist | Ergebnis |
|---|---|---|---|
| M3a Score | `>= 90` | `70` | FAIL |
| Frontend Truth gruen | Pflicht | Auth-Slice `22/22` gruen, letzter Full-Suite-Lauf `58/80`, `22 failed` | FAIL |
| PostgreSQL Truth gruen | Pflicht | `120/138`, `16 failed`, `2 errors`, Exit-Code `1` | FAIL |
| M4a | erfuellt | Marker `100.0%`, Gesamt-Truth rot | BLOCKED |
| M4b | erfuellt | Marker `91.7%`, Gesamt-Truth rot | BLOCKED |
| M4c | erfuellt | Marker `100.0%`, Gesamt-Truth rot | BLOCKED |
| M4d read-only | akzeptiert | Slice vorhanden | dokumentierbar, kein Gesamt-PASS |
| M4e minimal | Entscheidung dokumentiert | Restore-Truth-Nachweis vorhanden | PASS als Dokumentationspunkt |
| Dokumentation aktuell | Pflicht | Reconciliation dokumentiert | PASS |

## Entscheidung

- M4 bleibt blockiert: `ja`.
- M4 technisch stabil, aber GUI blockiert: `nein`; neben M3a/GUI ist auch PostgreSQL Truth rot.
- M4 Gesamtabschluss moeglich: `nein`.
- M5 Vorbereitung/Implementierung aus M4-Gate: `No-Go`.

## Freigabeaussagen, die nicht verwendet werden duerfen

- M4 ist abgeschlossen.
- M4 ist technisch stabil freigegeben.
- M5 ist durch das M4-Transition-Gate erlaubt.
- M4a/M4b/M4c sind durch Marker-Teilscore allein freigegeben.
- Der historische 2026-05-11-PASS ist ein aktueller Freigabenachweis.
