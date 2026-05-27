# Gate Hierarchy Result

- Result: `FAIL`
- Timestamp: `2026-05-27T06:57:20.792133+00:00`

## Gates

| Gate | Status | Dependencies | Reports | Blockers |
|---|---|---|---|---|
| M3a Gate | `FAIL` | - | `m3a_frontend_truth.json` | m3a_frontend_truth.json: passed (5) must equal collected (100)<br>m3a_frontend_truth.json: failed must be 0, got 37<br>m3a_frontend_truth.json: skipped must be 0, got 58<br>m3a_frontend_truth.json: exit_code must be 0, got 1<br>m3a_frontend_truth.json: failed_tests must be empty |
| M4a Gate | `PASS` | - | `m4a_auth_truth.json` | - |
| M4b Gate | `PASS` | - | `m4b_upload_queue_truth.json` | - |
| M4c Gate | `PASS` | - | `m4c_lifecycle_retrieval_truth.json` | - |
| M4e Gate | `PASS` | - | `m4e_backup_restore_truth.json` | - |
| M4 Cross-Cutting Gate | `FAIL` | - | `m4_truth_report.json` | missing report: H:\WissenMai2026\reports\current\m4_truth_report.json |
| M4 Gesamtgate | `BLOCKED` | `m4_crosscutting_gate`, `m4a_gate`, `m4b_gate`, `m4c_gate`, `m4e_gate` | - | dependency not passed: m4_crosscutting_gate |
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
