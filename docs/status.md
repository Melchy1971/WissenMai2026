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

Stand 2026-06-12: M5b-Implementierung vollstaendig (Drift Detection, CLI, Dashboard, API, Observability, Performance Baseline). M5b-Gates BLOCKED durch Kaskade: Alpha Hardening Gate BLOCKED (AHG-BLOCKER-01: M5a nicht READY_FOR_M5B; AHG-BLOCKER-02: drift_report_integrity PARTIAL) → Beta BLOCKED → Production Readiness BLOCKED. M5c Preparation PREPARED (16/16 Checks, `reports/current/m5c_preparation_gate.json`). M5c GO nicht erlaubt: `reports/current/m5c_start_gate.json` BLOCKED. Cleanup-Implementierung und Repair-Aktionen dauerhaft verboten (PROHIBIT-02, PROHIBIT-06). Quelle: `reports/current/m5b_alpha_hardening_gate.json`, `reports/current/m5b_production_readiness_gate.json`, `reports/current/m5c_preparation_gate.json`, `reports/current/m5c_start_gate.json`.

## M5c Regel

M5c Cleanup darf erst implementiert werden wenn: (1) `reports/current/m5c_start_gate.json` = PASS, (2) PO-Sign-off auf `reports/current/cleanup_governance_boundary.json`. Beides ist aktuell nicht erfuellt. Status: NO_GO.

M5c Preparation = PREPARED bedeutet ausschliesslich: Definitionsdokumente sind komplett und valide. Es bedeutet nicht: GO, nicht: Implementierung erlaubt, nicht: Cleanup freigegeben.

Dry-Run-Only: Jeder M5c-Run ist ein Dry Run. Keine automatische Ausfuehrung ohne explizites PO-Approval je Proposal (No-Auto-Execute, PROHIBIT-08).

## Globale Aussagen

Es gibt keine globale 100%- oder Vollstaendigkeits-Aussage in dieser Datei. Fortschritt, Blocker und Freigaben stehen im generierten Maschinenstatus `reports/current/masterplan_status.json`.

## Documentation Truth Lint

Aktueller Nachweis: `reports/current/documentation_truth_lint.json`.
