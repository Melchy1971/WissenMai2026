# Prompt 438 – Masterplan Status nach aktuellen Reports neu berechnen

Berechne masterplan_status.json neu.

Input:
- report_truth_preflight.json
- recovery_sprint_gate.json
- frontend_full_suite_staged_report.json
- m4a_auth_truth.json
- m4b_upload_queue_truth.json
- m4c_lifecycle_retrieval_truth.json
- m4e_backup_restore_truth.json
- m4_backend_release_candidate.json

Regeln:
- M3a bleibt blockiert, solange Full-Suite nicht grün
- M4 bleibt blockiert, solange M4b failt
- M5 bleibt No-Go

Output:
- reports/current/masterplan_status.json
- docs/generated/status_section.md
