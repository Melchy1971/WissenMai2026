# Prompt 435 – M4b Observability-Failures fixen

Behebe die 4 M4b Observability-Failures.

Fehlende Tests:
1. test_process_import_job_retry_is_observable_with_job_correlation
2. test_recover_stale_running_job_emits_recovery_observability
3. test_duplicate_import_is_observable_without_logging_sensitive_content
4. test_upload_logs_structured_context_without_document_content

Aufgabe:
1. Prüfe Logging Events:
   - job_retry
   - stale_job_recovered
   - duplicate_import_detected
   - upload_received

2. Pflichtfelder:
   - correlation_id
   - job_id
   - workspace_id
   - document_id optional
   - error_code optional

3. Verboten:
   - Dokumentinhalt im Log
   - Dateitext im Log
   - Passwort/Token im Log

Output:
- Logging-Fix
- Tests grün
- aktualisierter m4b Report
