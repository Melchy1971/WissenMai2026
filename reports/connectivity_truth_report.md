# Frontend Connectivity Truth Report

- Result: `FAIL`
- Generated: `2026-05-20T09:05:54.397Z`
- Frontend: `http://localhost:5173`
- API: `http://127.0.0.1:8000`

## Checks

| Check | Result | Evidence |
|---|---|---|
| frontend_reaches_backend | `FAIL` | 1 API request(s), 1 failed request(s). |
| health_reachable | `FAIL` | ECONNREFUSED: connect ECONNREFUSED 127.0.0.1:8000 |
| auth_me_reachable | `FAIL` | ECONNREFUSED: connect ECONNREFUSED 127.0.0.1:8000 |
| login_possible | `FAIL` | Login did not return a successful response. |
| workspace_bootstrap_successful | `FAIL` | No successful authenticated /api/v1/auth/me bootstrap observed. |
| document_list_loads | `FAIL` | No successful /documents response observed in browser flow. |
| no_api_unreachable_normalflow | `FAIL` | API_UNREACHABLE or backend-unreachable copy visible in normal flow. |
| authorization_header_correct | `FAIL` | No browser request with Authorization header observed. |
| x_workspace_id_correct | `FAIL` | No browser request with X-Workspace-Id observed. |
| no_cors_error | `PASS` | No CORS/access-control browser error observed. |
| no_mixed_content_error | `PASS` | No mixed-content mismatch detected. |
| no_dns_error | `PASS` | No DNS failure detected. |
| no_timeout | `PASS` | No timeout detected. |

## Failure-Klassifikation

- `REFUSED`

## Failed Requests

- `POST http://127.0.0.1:8000/api/v1/auth/login` -> `net::ERR_CONNECTION_REFUSED`
