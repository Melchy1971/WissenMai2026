# Gate Drift Report

- Result: `FAIL`
- Generated: `2026-05-20T08:27:56.314584+00:00`
- Baseline: `H:\WissenMai2026\reports\gate_drift_baseline.json`
- Max report age hours: `168`

## Fail-Regeln

- Gate report missing, unreadable, timestamp-less or stale.
- Current report collected count below baseline.
- Required gate marker missing from taxonomy.
- Unclassified or ambiguous tests present.
- Gate score rises while failed+error count rises.
- Documentation references missing or stale gate report.
- Baseline missing or unreadable.

## Findings

| ID | Severity | Rule | Message |
|---|---|---|---|
| `GDD-BASELINE-MISSING` | `critical` | Gate Drift Detection braucht eine Baseline. | Baseline fehlt oder ist unlesbar; Regressionen gegen vorherige Testmengen koennen nicht bewertet werden. |
| `GDD-REPORT-MISSING` | `critical` | Gate nutzt keinen fehlenden oder unlesbaren Report. | m3a_truth_report.json ist nicht verfuegbar. |
| `GDD-REPORT-MISSING` | `critical` | Gate nutzt keinen fehlenden oder unlesbaren Report. | m4_truth_report.json ist nicht verfuegbar. |
| `GDD-REPORT-MISSING` | `critical` | Gate nutzt keinen fehlenden oder unlesbaren Report. | m4a_auth_truth_report.json ist nicht verfuegbar. |
| `GDD-REPORT-MISSING` | `critical` | Gate nutzt keinen fehlenden oder unlesbaren Report. | m4b_upload_queue_truth_report.json ist nicht verfuegbar. |
| `GDD-REPORT-MISSING` | `critical` | Gate nutzt keinen fehlenden oder unlesbaren Report. | m4c_lifecycle_retrieval_truth_report.json ist nicht verfuegbar. |
| `GDD-REPORT-MISSING` | `critical` | Gate nutzt keinen fehlenden oder unlesbaren Report. | m4e_backup_restore_truth_report.json ist nicht verfuegbar. |
| `GDD-REPORT-MISSING` | `critical` | Gate nutzt keinen fehlenden oder unlesbaren Report. | m5_truth_report.json ist nicht verfuegbar. |
| `GDD-REPORT-MISSING` | `critical` | Gate nutzt keinen fehlenden oder unlesbaren Report. | governance_truth_report.json ist nicht verfuegbar. |
