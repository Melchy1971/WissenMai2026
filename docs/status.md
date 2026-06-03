# Projektstatus

Stand: `reports/current/masterplan_status.json`

Der aktuelle Projektstatus, Data-Quality-Status, Score und Gate-Entscheidungen werden ausschliesslich aus maschinenlesbaren Reports abgeleitet:

- `reports/current/masterplan_status.json` - Gesamtstatus und M5-Statusmodell
- `docs/gate_hierarchy.json` - Parent-/Child-Gate-Hierarchie
- `reports/current/m5a_data_quality_gate.json` - M5a Gesamtgate
- `reports/current/m5a_start_gate.json` - M5a Slice-Start-Gate
- `reports/current/m5b_start_gate.json` - M5b Start-Gate
- `reports/current/documentation_truth_lint.json` - Dokumentations-Lint

Manuelle Statusaussagen duerfen keine Report-Werte ueberschreiben.

## M5a Regel

M5a ist nur dann Gesamt-`PASS`, wenn das Parent-Gate `m5a` nach `docs/gate_hierarchy.json` `PASS` ist und `reports/current/m5a_data_quality_gate.json` entsprechend `PASS` meldet.

Slice-Gates wie `reports/current/m5a_duplicate_detector_gate.json`, `reports/current/m5a_metadata_detector_gate.json` oder `reports/current/m5a_lifecycle_integrity_gate.json` belegen nur ihren jeweiligen Slice. Ein Slice-`PASS` ist keine M5a-Gesamtfreigabe.

## M5b Regel

M5b Drift Architecture darf als Planung `DRAFT` sein, siehe `docs/m5b-drift-architecture.md`.

`reports/current/m5b_start_gate.json` darf erst `PREPARED` melden, wenn M5a Gesamt-`PASS` ist und die weiteren M5b-Vorbereitungsbedingungen erfuellt sind. Solange M5a nicht `PASS` ist, bleibt M5b blockiert.

## Globale Aussagen

Es gibt keine globale 100%- oder Vollstaendigkeits-Aussage in dieser Datei. Fortschritt, Blocker und Freigaben stehen im generierten Maschinenstatus `reports/current/masterplan_status.json`.

## Documentation Truth Lint

Aktueller Nachweis: `reports/current/documentation_truth_lint.json`.
