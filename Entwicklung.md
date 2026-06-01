# Entwicklung

Statusquelle: `reports/current/m5a_start_gate.json`, `reports/current/m5a_duplicate_detector_gate.json`

M5a Start-Gate (`reports/current/m5a_start_gate.json`): `GO`. Implementierung laeuft.

Duplicate Detector Slice Gate (`reports/current/m5a_duplicate_detector_gate.json`): `GO`, Score 100/100.

---

## Aktiver Slice: Duplicate Detector

Implementiert:

- Datenmodell: `data_quality_runs`, `data_quality_findings` (Migration `20260601_0018`, an `20260508_0014` gekettet)
- `DataQualityRunner` — workspace-scoped, idempotent, read-only, Python 3.10 kompatibel
- `DuplicateDetector` V1 — content_hash, nur aktive Dokumente, DUPLICATE_DOCUMENT warning, DB-agnostische 2-Query-Variante
- Read-Only API: `GET /api/v1/data-quality/runs`, `runs/{id}`, `findings`, `summary`
- Dashboard: Route `/data-quality`, read-only, keine Repair-Actions, `data-testid` vollstaendig
- CLI: `python scripts/run_data_quality.py --workspace <id>`, Report: `reports/current/data_quality_report.json`

Nicht freigegeben ohne separate Governance:

- Cleanup-, Merge- oder Repair-Actions
- `data_quality_metrics`, `data_quality_snapshots`
- Lifecycle-Aenderungen durch Data-Quality-Prozesse

## Ausstehend

Manuell auszufuehren (brauchen laufenden System-Stack):

- `reports/current/operations_selftest_report.json` — `scripts/operations_selftest.ps1`
- `reports/current/reindex_recovery_report.json` — pytest `test_m4e_reindex_recovery_truth.py`

PostgreSQL-Truth-Lauf fuer Duplicate Detector: `pytest -m m5_truth` (braucht `TEST_DATABASE_URL`).
