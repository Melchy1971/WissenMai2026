# Prompt 432 – Report Truth Preflight erzeugen

Implementiere und führe Report Truth Preflight aus.

Problem:
reports/current/report_truth_preflight.json fehlt und blockiert Full-Suite-Reaktivierung.

Aufgabe:
1. Prüfe alle Reports in reports/current:
   - gültiges JSON
   - report_schema_version
   - report_name
   - gate
   - status
   - timestamp
   - collected
   - passed
   - failed
   - errors
   - skipped
   - exit_code
   - generated_by

2. Regeln:
   - PASS nur bei failed=0, errors=0, skipped=0
   - collected > 0 für Truth-Reports
   - fehlende Pflichtreports blockieren

Output:
- reports/current/report_truth_preflight.json
- invalid_reports
- blocker
