# M3a Dokumentations-Abweichungsliste

Stand: 2026-05-18

Verbindliche Reports:

- `reports/frontend_truth_report.json`
- `reports/m3a_gate_result.json`
- `reports/postgres_truth_report.json`
- `reports/contract_test_report.json` (aktuell fehlend)

## Aktueller Gate-Stand

| Nachweis | Ergebnis |
|---|---|
| Letzter Full-Suite-Frontend-Truth-Report | `80 collected`, `58 passed`, `22 failed`, `0 skipped` |
| Aktueller Auth-Bootstrap-Truth-Slice | `22 collected`, `22 passed`, `0 failed`, `0 skipped` |
| M3a Gate Result | `BLOCKED`, Score `70` |
| PostgreSQL Truth Report | `138 collected`, `120 passed`, `16 failed`, `2 errors`, Exit-Code `1` |
| Contract Test Report | `8 collected`, `8 passed`, `0 failed`, `0 skipped` |

## Korrigierte Abweichungen

| Datei | Alte Aussageklasse | Korrektur |
|---|---|---|
| `masterplan.md` | M3a-GUI als gestartete/read-only Basis ohne Gate-Blocker hervorgehoben | GUI vorhanden, aber M3a nicht stabilisiert; roter Frontend Truth Report und rotes M3a Gate referenziert |
| `masterplan.md` | historische `5 passed`/Build-Aussage im M3a-Abschlussstand | ersetzt durch aktuellen Frontend Truth Report und konkrete Gate-Blocker |
| `docs/status.md` | M3a-Prototyp mit historischem Frontend-Nachweis, aber ohne Trennung zwischen Slice- und Full-Suite-Evidenz | aktualisiert auf `nicht abgeschlossen`, `nicht stabilisiert`, Auth-Slice gruen, Full-Suite weiter offen |
| `docs/frontend.md` | Frontend-Build und Screen-Tests als dominante Nachweise | aktuelle Truth-Report-Grenze ergaenzt; lokale Tests ersetzen kein E2E-Gate |
| `docs/api.md` | GUI/API-Vertrag konnte als stabiler M3a-Kontext gelesen werden | M3a-Nachweisgrenze ergaenzt; spaetere GUI-Slices getrennt vom M3a-Kernscope |
| `docs/changelog.md` | kein aktueller Eintrag zum roten M3a-Gate | Eintrag 2026-05-18 mit finalem Gate-Stand, Findings und Decision |

## Offene GUI-Blocker

- Kein aktueller gruener Full-Suite-Frontend-Truth-Lauf; letzter Gesamtstand bleibt `58/80`, `22 failed`.
- Nicht-Auth-GUI-Slices sind nach dem grünen Auth-Bootstrap-Nachlauf weiter als offene Restarbeit zu behandeln.
- roter `reports/postgres_truth_report.json`.
- M3a Gate `BLOCKED`; M3a darf nicht als abgeschlossen, freigegeben oder stabilisiert markiert werden.

## Dokumentationsregel

Keine Dokumentation darf M3a als `abgeschlossen`, `freigegeben`, `PASS`, `Go` oder `stabilisiert` markieren, solange `scripts/validate_m3a_gate.py` keinen gruenen Report erzeugt.
