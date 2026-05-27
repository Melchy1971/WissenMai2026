# Gate Hierarchy Result

- Result: `FAIL`
- Timestamp: `2026-05-27T12:43:45.811411+00:00`

## Gates

| Gate | Status | Dependencies | Reports | Blockers |
|---|---|---|---|---|
| M3a Gate | `FAIL` | - | `m3a_frontend_truth.json` | m3a_frontend_truth.json: passed (5) must equal collected (100)<br>m3a_frontend_truth.json: failed must be 0, got 37<br>m3a_frontend_truth.json: skipped must be 0, got 58<br>m3a_frontend_truth.json: exit_code must be 0, got 1<br>m3a_frontend_truth.json: failed_tests must be empty |
| M4a Gate | `PASS` | - | `m4a_auth_truth.json` | - |
| M4b Gate | `FAIL` | - | `m4b_upload_queue_truth.json` | m4b_upload_queue_truth.json: passed (46) must equal collected (51)<br>m4b_upload_queue_truth.json: failed must be 0, got 5<br>m4b_upload_queue_truth.json: exit_code must be 0, got 1<br>m4b_upload_queue_truth.json: failed_tests must be empty |
| M4c Gate | `PASS` | - | `m4c_lifecycle_retrieval_truth.json` | - |
| M4e Gate | `PASS` | - | `m4e_backup_restore_truth.json` | - |
| M4 Cross-Cutting Gate | `FAIL` | - | `m4_truth_report.json` | m4_truth_report.json: passed (94) must equal collected (99)<br>m4_truth_report.json: failed must be 0, got 5<br>m4_truth_report.json: exit_code must be 0, got 1<br>m4_truth_report.json: failed_tests must be empty |
| M4 Gesamtgate | `BLOCKED` | `m4_crosscutting_gate`, `m4a_gate`, `m4b_gate`, `m4c_gate`, `m4e_gate` | - | dependency not passed: m4_crosscutting_gate<br>dependency not passed: m4b_gate |
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
