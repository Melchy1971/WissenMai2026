# M5 Start Gate Report

Stand: 2026-05-12

## Entscheidung

**M5 Implementierung kontrolliert freigegeben.**

Die Freigabe gilt fuer kontrollierte, nachweisorientierte M5-Implementierung von Data Quality, Drift Detection, Cleanup Dry-Run, Observability, Health/Trend-Auswertung und Betriebsreports.

Nicht freigegeben:

- automatische Reparatur
- destructive Cleanup
- allgemeine mutierende Web-Admin-Aktionen
- Produktionsfreigabe
- Full Reindex/Repair ohne Dry-Run, Audit und Backup-Verifikation

## Start-Gate-Matrix

| Kriterium | Status | Nachweisquelle | Bewertung |
|---|---|---|---|
| 1. M4 vollstaendig abgeschlossen | erfuellt | `reports/postgres_truth/latest.json`, `docs/m4-m5-freigabefassung.md` | `33/33`, `failed=0`, `errors=0`, `skipped=0`, `pytest_exit_code=0`, M4-Gate PASS |
| 2. Restore Truth-Test gruen | erfuellt | `reports/restore_truth_report.md` | Gesamtstatus `PASS`, Restore auf leere Zielumgebung, Reindex, Queue, Citations und Lifecycle geprueft |
| 3. Langzeitsimulation definiert | erfuellt | `reports/m5_longrun/latest.json`, `docs/m5-longrun-simulation.md` | `status=pass`, 28 Zyklen, keine Stop-Events, `stale_index_growth=0`, `orphan_growth=0` |
| 4. Retrieval Baseline definiert | erfuellt | `reports/m5_retrieval/latest.json`, `docs/m5-retrieval-quality-baseline.md` | `status=pass`, Precision/Recall/MRR/Citation Completeness bei `1.0`, Lifecycle Violations `0` |
| 5. Drift Detection definiert | erfuellt | `docs/drift.md`, `docs/runbooks/m5-drift-repair-strategy.md` | Drift-Arten, Severity, Repair-Grenzen und Auditpflicht definiert; Detection bleibt initial read-only |
| 6. Cleanup Safety definiert | erfuellt | `docs/cleanup.md`, `backend/app/services/m5_cleanup.py`, `backend/tests/postgres_truth/test_m5_cleanup_truth.py` | Dry-run-first, Citation-/Queue-/Active-Data-Schutz und PostgreSQL-only Truth-Tests vorbereitet |
| 7. Observability erweitert | erfuellt | `docs/m5-observability.md`, `backend/app/observability/m5_metrics.py` | acht M5-Metriken definiert; sensitive Inhalte und falsche Workspace-Aggregation blockiert |
| 8. Operations Model vorhanden | erfuellt | `docs/runbooks/m5-operations-model.md` | Tages-/Wochenchecks, Backup, Drift, Queue, Reindex, Cleanup, Truth-Zyklen und Eskalation L0-L4 definiert |

## Betriebsalterung

Aktueller Aging-/Entropy-Status: `watch`

Nachweis: `reports/m5_entropy/latest.json`

Bewertung:

- Stale Queue Jobs: `low`, Backlog `11/25`
- Backup-Alterung: `low`, Restore-Zyklen bei `7, 14, 21, 28`
- Orphan Growth: `low`, final/max `0`
- Stale Indexeintraege: `low`, final/max `0`
- Historical Citation Drift: `low`, Citation Completeness `1.0`, Lifecycle Violations `0`
- Cleanup-Rueckstaende: `low`, blocked `0`
- Duplicate Growth: `medium`, weil Live-DB-Duplicate-Cardinality noch nicht gemessen ist

Regelableitung:

- Betriebsalterung erscheint kontrollierbar genug fuer kontrollierte M5-Implementierung.
- Der Status `watch` verhindert automatische/destruktive Betriebsaktionen.
- Duplicate-Cardinality bleibt ein frueher M5-Pflichtnachweis.

## Risiken

| Risiko | Schwere | Status | Begrenzung |
|---|---|---|---|
| Live-Duplicate-Cardinality nicht gemessen | mittel | offen | M5 muss Live-DB-Aggregation nach `workspace_id + content_hash` ergaenzen |
| Cleanup Truth-Tests noch nicht real gegen aktuelle `TEST_DATABASE_URL` ausgefuehrt | mittel | offen | Tests sind PostgreSQL-only implementiert; Gate-Nachweis braucht echten Lauf |
| Drift Detection aktuell definiert, aber noch nicht als vollstaendiger produktiver Drift-Service freigegeben | mittel | akzeptiert | initial read-only; Repair separat dry-run-first |
| Auto-Repair/destructive Cleanup koennte Daten oder Citations gefaehrden | hoch | blockiert | keine automatische Mutation; Audit, Backup, Dry-Run und Scope-Begrenzung Pflicht |
| M5-Reports basieren teils auf deterministischen Harnesses, nicht auf Langzeit-Produktionsdaten | mittel | akzeptiert | echte PostgreSQL- und Trendnachweise werden in M5 aufgebaut |

## Freigabeentscheidung

Von den drei moeglichen Entscheidungen gilt:

- M5 bleibt blockiert: **nein**
- M5 Vorbereitung vollstaendig: **ja**
- M5 Implementierung kontrolliert freigegeben: **ja**

Kontrollierte Freigabe bedeutet:

1. M5 darf mit read-only Detection, Dry-Run Cleanup, Trendmetriken, Health-/Entropy-Reports und PostgreSQL-Truth-Erweiterungen fortfahren.
2. Jede Mutation bleibt hinter eigener Safety-Freigabe.
3. Kein M5-Slice darf historische Citations, Workspace-Isolation, Queue-Konsistenz oder Backup/Restore-Faehigkeit verschlechtern.
4. Das erste M5-Implementierungsziel ist die Reduktion des Entropy-Status von `watch` auf `pass`.

## Naechste Pflichtnachweise

1. Live-Duplicate-Cardinality-Audit implementieren und gegen PostgreSQL ausfuehren.
2. `pytest -m postgres_truth tests/postgres_truth -vv` inklusive Cleanup-Truth-Tests mit gesetzter `TEST_DATABASE_URL` ausfuehren.
3. M5-Drift-Detection-Report versionieren.
4. Cleanup nur als Dry-Run weiterfuehren, bis Safety-Gate und Truth-Nachweis gruen sind.
