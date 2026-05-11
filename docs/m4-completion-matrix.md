# Masterplan Completion Matrix

Stand: 2026-05-11

## Status

Dieses Dokument ist eine aktualisierte Abschlussmatrix auf Basis des aktuellen Wahrheitsstands fuer M4 sowie der formalen Transition nach M5.

Massgebliche Quellen:

- `reports/postgres_truth_report.json`
- `reports/restore_truth_report.md`
- `docs/m4-m5-freigabefassung.md`
- `masterplan.md`

## Aktueller Gesamtstand

- M4 ist fuer den lokalen Produktbetrieb technisch abgeschlossen.
- `postgres_truth` ist vollstaendig gruen (`33/33`, `failed = 0`, `errors = 0`, `skipped = 0`).
- M4e Minimal ist ueber einen echten Restore-Truth-Test praktisch nachgewiesen.
- M4d bleibt im read-only Scope freigegeben; M4d full mit mutierenden Admin-Aktionen bleibt blockiert.
- M5 Vorbereitung ist erlaubt.
- M5 Implementierung ist durch das formale Transition Gate erlaubt, aber nicht pauschal als gestartet zu dokumentieren.

## Completion Matrix am 2026-05-11

| Bereich | Aktueller Stand | Gate-/Freigabestatus | Nachweisquelle |
|---|---|---|---|
| M4a Auth/Workspace | technisch abgeschlossen im aktuellen Gate-Scope | PASS | `reports/postgres_truth_report.json`, `docs/m4-m5-freigabefassung.md` |
| M4b Upload/Queue | technisch abgeschlossen im aktuellen Gate-Scope | PASS | `reports/postgres_truth_report.json`, `docs/m4-m5-freigabefassung.md` |
| M4c Lifecycle/Retrieval | technisch abgeschlossen im aktuellen Gate-Scope | PASS | `reports/postgres_truth_report.json`, `docs/m4-m5-freigabefassung.md` |
| M4d Diagnostics read-only | real implementiert und freigabefaehig | PASS im read-only Scope | `docs/m4-m5-freigabefassung.md` |
| M4d Diagnostics full | bewusst nicht freigegeben | blockiert | `docs/m4-m5-freigabefassung.md` |
| M4e Backup/Restore minimal | real implementiert und praktisch nachgewiesen | PASS im Minimal-Scope | `reports/restore_truth_report.md`, `docs/m4-m5-freigabefassung.md` |
| M5 Systemreife | Vorbereitung dokumentiert; Implementierung freigegeben, aber nicht pauschal gestartet | Vorbereitung `Go`, Implementierung erlaubt | `docs/m4-m5-freigabefassung.md`, `masterplan.md` |

## Aktuelle Schlussfolgerung

- Die frueheren Prozent- und Gap-Schaetzungen fuer einen blockierten M4-Stabilization-Sprint sind ueberholt.
- Fuer aktuelle Freigabeaussagen sind nur die formalen Gate-Quellen massgeblich.
- M4 gilt nicht mehr als blockiert.
- M5 gilt nicht mehr als pauschal blockiert.
- M5 darf dennoch nur sliceweise mit echtem PostgreSQL-Nachweis auf `gruen` gesetzt werden.
