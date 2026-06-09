# Gate Hierarchy

Quelle: `docs/gate_hierarchy.json`.

## Pflicht-Hierarchie

| Parent-Gate | Pflicht-Child-Gates |
|---|---|
| M3a | `runtime_connectivity_gate`, `frontend_full_suite_staged`, `documentation_truth_lint` |
| M4 | `m4a_auth_truth`, `m4b_upload_queue_truth`, `m4c_lifecycle_retrieval_truth`, `m4e_backup_restore_truth`, `report_truth_preflight` |
| M5a | `m5a_start_gate`, `report_integrity_v2`, `documentation_truth_lint`, `data_quality_report`, `duplicate_detector_gate`, `metadata_detector_gate`, `lifecycle_integrity_gate`, `source_status_integrity_gate`, `orphan_detector_gate` |

## Validator-Regeln

- Ein Parent-Gate darf nur `PASS` sein, wenn alle Pflicht-Child-Gates `PASS` sind.
- Fehlende, ungueltige oder stale Child-Reports blockieren das Parent-Gate.
- Gate-Validatoren duerfen nur `reports/current` als aktive Reportquelle lesen.
- Root-Level-Reports und `reports/archive` sind keine aktiven Gate-Quellen.
- Gate-Reports muessen `generated_by` setzen.
- Counter-basierte Reports muessen `collected > 0`, `passed = collected`, `failed = 0`, `errors = 0`, `skipped = 0` und `exit_code = 0` erfuellen.
- Reports mit `decision.go_no_go` muessen fuer GO-Abhaengigkeiten `GO` melden.
- `data_quality_report` gilt als bestanden, wenn `status = completed` und `quality_score >= 90` ist.
- Manuelle Statusaussagen duerfen den maschinenlesbaren Gate-Status nicht ueberschreiben.
