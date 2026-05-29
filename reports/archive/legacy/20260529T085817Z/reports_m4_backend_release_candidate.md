# M4 Backend Release Candidate

**Entscheidung: NO-GO**  
Stand: 2026-05-26T08:28:56.846946+00:00

---

## Score-Matrix

| Gate | Score | Threshold | Status |
|------|-------|-----------|--------|
| `m4a_auth_truth` | 96.8% | ≥ 95.0% | **FAIL** |
| `m4b_upload_queue` | 100.0% | ≥ 90.0% | **PASS** |
| `m4c_lifecycle` | 100.0% | ≥ 90.0% | **PASS** |
| `m4e_backup` | 100.0% | DECIDED | **DECIDED_PASS** |

## Gate-Details

| Gate | Collected | Passed | Failed | Errors | Exit |
|------|-----------|--------|--------|--------|------|
| `m4_truth` | 9 | 9 | 0 | 0 | 0 |
| `m4a_auth_truth` | 31 | 30 | 0 | 1 | 1 |
| `m4b_upload_queue_truth` | 12 | 12 | 0 | 0 | 0 |
| `m4c_lifecycle_retrieval_truth` | 10 | 10 | 0 | 0 | 0 |
| `m4e_backup_restore_truth` | 9 | 9 | 0 | 0 | 0 |

## Blocker

- **[CRITICAL]** `m4a_auth_truth`: score=96.8%, threshold=95.0%, errors=1, failed=0
- **[CRITICAL]** `KL-M4-003`: PostgreSQL Truth enthält 1 unklassifizierten Setup-/Collect-Error in m4a_auth_truth.

## Known Limitations

### Geschlossen

- `KL-M4-001` — SUPERSEDED: Split-Reports 2026-05-26 zeigen M4-Marker-Tests korrekt. Alter central report obsolet.
- `KL-M4-002` — RESOLVED: m4b_upload_queue_truth 12/12 passed, 0 errors, exit_code 0.
- `KL-M4-004` — RESOLVED: Split-Reports für alle M4-Marker vorhanden (reports/<marker>_report.json).

### Offen

- `KL-M4-003` [CRITICAL]: PostgreSQL Truth enthält 1 unklassifizierten Setup-/Collect-Error in m4a_auth_truth.
  - Aktion: m4a_auth_truth Error-Ursache isolieren und beseitigen. errors=0 ist Pflicht.

## Hinweise

m4a: Score 96.8% ≥ 95% — Threshold erreicht. Einziger Blocker: errors=1 (Setup-Error). Keine failed_tests. M4b vollständig grün. M4c vollständig grün. M4e Minimal-Pfad als DECIDED_PASS gesetzt (KL-NB-002).

---

### Freigabe-Entscheidung

**NO-GO** — M4 Backend ist nicht freigebbar bis `m4a_auth_truth errors=0`.
Alle anderen M4-Marker bestehen. Ein Setup-Error in m4a blockiert den Release.
