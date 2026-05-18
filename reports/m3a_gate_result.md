# M3a Gate Result

| Feld | Wert |
|---|---|
| Gate Result | FAIL |
| Score | 57.1 |
| Regeln | 4 / 7 |
| Timestamp | `2026-05-18T10:00:21.705779+00:00` |

## Regeln

| Regel | Status | Blocker |
|---|---|---|
| `frontend_truth_passed_equals_collected` | FAIL | frontend_truth passed (58) must equal collected (80) |
| `frontend_truth_failed_zero` | FAIL | frontend_truth failed must be 0, got 22 |
| `frontend_truth_skipped_zero` | PASS |  |
| `postgres_truth_green` | FAIL | postgres_truth passed (120) must equal collected (138); postgres_truth failed must be 0, got 16; postgres_truth errors must be 0, got 2; postgres_truth exit code must be 0, got 1 |
| `contract_tests_green` | PASS |  |
| `no_api_unreachable_in_normalflow` | PASS |  |
| `no_workspace_not_configured_after_valid_login` | PASS |  |

## Blocker

- frontend_truth passed (58) must equal collected (80)
- frontend_truth failed must be 0, got 22
- postgres_truth passed (120) must equal collected (138); postgres_truth failed must be 0, got 16; postgres_truth errors must be 0, got 2; postgres_truth exit code must be 0, got 1
