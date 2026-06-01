# Projektstatus

Stand: `reports/current/masterplan_status.json`

Der aktuelle Projektstatus, Data Quality Status, Score und Gate-Entscheidungen werden ausschliesslich aus maschinenlesbaren Reports abgeleitet:

- `reports/current/masterplan_status.json` — Gesamtstatus
- `reports/current/m5a_start_gate.json` — M5a Implementierungsfreigabe
- `reports/current/m5a_duplicate_detector_gate.json` — Duplicate Detector Slice Gate
- `reports/current/data_quality_report.json` — aktueller Data-Quality-Run (generiert via `python scripts/run_data_quality.py`)
- `reports/current/documentation_truth_lint.json` — Dokumentations-Lint

Alle Aussagen, Scores und Gates sind maschinenbasiert. Manuelle Statusaussagen duerfen keine Report-Werte ueberschreiben.

---

## M5a Implementierungsstand

M5a Start-Gate (`reports/current/m5a_start_gate.json`): `GO`.

Duplicate Detector Slice (`reports/current/m5a_duplicate_detector_gate.json`): `GO`, Score 100/100.

Implementiert:

- Datenmodell: `data_quality_runs`, `data_quality_findings` (Migration `20260601_0018`)
- `DataQualityRunner` — workspace-scoped, idempotent, read-only
- `DuplicateDetector` V1 — content_hash, nur aktive Dokumente, Finding-Typ `DUPLICATE_DOCUMENT`
- Read-Only API: `GET /api/v1/data-quality/runs`, `runs/{id}`, `findings`, `summary`
- Dashboard: Route `/data-quality`, read-only, keine Repair-Actions
- CLI: `python scripts/run_data_quality.py --workspace <id>`

Nicht freigegeben und ohne separate Governance ausser Scope:

- Cleanup-, Merge- oder Repair-Actions
- `data_quality_metrics`, `data_quality_snapshots`

---

## Documentation Truth Lint

Aktueller Nachweis: `reports/current/documentation_truth_lint.json`. Status: `PASS`.
