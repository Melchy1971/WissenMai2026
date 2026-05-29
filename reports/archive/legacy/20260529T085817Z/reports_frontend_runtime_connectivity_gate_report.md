# Frontend Runtime Connectivity Gate Report

- Result: `FAIL`
- Decision: `M3A_BLOCKED`
- Score: `22.2` / 100
- Threshold: `>= 90.0`
- Generated: `2026-05-20T09:06:12Z`
- Source: `reports/connectivity_truth_report.json`

## Checks

| Check | Result | Evidence |
|---|---|---|
| backend_reachable | `FAIL` | 1 API request(s), 1 failed request(s). |
| health_green | `FAIL` | ECONNREFUSED: connect ECONNREFUSED 127.0.0.1:8000 |
| auth_me_reachable | `FAIL` | ECONNREFUSED: connect ECONNREFUSED 127.0.0.1:8000 |
| login_successful | `FAIL` | Login did not return a successful response. |
| workspace_bootstrap_successful | `FAIL` | No successful authenticated /api/v1/auth/me bootstrap observed. |
| document_list_loads | `FAIL` | No successful /documents response observed in browser flow. |
| no_api_unreachable_normalflow | `FAIL` | API_UNREACHABLE or backend-unreachable copy visible in normal flow. |
| no_cors_error | `PASS` | No CORS/access-control browser error observed. |
| no_mixed_content_error | `PASS` | No mixed-content mismatch detected. |

## Runtime Blocker

- `backend_not_reachable`: 1 API request(s), 1 failed request(s).
- `health_not_green`: ECONNREFUSED: connect ECONNREFUSED 127.0.0.1:8000
- `auth_me_not_reachable`: ECONNREFUSED: connect ECONNREFUSED 127.0.0.1:8000
- `login_not_successful`: Login did not return a successful response.
- `workspace_bootstrap_failed`: No successful authenticated /api/v1/auth/me bootstrap observed.
- `document_list_not_loaded`: No successful /documents response observed in browser flow.
- `api_unreachable_visible`: API_UNREACHABLE or backend-unreachable copy visible in normal flow.

## Failure-Klassifikation

- `REFUSED`
