# M4/M5 Freigabefassung

Diese Datei enthaelt keine eigene Gate-Entscheidung mehr. Der aktuelle Status wird ausschliesslich aus `reports/current/masterplan_status.json` abgeleitet und als generierter Abschnitt in `docs/generated/status_section.md` ausgegeben.

## Statusquelle

- Primaere Quelle: `reports/current/masterplan_status.json`.
- Generierter Lesestand: `docs/generated/status_section.md`.
- Dokumentations-Lint: `reports/current/documentation_truth_lint.json`.

## Boundary M3a/M4/M5

- M3a wird durch das Frontend-Full-Suite-Gate bewertet.
- M4 wird durch die aktuellen M4-Split-Reports und `reports/current/m4_truth_report.json` bewertet.
- M5 darf nur aus dem maschinellen M5-Start-Gate in `reports/current/masterplan_status.json` abgeleitet werden.
- Historische M4/M5-Matrizen, Scores und Zwischenentscheidungen sind keine aktuelle Wahrheit.

## Dokumentationsregel

Manuelle PASS-, GO-, Prozent- oder Abschlussaussagen duerfen hier nicht gepflegt werden. Aenderungen am Gate-Status muessen zuerst die Reports unter `reports/current/` aktualisieren; danach wird `docs/generated/status_section.md` neu erzeugt.
