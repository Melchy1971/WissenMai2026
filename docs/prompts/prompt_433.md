# Prompt 433 – Recovery Sprint Gate erzeugen

Erzeuge recovery_sprint_gate.json.

Input:
- frontend_truth_minimal_report.json
- frontend_full_suite_staged_report.json
- m4a_auth_truth.json
- m4b_upload_queue_truth.json
- m4c_lifecycle_retrieval_truth.json
- m4e_backup_restore_truth.json
- report_truth_preflight.json

Bewertung:
1. Minimal Slice grün?
2. Auth-Gruppe Full-Suite stabil genug?
3. M4a grün?
4. M4b noch blockiert?
5. M4c grün?
6. M4e grün?
7. Reports valide?

Output:
- reports/current/recovery_sprint_gate.json
- Go/No-Go für Full-Suite-Reaktivierung
