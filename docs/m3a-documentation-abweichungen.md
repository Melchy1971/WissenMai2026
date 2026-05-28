# M3a Dokumentations-Abweichungsliste

Stand: 2026-05-19

## Verbindliche Reports

- `reports/current/frontend_full_suite_staged_report.json`
- `reports/current/frontend_full_suite_staged_report.json`
- `reports/current/frontend_full_suite_staged_report.json`
- `reports/current/m3a_release_candidate.json`
- `reports/current/gate_hierarchy_result.json`

`reports/current/m4_truth_report.json` ist keine M3a-Pflichtquelle. Der Report bleibt M4 Backend Truth und M5 Operational Truth.

## Aktueller Gate-Stand

| Nachweis | Ergebnis |
|---|---|
| Full-Suite-Frontend-Truth | `82 collected`, `82 passed`, `0 failed`, `0 skipped` |
| GUI Chaos Suite | `8 collected`, `8 passed`, `0 failed` |
| Contract Test Report | `8 collected`, `8 passed`, `0 failed`, `0 skipped` |
| M3a Gate Result | `PASS`, Score `100.0` |
| PostgreSQL Truth Report | M4/M5-Referenz: `138 collected`, `120 passed`, `16 failed`, `2 errors`, Exit-Code `1` |

## Korrigierte Abweichungen

| Datei | Alte Aussageklasse | Korrektur |
|---|---|---|
| `scripts/validate_m3a_gate.py` | vollstaendige `postgres_truth` konnte M3a blockieren | M3a nutzt Backend-Minimum statt M4/M5-Truth-Gesamtsuite |
| `masterplan.md` | M3a als blockiert durch roten Frontend-/PostgreSQL-Truth beschrieben | M3a PASS, M4/M5 bleiben separat ueber PostgreSQL Truth blockiert | Quelle: `reports/current/masterplan_status.json`.
| `docs/status.md` | M3a nicht stabilisiert, M4 zusaetzlich durch GUI blockiert | M3a abgeschlossen; M4 bleibt durch Backend Truth blockiert |
| `docs/frontend.md` | alter roter Full-Suite-Lauf als aktuelle Gate-Grenze | aktueller gruener Full-Suite-Frontend-Truth referenziert |
| `docs/api.md` | API-/GUI-Vertrag konnte als M3a durch komplette `postgres_truth` gekoppelt gelesen werden | M3a Backend-Minimum explizit reduziert |
| `docs/operational-truth-governance.md` | M3a-Policy trennte Frontend-, Backend- und Operational-Truth nicht hart genug | M3a/M4/M5 Truth-Domaenen getrennt |

## Reduzierte Fehlkopplung

- M3a Frontend Truth blockiert M3a.
- M3a Backend-Minimum blockiert M3a.
- M4 Backend Truth blockiert M4.
- M5 Operational Truth blockiert M5.
- M5 Entropy, Queue Aging, Drift, Cleanup und Longevity blockieren M3a nicht.

## Dokumentationsregel

M3a darf als `abgeschlossen`, `freigegeben`, `PASS` oder `stabilisiert` markiert werden, solange `reports/current/gate_hierarchy_result.json` gruen ist und keine neuere rote M3a-Quelle existiert.
