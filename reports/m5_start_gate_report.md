# M5 Start Gate Report

Stand: 2026-05-13

## Entscheidung

**M5 bleibt blockiert.**

Die Vorbereitung ist in grossen Teilen vorhanden, aber die kontrollierte Implementierungsfreigabe ist aktuell nicht zulaessig. Der heute neu erzeugte PostgreSQL-Truth-Report ist nicht gruen und der verbindliche M4-Gate-Validator bewertet den aktuellen Zustand als `FAIL`.

Blockierende Quelle:

- `reports/postgres_truth_report.json`
- `reports/postgres_truth_report.md`
- `scripts/validate_m4_truth_gate.py`

Aktueller Truth-Stand:

| Feld | Wert |
|---|---:|
| Generated at | `2026-05-13T08:23:30.535021Z` |
| Collected | 112 |
| Passed | 83 |
| Failed | 29 |
| Skipped | 0 |
| Errors | 0 |
| Pytest exit code | 1 |

Validator-Entscheidung:

- `M4 Stabilization Gate = FAIL`
- `M5 bleibt blockiert`

## Start-Gate-Matrix

| Kriterium | Status | Nachweisquelle | Bewertung |
|---|---|---|---|
| 1. M4 vollstaendig abgeschlossen? | blockiert | `reports/postgres_truth_report.json`, `scripts/validate_m4_truth_gate.py` | Nicht erfuellt: 29 fehlgeschlagene PostgreSQL-Truth-Tests, `pytest_exit_code=1`, M4d-Gate-Marker fehlt. M4a/M4b/M4c Scores sind zwar ueber Schwelle, reichen aber nicht gegen rote Full-Suite. |
| 2. Restore Truth-Test gruen? | erfuellt | `reports/restore_truth_report.md` | Gesamtstatus `PASS`; Restore auf leere Zielumgebung, Reindex, Queue, Citations und Lifecycle wurden im geprueften Scope nachgewiesen. |
| 3. Langzeitsimulation definiert? | erfuellt | `docs/m5-longrun-simulation.md`, `reports/m5_longrun/latest.json` | Definiert und letzter Report `status=pass`; 28 Zyklen, Restore alle 7 Zyklen, keine Stop-Events. |
| 4. Retrieval Baseline definiert? | erfuellt | `docs/m5-retrieval-quality-baseline.md`, `reports/m5_retrieval/latest.json` | Golden Dataset `m5-retrieval-golden-v1`; letzter Report `status=pass`. |
| 5. Drift Detection definiert? | erfuellt, nicht freigegeben | `docs/drift.md`, `docs/runbooks/m5-drift-repair-strategy.md` | Drift-Arten, Severity, Repair-Grenzen und Auditpflicht sind definiert; produktiver Repair bleibt gesperrt. |
| 6. Cleanup Safety definiert? | teilweise erfuellt | `docs/cleanup.md`, `backend/tests/postgres_truth/test_m5_cleanup_truth.py`, `reports/postgres_truth_report.json` | Neue Cleanup-Prozess-Truth-Tests sind isoliert gruen, aber der volle Truth-Report enthaelt weiterhin Cleanup-Governance-Failures. Destructive Cleanup bleibt gesperrt. |
| 7. Observability erweitert? | erfuellt mit Nachlauf | `docs/m5-observability.md`, `backend/app/observability/m5_metrics.py` | Acht Pflichtmetriken sind definiert. Nachlauf: erlaubte Dimensionen im Code muessen mit dem Dokument abgeglichen werden. |
| 8. Operations Model vorhanden? | erfuellt | `docs/runbooks/m5-operations-model.md` | Tages-/Wochenchecks, Backup, Drift, Queue, Reindex, Cleanup, Truth-Zyklen und Eskalation L0-L4 sind vorhanden. |

## Risiken

| Risiko | Schwere | Status | Begrenzung |
|---|---|---|---|
| Voller PostgreSQL-Truth-Report ist rot | hoch | offen | M5-Start bleibt blockiert, bis `failed=0`, `errors=0`, `skipped=0`, `pytest_exit_code=0`. |
| M4d-Gate ohne registrierte Tests | hoch | offen | `@pytest.mark.m4d_gate` fuer relevante read-only Diagnostics-Truth-Tests nachziehen oder Gate-Regel bewusst aendern. |
| Citation Longevity und Entropy Truth schlagen fehl | hoch | offen | Datenalterung gilt nicht als kontrollierbar, solange diese Bloecke rot sind. |
| Cleanup Governance hat rote Tests | hoch | offen | Cleanup bleibt nur konzeptionell und fuer isolierte Prozess-Tests belegbar; kein produktiver Cleanup-Execute. |
| Duplicate Growth nicht live gemessen | mittel | offen | Live-DB-Aggregation nach `workspace_id + content_hash` bleibt Pflichtnachweis. |
| Observability-Dimensionen uneinheitlich | mittel | offen | Code-Whitelist fuer Dimensionen gegen `docs/m5-observability.md` synchronisieren. |

## Freigabeentscheidung

Von den drei moeglichen Entscheidungen gilt aktuell:

| Entscheidung | Ergebnis |
|---|---|
| M5 bleibt blockiert | ja |
| M5 Vorbereitung vollstaendig | nein |
| M5 Implementierung kontrolliert freigegeben | nein |

Begruendung:

- M5 darf erst implementiert werden, wenn Betriebsalterung kontrollierbar erscheint.
- Der aktuelle Entropy-Status ist nur `watch`, nicht `pass`.
- Der aktuelle vollstaendige PostgreSQL-Truth-Lauf ist rot.
- Der verbindliche M4-Gate-Validator blockiert.

## Erforderliche Schritte zur Entblockung

1. Die 29 fehlgeschlagenen PostgreSQL-Truth-Tests beheben oder sauber aus dem Gate-Scope begruenden.
2. `m4d_gate`-Marker fuer den read-only Diagnostics-Gate-Nachweis registrieren.
3. Vollstaendigen `python ..\scripts\generate_postgres_truth_report.py`-Lauf erneut mit echter `TEST_DATABASE_URL` ausfuehren.
4. `python scripts\validate_m4_truth_gate.py reports\postgres_truth_report.json` muss `PASS` melden.
5. Entropy/Duplicate-Nachlauf schliessen, bis Betriebsalterung mindestens fuer das Start Gate kontrollierbar ist.
