# Report-Erzeugungsregeln

Aktive Gate-Reports liegen ausschliesslich unter `reports/current`.

Pflichtregeln:

- Gate-Validatoren duerfen aktive Reportquellen nur aus `reports/current` lesen.
- Dateien im Projektroot sind keine aktiven Reportquellen.
- Dateien unter `reports/archive` sind historische Evidenz und duerfen nie Gate-Input sein.
- Veraltete Reports duerfen nicht als aktive Gate-Evidenz akzeptiert werden; Validatoren pruefen maschinenlesbare Timestamps.
- Jeder aktive Report muss `report_schema_version: 1` enthalten.
- Jeder aktive Report muss `generated_by: "gate_validator"` enthalten.
- Reports ohne `generated_by` sind invalid.
- Reports mit einem anderen `generated_by`-Wert gelten als manuell gepflegt und sind invalid.
- `status: "PASS"` ist nur erlaubt, wenn `failed=0`, `errors=0` und `skipped=0` sind.
- `collected` muss `passed + failed + errors + skipped` entsprechen.
- `collected` muss groesser als `0` sein, ausser bei `report_type: "informational"`.
- Final-Release-Reports duerfen nur aus Gate-Validator-Output entstehen.

Legacy- und manuelle Reports werden nicht als Gate-Eingabe gelesen. Sie muessen nach
`reports/archive/<gate>/<timestamp>_<report>.json` verschoben werden.

Der Validator ist `scripts/validate_reports.py`.
