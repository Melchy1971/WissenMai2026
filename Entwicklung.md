# Entwicklung

Statusquelle: `reports/current/m5a_start_gate.json`, `reports/current/m5a_duplicate_detector_gate.json`, `reports/current/m5a_metadata_detector_gate.json`, `reports/current/m5a_lifecycle_integrity_gate.json`, `reports/current/m5a_data_quality_gate.json`

M5a Start-Gate (`reports/current/m5a_start_gate.json`): `GO`. Implementierung laeuft.

Duplicate Detector Slice Gate (`reports/current/m5a_duplicate_detector_gate.json`): `GO`, Score 100/100.

Metadata Detector Slice Gate (`reports/current/m5a_metadata_detector_gate.json`): `GO`, Score 100/100.

Lifecycle Integrity Slice Gate (`reports/current/m5a_lifecycle_integrity_gate.json`): `GO`, Score 100/100.

---

## Abgeschlossene M5a Slices

- Slice 1: Duplicate Detector (`reports/current/m5a_duplicate_detector_gate.json`) = `PASS`
- Slice 2: Metadata Detector (`reports/current/m5a_metadata_detector_gate.json`) = `PASS`
- Slice 3: Lifecycle Integrity Detector (`reports/current/m5a_lifecycle_integrity_gate.json`) = `PASS`

## Aktiver M5a Slice

- Kein aktiver Blocker im Lifecycle Slice; Slice 3 ist formal abgeschlossen.

## Aktueller Fokus: M5a Gesamtgate-Hardening

Implementiert:

- Datenmodell: `data_quality_runs`, `data_quality_findings` (Migration `20260601_0018`, an `20260508_0014` gekettet)
- `DataQualityRunner` — workspace-scoped, idempotent, read-only, Python 3.10 kompatibel
- `DuplicateDetector` V1 — content_hash, nur aktive Dokumente, DUPLICATE_DOCUMENT warning, DB-agnostische 2-Query-Variante
- `MetadataQualityDetector` V1 — MQ-1..MQ-5 (title/tags/category/doc_type/summary), `MISSING_METADATA`, read-only
- `LifecycleIntegrityDetector` V1 — Search/Retrieval/Lifecycle/source_status Konsistenz, read-only
- Read-Only API: `GET /api/v1/data-quality/runs`, `runs/{id}`, `findings`, `summary`
- Dashboard: Route `/data-quality`, read-only, keine Repair-Actions, `data-testid` vollstaendig
- CLI: `python scripts/run_data_quality.py --workspace <id>`, Report: `reports/current/data_quality_report.json`
- Tests Metadata Slice: `backend/tests/test_metadata_quality_detector.py`, `backend/tests/postgres_truth/test_m5a_metadata_quality_truth.py`
- Tests Lifecycle Slice: `backend/tests/test_lifecycle_integrity_detector.py`, `backend/tests/postgres_truth/test_m5a_lifecycle_integrity_truth.py`

Wichtig: Auch bei PASS der drei Slice-Gates bleibt das M5a-Gesamtgate (`reports/current/m5a_data_quality_gate.json`) an den aktuellen Data-Quality-Run und Integritaetsreports gebunden.

Nicht freigegeben ohne separate Governance:

- Cleanup-, Merge- oder Repair-Actions
- `data_quality_metrics`, `data_quality_snapshots`
- Lifecycle-Aenderungen durch Data-Quality-Prozesse

## Ausstehend

Manuell auszufuehren (brauchen laufenden System-Stack):

- `reports/current/operations_selftest_report.json` — `scripts/operations_selftest.ps1`
- `reports/current/reindex_recovery_report.json` — pytest `test_m4e_reindex_recovery_truth.py`

PostgreSQL-Truth-Lauf fuer Duplicate Detector: `pytest -m m5_truth` (braucht `TEST_DATABASE_URL`).
