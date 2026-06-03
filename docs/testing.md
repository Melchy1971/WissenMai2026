# Testing

Statusquelle: `reports/current/masterplan_status.json`, `docs/gate_hierarchy.json`, `reports/current/documentation_truth_lint.json`

Tests koennen Implementierungs- oder Slice-Reife belegen, aber keine Parent-Gate- oder Gesamtfreigabe manuell ersetzen.

## Gate-Hierarchie

- Parent-Gates folgen `docs/gate_hierarchy.json`.
- M5a Gesamt-`PASS` ist nur zulaessig, wenn das Parent-Gate `m5a` `PASS` ist und `reports/current/m5a_data_quality_gate.json` `PASS` meldet.
- Ein Slice-Test oder Slice-Gate belegt nur den jeweiligen Slice.
- M5b darf nur `DRAFT` als Planung oder `PREPARED` nach `reports/current/m5b_start_gate.json` sein. M5b wird nicht automatisch durch M5a-Slice-Ergebnisse freigegeben.

## Relevante Testbereiche

- Parent-Gate Validator: `backend/tests/test_parent_gate_validator.py`
- M5a Gate-Hierarchie: `tests/test_m5a_gate_hierarchy.py`
- Masterplan Status Engine: `backend/tests/test_masterplan_status_engine_v3.py`
- Data Quality Detectoren: `backend/tests/test_metadata_quality_detector.py`, `backend/tests/test_lifecycle_integrity_detector.py`
- PostgreSQL Truth fuer M5a-Slices: `backend/tests/postgres_truth/`

## Statusregeln

- Keine globale 100%-Aussage aus lokalen Testlaeufen.
- Keine manuelle PASS-/FAIL-/GO-/NO-GO-Aussage ohne Reportreferenz.
- Testergebnisse muessen in aktuelle Reports unter `reports/current/` einfliessen, bevor sie Gate-Entscheidungen tragen.
- `reports/current/documentation_truth_lint.json` prueft, ob Statusaussagen ausreichend referenziert sind.
