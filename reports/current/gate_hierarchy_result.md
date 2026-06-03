# Gate Hierarchy Result

- Result: `FAIL`
- Timestamp: `2026-06-03T08:09:49.106502+00:00`
- Hierarchy Source: `docs/gate_hierarchy.json`

## Gates

| Gate | Status | Mandatory Children | Reports | Blockers |
|---|---|---|---|---|
| Runtime Connectivity Gate | `FAIL` | - | `runtime_connectivity_gate.json` | missing report: H:\WissenMai2026\reports\current\runtime_connectivity_gate.json |
| Frontend Full Suite Staged | `PASS` | - | `frontend_full_suite_staged_report.json` | - |
| Documentation Truth Lint | `PASS` | - | `documentation_truth_lint.json` | - |
| M4a Auth Truth | `PASS` | - | `m4a_auth_truth.json` | - |
| M4b Upload Queue Truth | `PASS` | - | `m4b_upload_queue_truth.json` | - |
| M4c Lifecycle Retrieval Truth | `PASS` | - | `m4c_lifecycle_retrieval_truth.json` | - |
| M4e Backup Restore Truth | `PASS` | - | `m4e_backup_restore_truth.json` | - |
| Report Truth Preflight | `PASS` | - | `report_truth_preflight.json` | - |
| M5a Start Gate | `PASS` | - | `m5a_start_gate.json` | - |
| Report Integrity Pre M5a | `FAIL` | - | `report_integrity_pre_m5a.json` | report_integrity_pre_m5a.json: status/result must be one of ['PASS'], got ['BLOCKED', 'NO_GO']<br>report_integrity_pre_m5a.json: decision.go_no_go must be GO, got 'NO_GO'<br>report_integrity_pre_m5a.json: passed (6) must equal collected (8)<br>report_integrity_pre_m5a.json: failed must be 0, got 2<br>report_integrity_pre_m5a.json: exit_code must be 0, got 1<br>report_integrity_pre_m5a.json: blockers must be empty |
| Data Quality Report V2 | `PASS` | - | `data_quality_report.json` | - |
| Duplicate Detector Gate | `PASS` | - | `m5a_duplicate_detector_gate.json` | - |
| Metadata Detector Gate | `PASS` | - | `m5a_metadata_detector_gate.json` | - |
| Lifecycle Integrity Gate | `PASS` | - | `m5a_lifecycle_integrity_gate.json` | - |
| Source Status Integrity Gate | `FAIL` | - | `m5a_source_status_integrity_gate.json` | missing report: H:\WissenMai2026\reports\current\m5a_source_status_integrity_gate.json |
| Orphan Detector Gate | `FAIL` | - | `m5a_orphan_detector_gate.json` | missing report: H:\WissenMai2026\reports\current\m5a_orphan_detector_gate.json |
| M3a | `BLOCKED` | `runtime_connectivity_gate`, `frontend_full_suite_staged`, `documentation_truth_lint` | - | mandatory child not passed: runtime_connectivity_gate |
| M4 | `PASS` | `m4a_auth_truth`, `m4b_upload_queue_truth`, `m4c_lifecycle_retrieval_truth`, `m4e_backup_restore_truth`, `report_truth_preflight` | - | - |
| M5a | `BLOCKED` | `m5a_start_gate`, `report_integrity_pre_m5a`, `documentation_truth_lint`, `data_quality_report`, `duplicate_detector_gate`, `metadata_detector_gate`, `lifecycle_integrity_gate`, `source_status_integrity_gate`, `orphan_detector_gate` | - | mandatory child not passed: report_integrity_pre_m5a<br>mandatory child not passed: source_status_integrity_gate<br>mandatory child not passed: orphan_detector_gate |

## Dependency Graph

- `runtime_connectivity_gate` -> `m3a`
- `frontend_full_suite_staged` -> `m3a`
- `documentation_truth_lint` -> `m3a`
- `m4a_auth_truth` -> `m4`
- `m4b_upload_queue_truth` -> `m4`
- `m4c_lifecycle_retrieval_truth` -> `m4`
- `m4e_backup_restore_truth` -> `m4`
- `report_truth_preflight` -> `m4`
- `m5a_start_gate` -> `m5a`
- `report_integrity_pre_m5a` -> `m5a`
- `documentation_truth_lint` -> `m5a`
- `data_quality_report` -> `m5a`
- `duplicate_detector_gate` -> `m5a`
- `metadata_detector_gate` -> `m5a`
- `lifecycle_integrity_gate` -> `m5a`
- `source_status_integrity_gate` -> `m5a`
- `orphan_detector_gate` -> `m5a`

## Validator Rules

- `parent_pass_requires_all_mandatory_children_pass`: `True`
- `missing_child_report_blocks_parent`: `True`
- `invalid_json_blocks_parent`: `True`
- `child_pass_status`: `PASS`
- `child_go_decision`: `GO`
- `gate_reports_require_generated_by`: `True`
- `counter_reports_require_collected_gt_zero`: `True`
- `counter_reports_require_passed_equals_collected`: `True`
- `counter_reports_require_failed_errors_skipped_zero`: `True`
- `counter_reports_require_exit_code_zero`: `True`
- `data_quality_report_requires_status_completed`: `True`
- `data_quality_report_min_quality_score`: `90`
