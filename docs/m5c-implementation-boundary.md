# M5c Implementation Boundary

**Status:** DEFINITION  
**Datum:** 2026-06-12  
**Invariante:** Diese Boundary ist verbindlich. Abweichungen erfordern neues Gate + PO-Sign-off.

---

## Erlaubt in M5c

| Bereich | Beschreibung |
|---------|-------------|
| **Candidate Detection** | Erkennen von Duplikaten, Orphans, Unused Metadata via read-only SQL |
| **Dry Run Reports** | Erzeugen von Dry-Run-Reports (cleanup_report.json, cleanup_summary.json) |
| **Risk Scoring** | Berechnen und Speichern von risk_score pro CleanupCandidate |
| **Dashboard** | Read-only Anzeige von Kandidaten, Risk Breakdown, Run History |
| **Audit Trail** | Schreiben von Audit-Einträgen (INSERT-only, cleanup_audit) |

---

## Verboten in M5c

| Aktion | Code-Mapping | PROHIBIT-Referenz |
|--------|-------------|-------------------|
| **Delete** | `DELETE FROM documents` | PROHIBIT-04 |
| **Merge** | `UPDATE documents SET ... WHERE id IN (...)` | PROHIBIT-05 |
| **Repair** | Jede Schreiboperation auf `documents`, `chunks`, `citations` zur Korrektur | PROHIBIT-02 |
| **Reindex** | Trigger auf Vector-Index-Rebuild | PROHIBIT-07 |
| **Lifecycle-Änderungen** | `UPDATE documents SET lifecycle_status = ...` | PROHIBIT-03 |
| **Auto-Execute** | Automatische Ausführung von Proposals ohne PO-Sign-off | PROHIBIT-08 |
| **Bulk-Actions** | Massenoperationen auf documents ohne Einzel-Review | PROHIBIT-09 |

---

## Datenbankzugriff

| Operation | Tabelle | Erlaubt |
|-----------|---------|---------|
| SELECT | documents | ja |
| SELECT | chunks | ja |
| SELECT | citations | ja |
| SELECT | document_metadata | ja |
| SELECT | drift_findings | ja |
| INSERT | cleanup_runs | ja |
| INSERT | cleanup_candidates | ja |
| INSERT | cleanup_proposals | ja |
| INSERT | cleanup_audit | ja |
| UPDATE | cleanup_proposals (status only) | ja (nach PO-Approval) |
| UPDATE | documents | **nein** |
| DELETE | (any table) | **nein** |

---

## API-Boundary

Erlaubte Endpunkte:
- `GET /api/cleanup/status`
- `GET /api/cleanup/runs`
- `GET /api/cleanup/runs/{run_id}`
- `GET /api/cleanup/candidates`
- `GET /api/cleanup/proposals`
- `POST /api/cleanup/runs` (startet Dry Run, keine Datenänderung)

Verbotene Endpunkte:
- `POST /api/cleanup/execute` — nicht implementieren
- `DELETE /api/cleanup/*` — nicht implementieren
- `PUT/PATCH /api/cleanup/documents/*` — nicht implementieren

---

## Code-Boundary

M5c darf keine Module aus folgenden Bereichen aufrufen:
- `app.services.document_writer` (Schreibzugriff auf documents)
- `app.services.index_manager` (Reindex-Trigger)
- `app.services.lifecycle_manager` (Lifecycle-Änderungen)

M5c-Module dürfen aufgerufen werden von:
- Dashboard-Frontend (read-only Queries)
- Scheduler (Dry-Run-Trigger, kein Schreibzugriff auf documents)

---

## Änderungshistorie

| Datum | Änderung |
|-------|---------|
| 2026-06-12 | Initial erstellt |
