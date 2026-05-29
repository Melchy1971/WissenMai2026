# Gate Hierarchy Result

- Result: `FAIL`
- Timestamp: `2026-05-26T08:36:46.177205+00:00`

## Gates

| Gate | Status | Dependencies | Reports | Blockers |
|---|---|---|---|---|
| M3a Gate | `FAIL` | - | `m3a_truth_report.json`, `frontend_truth_report.json` | m3a_truth_report.json: collected must be > 0, got 0<br>m3a_truth_report.json: exit_code must be 0, got 1<br>frontend_truth_report.json: passed (5) must equal collected (100)<br>frontend_truth_report.json: failed must be 0, got 37<br>frontend_truth_report.json: errors must be 0, got None<br>frontend_truth_report.json: skipped must be 0, got 58<br>frontend_truth_report.json: exit_code must be 0, got 1<br>frontend_truth_report.json: failed_tests must be empty |
| M4a Gate | `FAIL` | - | `m4a_auth_truth_report.json` | m4a_auth_truth_report.json: passed (42) must equal collected (43)<br>m4a_auth_truth_report.json: errors must be 0, got 1<br>m4a_auth_truth_report.json: exit_code must be 0, got 1 |
| M4b Gate | `FAIL` | - | `m4b_upload_queue_truth_report.json` | m4b_upload_queue_truth_report.json: passed (46) must equal collected (51)<br>m4b_upload_queue_truth_report.json: failed must be 0, got 5<br>m4b_upload_queue_truth_report.json: exit_code must be 0, got 1<br>m4b_upload_queue_truth_report.json: failed_tests must be empty |
| M4c Gate | `FAIL` | - | `m4c_lifecycle_retrieval_truth_report.json` | m4c_lifecycle_retrieval_truth_report.json: passed (155) must equal collected (179)<br>m4c_lifecycle_retrieval_truth_report.json: failed must be 0, got 9<br>m4c_lifecycle_retrieval_truth_report.json: errors must be 0, got 15<br>m4c_lifecycle_retrieval_truth_report.json: exit_code must be 0, got 1<br>m4c_lifecycle_retrieval_truth_report.json: failed_tests must be empty |
| M4e Gate | `PASS` | - | `m4e_backup_restore_truth_report.json` | - |
| M4 Cross-Cutting Gate | `PASS` | - | `m4_truth_report.json` | - |
| M4 Gesamtgate | `BLOCKED` | `m4_crosscutting_gate`, `m4a_gate`, `m4b_gate`, `m4c_gate`, `m4e_gate` | - | dependency not passed: m4a_gate<br>dependency not passed: m4b_gate<br>dependency not passed: m4c_gate |
| M5 Startgate | `BLOCKED` | `m4_overall_gate` | - | dependency not passed: m4_overall_gate |
| Operational Governance Gate | `BLOCKED` | `m5_start_gate` | `governance_truth_report.json` | dependency not passed: m5_start_gate |

## Dependency Graph

- `m4_crosscutting_gate` -> `m4_overall_gate`
- `m4a_gate` -> `m4_overall_gate`
- `m4b_gate` -> `m4_overall_gate`
- `m4c_gate` -> `m4_overall_gate`
- `m4e_gate` -> `m4_overall_gate`
- `m4_overall_gate` -> `m5_start_gate`
- `m5_start_gate` -> `operational_governance_gate`
