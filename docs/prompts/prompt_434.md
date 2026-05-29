# Prompt 434 – M4b Duplicate-Import Failure fixen

Behebe den M4b-Fehler:

tests/integration/test_documents_import.py::test_parallel_duplicate_imports_create_single_document

Prüfe:
1. Unique Constraint auf workspace_id + content_hash
2. Advisory Lock für parallelen Import
3. Konfliktbehandlung bei IntegrityError
4. gleiche document_id oder DUPLICATE_DOCUMENT für zweiten Upload
5. keine doppelten Versionen
6. keine doppelten Chunks

Output:
- Root Cause
- Code-Fix
- grüner Einzeltest
- aktualisierter reports/current/m4b_upload_queue_truth.json
