<!-- BEGIN GENERATED MASTERPLAN STATUS -->
## Maschinenstatus Masterplan

Stand: `2026-05-26T12:19:07.849356+00:00`

Gesamtstatus: `blocked`
Gesamtfortschritt: `17.5%`
Freigabe: `nein`

> Dieser Abschnitt ist maschinell aus Artefakten generiert. Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben.

### Phasen

| Phase | Status | Entscheidung | Score | Quelle |
|---|---|---|---|---|
| M3a Frontend Foundation | `draft` | `UNKNOWN` | - | `reports/m3a_release_candidate.json` |
| M4 Stabilization | `tested` | `NO_GO` | 93.48 | `reports/m4_release_candidate.json` |
| M5 Start | `blocked` | `NO_GO` | - | `docs/known_limitations.json` |
| Operational Governance | `blocked` | `NO_GO` | - | `docs/known_limitations.json` |

### Gate-Scores

| Gate | Score | Status | Quelle |
|---|---:|---|---|
| `m3a_gate` | - | `draft` | `reports/m3a_release_candidate.json` |
| `frontend_truth` | 5.0 | `-` | `reports/frontend_truth_report.json` |
| `m4a_auth` | 100.0 | `PARTIAL_PASS_BLOCKED_BY_M4_TRUTH` | `reports/m4_release_candidate.json` |
| `m4b_upload_queue` | 91.7 | `PARTIAL_PASS_BLOCKED_BY_M4_TRUTH` | `reports/m4_release_candidate.json` |
| `m4c_lifecycle_retrieval` | 100.0 | `PARTIAL_PASS_BLOCKED_BY_M4_TRUTH` | `reports/m4_release_candidate.json` |
| `m4_postgres_truth` | 93.48 | `-` | `reports/postgres_truth_report.json` |

### Blocker

- `frontend_truth_green` (m3a, None): None Quelle: `reports/m3a_release_candidate.json`
- `missing_m4_split_gate_reports` (m4, blocking): reports/m4a_auth_truth_report.json, reports/m4b_upload_queue_truth_report.json, reports/m4c_lifecycle_retrieval_truth_report.json, reports/m4e_backup_restore_truth_report.json and reports/m4_truth_report.json are not present. Quelle: `reports/m4_release_candidate.json`
- `postgres_truth_m4_not_green` (m4, blocking): reports/postgres_truth_report.json is blocked: 120/138 passed, 16 failed, 2 errors, exit_code=1. Quelle: `reports/m4_release_candidate.json`
- `m4b_truth_failure` (m4, blocking): tests/postgres_truth/test_m4_truth_flows.py::test_postgres_truth_recover_stale_import_job_retries_without_duplicate_rows failed and is M4b-critical. Quelle: `reports/m4_release_candidate.json`
- `postgres_truth_setup_errors` (m4, blocking): reports/postgres_truth_report.json records 2 setup/collect errors; unclassified setup errors are gate-blocking until resolved. Quelle: `reports/m4_release_candidate.json`
- `KL-M4-001` (m5, blocking): Der aktuelle PostgreSQL-Truth-Report ist nicht gruen: 138 collected, 120 passed, 16 failed, 2 errors, exit_code 1. Quelle: `docs/known_limitations.json`
- `KL-M4-003` (m5, blocking): PostgreSQL Truth enthaelt 2 Setup-/Collect-Errors; unklassifizierte Setup-Errors bleiben gate-blockierend. Quelle: `docs/known_limitations.json`
- `KL-M5-001` (m5, blocking): M5 Startgate bleibt blockiert, solange M4 Gesamtgate nicht PASS ist. Quelle: `docs/known_limitations.json`
- `KL-M5-002` (m5, blocking): Aktuelle PostgreSQL-Truth-Findings enthalten 15 M5 Entropy-/Drift-Failures. Quelle: `docs/known_limitations.json`
- `KL-M5-001` (governance, blocking): M5 Startgate bleibt blockiert, solange M4 Gesamtgate nicht PASS ist. Quelle: `docs/known_limitations.json`
- `KL-M5-003` (governance, blocking): Operational Governance Gate darf erst nach M5 Startgate blockierend bewertet werden. Quelle: `docs/known_limitations.json`
- `KL-M4-001` (M4, blocking): Der aktuelle PostgreSQL-Truth-Report ist nicht gruen: 138 collected, 120 passed, 16 failed, 2 errors, exit_code 1. Quelle: `docs/known_limitations.json`
- `KL-M4-002` (M4b, blocking): M4b-kritischer Truth-Test fuer stale import job recovery ist rot. Quelle: `docs/known_limitations.json`
- `KL-M4-003` (M4, blocking): PostgreSQL Truth enthaelt 2 Setup-/Collect-Errors; unklassifizierte Setup-Errors bleiben gate-blockierend. Quelle: `docs/known_limitations.json`
- `KL-M4-004` (M4, blocking): Split-Reports fuer M4a, M4b, M4c, M4e und M4 Gesamt fehlen im reports-Verzeichnis. Quelle: `docs/known_limitations.json`
- `KL-M5-001` (M5, blocking): M5 Startgate bleibt blockiert, solange M4 Gesamtgate nicht PASS ist. Quelle: `docs/known_limitations.json`
- `KL-M5-002` (M5, blocking): Aktuelle PostgreSQL-Truth-Findings enthalten 15 M5 Entropy-/Drift-Failures. Quelle: `docs/known_limitations.json`
- `KL-M5-003` (M5, blocking): Operational Governance Gate darf erst nach M5 Startgate blockierend bewertet werden. Quelle: `docs/known_limitations.json`
- `DRA-001` (documentation, blocking): Documentation Release Audit blockiert Freigabe. Quelle: `reports/documentation_release_audit.json`
- `DRA-002` (documentation, blocking): Documentation Release Audit blockiert Freigabe. Quelle: `reports/documentation_release_audit.json`
- `DRA-003` (documentation, blocking): Documentation Release Audit blockiert Freigabe. Quelle: `reports/documentation_release_audit.json`
- `DRA-004` (documentation, blocking): Documentation Release Audit blockiert Freigabe. Quelle: `reports/documentation_release_audit.json`
- `gate_drift_fail` (gate_drift, blocking): Gate Drift Detection meldet 9 Findings. Quelle: `reports/gate_drift_report.json`
<!-- END GENERATED MASTERPLAN STATUS -->
