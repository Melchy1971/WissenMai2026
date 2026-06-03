# Entwicklung

Statusquelle: `reports/current/masterplan_status.json`, `docs/gate_hierarchy.json`, `reports/current/m5a_data_quality_gate.json`, `reports/current/m5b_start_gate.json`

Aktuelle Freigaben werden nicht manuell gepflegt. Der generierte Maschinenstatus in `reports/current/masterplan_status.json` ist autoritativ.

## Gate-Hierarchie nach Fix

- M5a ist nur dann Gesamt-`PASS`, wenn das Parent-Gate `m5a` nach `docs/gate_hierarchy.json` `PASS` ist.
- Ein M5a Slice-Gate bewertet nur den jeweiligen Slice. Slice-`PASS` ist keine M5a-Gesamtfreigabe.
- `reports/current/m5a_data_quality_gate.json` bleibt das Gesamtgate fuer M5a Data Quality.
- `reports/current/m5b_start_gate.json` bleibt `DRAFT` oder `PREPARED` nur in Abhaengigkeit von M5a; solange M5a nicht `PASS` ist, bleibt M5b blockiert.
- Es gibt keine globale Prozent- oder Vollstaendigkeitsfreigabe ausserhalb maschinenlesbarer Reports.

## M5a Slice-Arbeit

Vorhandene Slice-Artefakte:

- Duplicate Detector: `reports/current/m5a_duplicate_detector_gate.json`
- Metadata Detector: `reports/current/m5a_metadata_detector_gate.json`
- Lifecycle Integrity Detector: `reports/current/m5a_lifecycle_integrity_gate.json`

Diese Reports koennen Slice-Fortschritt belegen. Sie ersetzen nicht `reports/current/m5a_data_quality_gate.json` und nicht die Parent-Gate-Validierung aus `docs/gate_hierarchy.json`.

## M5b Planung

M5b Drift Architecture ist ein Planungsartefakt: `docs/m5b-drift-architecture.md`.

Planung ist unabhaengig vom Start-Gate erlaubt. Implementierung bleibt untersagt, solange `reports/current/m5b_start_gate.json` keine entsprechende Freigabe gemaess M5a-Abhaengigkeit meldet.

## Laufende technische Arbeit

- Data-Quality-Runner, Detectoren, Read-only API und Dashboard bleiben read-only.
- Cleanup-, Merge- oder Repair-Actions brauchen separate Governance.
- Lifecycle-Aenderungen durch Data-Quality-Prozesse bleiben ausser Scope.

## Relevante Tests

- Metadata Slice: `backend/tests/test_metadata_quality_detector.py`, `backend/tests/postgres_truth/test_m5a_metadata_quality_truth.py`
- Lifecycle Slice: `backend/tests/test_lifecycle_integrity_detector.py`, `backend/tests/postgres_truth/test_m5a_lifecycle_integrity_truth.py`
- Gate-Hierarchie: `tests/test_m5a_gate_hierarchy.py`, `backend/tests/test_parent_gate_validator.py`

Testergebnisse und Freigaben werden nur aus aktuellen Reports unter `reports/current/` abgeleitet.
