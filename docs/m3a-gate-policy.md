# M3a Gate Policy

Stand: 2026-05-19

## Entscheidung

M3a bewertet die Frontend Foundation. M3a darf nicht durch vollstaendige `postgres_truth`-Suiten fuer M4-Backend-Hardening oder M5-Operational-Truth blockiert werden.

Backend-Wahrheit ist fuer M3a nur als Mindestnachweis erforderlich:

- API ist erreichbar.
- API laeuft gegen eine echte PostgreSQL-Testdatenbank.
- Contract Tests sind gruen.
- relevante M3a-/GUI-Endpunktflows funktionieren im Frontend Truth Report gegen echte API.

Nicht erforderlich fuer M3a:

- M5 Entropy Tests.
- Queue Aging Tests.
- M4/M5 Drift Tests.
- Cleanup-, Longevity-, Recovery- und Operational-Hardening-Bloecke aus der vollstaendigen `postgres_truth`-Suite.

## Truth-Domaenen

| Domaene | Zweck | Blockierend fuer |
|---|---|---|
| M3a Frontend Truth | GUI Foundation, Auth-/Workspace-Bootstrap, Error States, Recovery-Sichtbarkeit, Concurrency, relevante GUI-Flows gegen echte API | M3a |
| M3a Backend-Minimum | API erreichbar, echte DB aktiv, Contract Tests gruen, relevante Endpunkte durch Frontend Truth belegt | M3a |
| M4 Backend Truth | Auth-/Workspace-Hardening, Upload-/Queue-Stabilitaet, Lifecycle/Retrieval, Crash/Recovery gegen PostgreSQL | M4 |
| M5 Operational Truth | Entropy, Queue Aging, Drift, Cleanup, Longevity, Health und Langzeitbetrieb | M5 |

## Blockierende M3a-Quellen

- `reports/frontend_truth_report.json`
- `reports/gui_truth/latest.json`
- `reports/gui_truth/gui_chaos_suite_report.json`
- `reports/contract_test_report.json`
- `reports/m3a_gate_result.json`

## Nicht blockierende M3a-Referenz

`reports/postgres_truth_report.json` darf im M3a-Report als M4/M5-Referenz erscheinen, aber sein Gesamtstatus ist keine M3a-Regel.

Rote `postgres_truth`-Bloecke blockieren weiterhin M4/M5, wenn sie zu Auth/Workspace, Upload/Queue, Lifecycle/Retrieval, Recovery, Drift, Cleanup, Entropy oder Operational Readiness gehoeren.

Die Detailklassifikation der aktuellen roten `postgres_truth`-Findings steht in `docs/postgres-truth-failure-gate-matrix.md`. Nach dieser Matrix sind die 15 Entropy-/Drift-Failures nicht M3a- oder M4-blockierend; die eine M4b-Failure und die zwei unklassifizierten Setup/Error-Faelle bleiben fuer M4 gate-kritisch.

## Gate-Regel

M3a ist abgeschlossen, wenn alle M3a-Regeln in `scripts/validate_m3a_gate.py` gruen sind:

- Full-Suite Frontend Truth gruen.
- Der Full-Suite-Scope entspricht `docs/frontend-truth-full-suite-scope.md`; ein Auth-/Bootstrap-Slice reicht nicht.
- M3a Backend-Minimum gruen.
- Contract Tests gruen.
- GUI Chaos Tests gruen.
- `frontend_truth.passed == frontend_truth.collected`.
- `frontend_truth.failed == 0`.
- `frontend_truth.skipped == 0`.
- Keine `API_UNREACHABLE`-Fehler im Normalflow.
- Keine `WORKSPACE_NOT_CONFIGURED`-Fehler nach Login mit gueltiger Membership.

## Fehlkopplungsregel

Ein roter M4- oder M5-Truth-Block darf M3a nur blockieren, wenn er direkt eine M3a-Pflichtbedingung verletzt, zum Beispiel:

- API nicht erreichbar.
- `/health/db` rot.
- Contract Tests rot.
- Frontend Truth nutzt keine echte DB.
- relevante GUI-Flows koennen gegen die echte API nicht laufen.

Alle anderen roten M4/M5-Bloecke bleiben im M3a-Report sichtbar, aber nicht blockierend.
