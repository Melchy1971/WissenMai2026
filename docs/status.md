# Projektstatus

Stand: `reports/current/masterplan_status.json`

Der aktuelle Projektstatus, Data-Quality-Status, Score und Gate-Entscheidungen werden ausschliesslich aus maschinenlesbaren Reports abgeleitet:

- `reports/current/masterplan_status.json` - Gesamtstatus und M5-Statusmodell
- `docs/gate_hierarchy.json` - Parent-/Child-Gate-Hierarchie
- `reports/current/m5a_final_readiness_review.json` - M5a Final Readiness und READY_FOR_M5B-Entscheidung
- `reports/current/m5a_data_quality_gate.json` - erforderlicher M5a Data-Quality-Eingang
- `reports/current/m5a_start_gate.json` - M5a Slice-Start-Gate
- `reports/current/m5b_release_decision.json` - M5b PREPARED-/GO-Entscheidung
- `reports/current/documentation_truth_lint.json` - Dokumentations-Lint

Manuelle Statusaussagen duerfen keine Report-Werte ueberschreiben.

## M5a Regel

M5a ist nur dann Gesamt-`PASS`, wenn `reports/current/m5a_final_readiness_review.json` `READY_FOR_M5B` meldet. Diese Entscheidung setzt M5a Data Quality, Report Integrity v2, Documentation Truth Lint und M5a-scope Known Limitations voraus.

Slice-Gates wie `reports/current/m5a_duplicate_detector_gate.json`, `reports/current/m5a_metadata_detector_gate.json` oder `reports/current/m5a_lifecycle_integrity_gate.json` belegen nur ihren jeweiligen Slice. Ein Slice-`PASS` ist keine M5a-Gesamtfreigabe.

## M5b Regel

M5b Drift Architecture darf als Planung `DRAFT` sein, siehe `docs/m5b-drift-architecture.md`.

`reports/current/m5b_release_decision.json` trennt die Stufen: `DRAFT` erlaubt Architekturplanung, `PREPARED` erlaubt Vorbereitung ohne Implementierung, und nur `GO` erlaubt M5b Implementierung. Solange M5a nicht ueber `reports/current/m5a_final_readiness_review.json` bereit ist, bleibt M5b blockiert.

Stand 2026-06-10: M5b Preparation-Artefakte vollstaendig (27/27, PREP-01 bis PREP-27). Architecture Review COMPLETE (8/8, 0 Luecken). Formales `PREPARED` BLOCKED (M5a READY_FOR_M5B fehlt, Report Integrity BLOCKED). Implementation Gate NO-GO. Drift Detection Code nicht vorhanden. Alpha Validation BLOCKED (keine Implementierung; erwartet). Beta Start Gate BLOCKED (3/6; BSG-04/05/06 PASS). M5c NOT_STARTED. Repair-Aktionen und Cleanup-Aktionen sind dauerhaft verboten (PROHIBIT-02, PROHIBIT-06). Quelle: `reports/current/m5b_preparation_gate.json`, `reports/current/m5b_architecture_review.json`, `reports/current/m5b_alpha_validation_report.json`, `reports/current/m5b_beta_start_gate.json`.

## Globale Aussagen

Es gibt keine globale 100%- oder Vollstaendigkeits-Aussage in dieser Datei. Fortschritt, Blocker und Freigaben stehen im generierten Maschinenstatus `reports/current/masterplan_status.json`.

## Documentation Truth Lint

Aktueller Nachweis: `reports/current/documentation_truth_lint.json`.
