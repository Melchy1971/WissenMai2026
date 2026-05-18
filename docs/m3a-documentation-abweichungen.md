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
| Frontend Truth Report | `80 collected`, `58 passed`, `22 failed`, `0 skipped` |
| M3a Gate Result | `FAIL`, Score `57.1` |
| PostgreSQL Truth Report | `138 collected`, `120 passed`, `16 failed`, `2 errors`, Exit-Code `1` |
| Contract Test Report | `8 collected`, `8 passed`, `0 failed`, `0 skipped` |

## Korrigierte Abweichungen

| Datei | Alte Aussageklasse | Korrektur |
|---|---|---|
| `masterplan.md` | M3a-GUI als gestartete/read-only Basis ohne Gate-Blocker hervorgehoben | GUI vorhanden, aber M3a nicht stabilisiert; roter Frontend Truth Report und rotes M3a Gate referenziert |
| `masterplan.md` | historische `5 passed`/Build-Aussage im M3a-Abschlussstand | ersetzt durch aktuellen Frontend Truth Report und konkrete Gate-Blocker |
| `docs/status.md` | M3a-Prototyp mit historischem Frontend-Nachweis, aber ohne aktuellen Gate-Bezug | aktualisiert auf `nicht abgeschlossen`, `nicht stabilisiert`, Gate `FAIL` |
| `docs/frontend.md` | Frontend-Build und Screen-Tests als dominante Nachweise | aktuelle Truth-Report-Grenze ergaenzt; lokale Tests ersetzen kein E2E-Gate |
| `docs/api.md` | GUI/API-Vertrag konnte als stabiler M3a-Kontext gelesen werden | M3a-Nachweisgrenze ergaenzt; spaetere GUI-Slices getrennt vom M3a-Kernscope |
| `docs/changelog.md` | kein aktueller Eintrag zum roten M3a-Gate | Eintrag 2026-05-18 mit finalem Gate-Stand, Findings und Decision |

## Offene GUI-Blocker

- 22 fehlgeschlagene Frontend-E2E-Flows im aktuellen Frontend Truth Report.
- roter `reports/postgres_truth_report.json`.
- M3a Gate `FAIL`; M3a darf nicht als abgeschlossen, freigegeben oder stabilisiert markiert werden.

## Dokumentationsregel

Keine Dokumentation darf M3a als `abgeschlossen`, `freigegeben`, `PASS`, `Go` oder `stabilisiert` markieren, solange `scripts/validate_m3a_gate.py` keinen gruenen Report erzeugt.
