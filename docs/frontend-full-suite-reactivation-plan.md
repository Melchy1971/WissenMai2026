# Frontend Full-Suite Reactivation Plan

Die Frontend Full-Suite wird schrittweise aktiviert. Eine Gruppe wird nur ausgefuehrt, wenn alle vorherigen Gruppen gruen sind.

Reihenfolge:
1. Auth
2. Workspace
3. Documents
4. Upload
5. Search
6. Chat
7. Lifecycle
8. Diagnostics
9. Error States
10. Concurrency

Regel:
- echte API
- echte DB
- keine Mocks
- pro aktivierter Gruppe: `failed = 0`, `errors = 0`, `skipped = 0`
- naechste Gruppe wird nur aktiviert, wenn die vorherige Gruppe `PASS` ist

Ausfuehren:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://Markus:Markus..2026@85.215.131.200:5432/wissen2026"
$env:TEST_DATABASE_URL = $env:DATABASE_URL
python scripts\run_frontend_full_suite_staged.py --start-api --start-frontend
```

Outputs:
- `reports/archive/legacy/20260605T100000Z/frontend_full_suite_activation_plan.json`
- `reports/archive/legacy/20260605T100000Z/frontend_truth_groups/01_auth_report.json`
- `reports/archive/legacy/20260605T100000Z/frontend_truth_groups/02_workspace_report.json`
- `reports/archive/legacy/20260605T100000Z/frontend_truth_groups/03_documents_report.json`
- `reports/archive/legacy/20260605T100000Z/frontend_truth_groups/04_upload_report.json`
- `reports/archive/legacy/20260605T100000Z/frontend_truth_groups/05_search_report.json`
- `reports/archive/legacy/20260605T100000Z/frontend_truth_groups/06_chat_report.json`
- `reports/archive/legacy/20260605T100000Z/frontend_truth_groups/07_lifecycle_report.json`
- `reports/archive/legacy/20260605T100000Z/frontend_truth_groups/08_diagnostics_report.json`
- `reports/archive/legacy/20260605T100000Z/frontend_truth_groups/09_error_states_report.json`
- `reports/archive/legacy/20260605T100000Z/frontend_truth_groups/10_concurrency_report.json`
- `reports/archive/legacy/20260605T100000Z/frontend_full_suite_staged_report.json`
