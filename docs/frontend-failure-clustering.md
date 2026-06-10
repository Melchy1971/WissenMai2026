# Frontend Failure Clustering

`scripts/cluster_frontend_failures.py` classifies Frontend Truth failures after a Playwright run.

Input:
- Playwright or Frontend Truth JSON report, default `reports/archive/legacy/20260605T100000Z/m3a_frontend_truth.json`
- Playwright artifacts from `frontend/test-results`
- Error contexts, screenshots, traces, console errors, and network errors when present

Output:
- `reports/archive/legacy/20260605T100000Z/frontend_failure_clusters.json`

Clusters:
- Setup Failure
- Selector Failure
- Auth Failure
- Workspace Failure
- API Failure
- Routing Failure
- Timeout Failure
- Test Data Missing

Rules:
- The report is informational and must not be used as a Gate PASS/FAIL source.
- The report is generated with `generated_by: gate_validator`.
- `run_gui_truth.py` writes the cluster report automatically after each Frontend Truth report.
- Manual cluster reports are not authoritative for release status.

Manual run:

```powershell
python scripts\cluster_frontend_failures.py
```

Custom input:

```powershell
python scripts\cluster_frontend_failures.py --report reports\current\m3a_frontend_truth.json --test-results frontend\test-results --output reports\current\frontend_failure_clusters.json
```
