# Prompt 436 – M4 Backend RC generieren

Generiere M4 Backend Release Candidate.

Voraussetzungen:
- m4a_auth_truth PASS
- m4b_upload_queue_truth PASS
- m4c_lifecycle_retrieval_truth PASS
- m4e_backup_restore_truth PASS
- report_truth_preflight PASS
- keine invalid JSON Reports

Output:
- reports/current/m4_backend_release_candidate.json
- reports/current/m4_backend_release_candidate.md
- M4 Backend Go/No-Go
