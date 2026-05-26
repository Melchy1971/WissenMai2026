# M3a Release Candidate

Generated: 2026-05-26T08:11:36.043971Z

## Entscheidung

- gate_passed: `false`
- blocked: `true`
- Go/No-Go: `NO-GO`

## Kriterien

| Kriterium | Status | Evidenz |
| --- | --- | --- |
| Login stabil | PASS | seed=PASS, runtime_login_ok=True, guard=PASS |
| Workspace Bootstrap stabil | PASS | workspace_bootstrap=True, role=admin |
| Frontend Truth gruen | FAIL | 5/100 passed, failed=37, skipped=58 |
| Contracts gruen | PASS | 8/8 contracts, deviations=0 |
| Chaos gruen | PASS | result=PASS, failed=0 |

## Blocker

- `frontend_truth_green`: Frontend Truth gruen

## Inputs

- `seed_smoke`: `reports/seed_smoke_report.json`
- `runtime_connectivity`: `reports/runtime_connectivity_report.json`
- `frontend_truth`: `reports/frontend_truth_report.json`
- `gui_chaos`: `reports/gui_truth/gui_chaos_suite_report.json`
- `contract_runtime`: `reports/contract_runtime_report.json`
- `auth_bootstrap_guard`: `reports/auth_bootstrap_guard.json`
