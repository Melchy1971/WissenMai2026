# Known Limitations Fixlog

## 2026-06-09 - KL-M5-T-001

Status: offen gelassen.

Pruefung:

- Beschreibung gelesen: M5 Entropy-/Drift-Truth blockiert Slice-Start.
- Blockiertes Gate bestaetigt: `m5_truth_gate`.
- Evidence geprueft: `reports/current/m4_truth_report.json` ist PASS, schliesst M5-Governance aber explizit aus und erledigt KL-M5-T-001 daher nicht.
- Zusaetzliche Evidence geprueft: `reports/current/pre_m5_decision_report.json` fuehrt KL-M5-T-001 weiterhin als aktiven Slice-Level-Blocker.
- Archiv-Evidence geprueft: `reports/archive/m5_truth/20260527T065210Z_m5_truth_report.json` war rot (`35/44`, `failed=9`, `exit_code=1`) und ist kein aktueller PASS-Nachweis.

Aenderung:

- `status` bleibt `open`.
- `blocks_gate` bleibt `["m5_truth_gate"]`.
- `target_phase` konkretisiert auf `M5a Data Quality / M5 Slice Start`.
- `evidence_report` auf `reports/current/pre_m5_decision_report.json` gesetzt.
- `next_action` konkretisiert: aktuellen M5-Truth-Run ausfuehren, `reports/current/m5_truth_report.json` mit `status=PASS`, `failed=0`, `errors=0`, `blockers=[]` erzeugen und erst danach das Gate freigeben.

## 2026-06-09 - KL-M5-T-002

Status: offen gelassen, aber Gate-Zuordnung korrigiert.

Pruefung:

- Beschreibung gelesen: drei Pflicht-Artefakte fehlen vor Slice-Start.
- Bisher blockiertes Gate war generisch `m5_slice_start_gate`.
- Evidence geprueft: `docs/m5-preparation.md` beschreibt generische M5-Slice-Vorbedingungen.
- Aktuelle Gate-Evidence geprueft: `reports/current/m5b_start_gate.json` fuehrt die Retrieval-Baseline als nicht release-grade und als Blocker fuer M5b-Implementierung, nicht fuer M5b `PREPARED`.
- Aktuelle Baseline geprueft: `reports/current/retrieval_quality_baseline_report.json` ist `WARN`, `baseline_release_grade=false`, `requires_golden_retrieval_benchmark=true`.
- M5a Readiness geprueft: `reports/current/m5a_final_readiness_review.json` blockiert M5a durch Parent-/Child-Gates, Report Integrity, Source Status, Orphan, stale Child-Gates und Parent-Evidence; KL-M5-T-002 ist dort kein direkter M5a-Blocker.

Aenderung:

- `status` bleibt `open`.
- `category` auf `M5b implementation blocker` gesetzt.
- `blocks_gate` von `m5_slice_start_gate` auf `m5b_implementation_gate` geaendert.
- `target_phase` auf `M5b Drift / M5b Slice Implementation` gesetzt.
- `evidence_report` auf `reports/current/m5b_start_gate.json` gesetzt.
- `next_action` konkretisiert: M5a nicht durch KL-M5-T-002 blockieren; fuer M5b die Retrieval-Baseline release-grade machen, Cleanup-Dry-Run mit `blocked_count=0` erzeugen, M5b-Truth-Block PASS/GO nachweisen und danach `m5b_implementation_gate` neu bewerten.

Gate-Auswirkung:

- M5a: keine zusaetzliche Blockade durch KL-M5-T-002. M5a bleibt nur durch die technischen M5a-Gates und Report-Integritaet blockiert.
- M5b PREPARED: bleibt durch M5a Parent-Gate und offene High-Severity-Limitations blockiert, bis die Release-Entscheidung neu bewertet wird.
- M5b Implementierung: KL-M5-T-002 blockiert weiter das separate `m5b_implementation_gate`.

## 2026-06-09 - KL-GOV-001

Status: auf `deferred` gesetzt, Gate-Zuordnung beibehalten und Wirkung eingegrenzt.

Pruefung:

- Beschreibung gelesen: mutierende Admin-Aktionen ohne Runbook und Gate-Freigabe bleiben gesperrt.
- Gate-Hierarchie geprueft: `docs/gate_hierarchy.json` enthaelt KL-GOV-001 nicht als M5a-Child und `operational_governance_gate` ist kein M5a-Pflichtkind.
- Governance-Boundary geprueft: `docs/governance-boundary.json` klassifiziert `governance_truth` als Operational-Governance-Thema; es blockiert M4 nicht und M5-Start nicht vor bestandenem M5-Start.
- Evidence geprueft: `docs/m4d-admin-diagnostics.md` definiert M4d als read-only; mutierende Adminaktionen sind spaetere Ausbaustufen.
- M5b-Evidence geprueft: `reports/current/m5b_start_gate.json` blockiert M5b wegen M5a Parent-Gate und M5b-Implementierungsbedingungen, nicht wegen mutierender Admin-Governance.

Aenderung:

- `status` von `open` auf `deferred` gesetzt.
- `blocks_gate` bleibt `["operational_governance_gate"]`, weil dies das tatsaechliche Ziel-Gate fuer spaetere mutierende Adminaktionen ist.
- `target_phase` auf `Post-M5 mutating admin actions` gesetzt.
- `next_action` konkretisiert: keine M5a-/M5b-Freigabe durch KL-GOV-001 blockieren; erst bei geplanter Web-Admin-Mutation Runbook, Auth-/Redaction-/Audit-Tests und `operational_governance_gate` PASS/GO erzeugen.

Governance-Gate-Mapping:

| Bereich | Blockiert durch KL-GOV-001? | Begruendung |
|---|---:|---|
| M5a Parent-Gate | nein | `operational_governance_gate` ist kein M5a-Child in `docs/gate_hierarchy.json`. |
| M5b DRAFT/PREPARED | nein | M5b bleibt durch M5a Parent-Gate und M5b-spezifische Preconditions gesteuert; mutierende Adminaktionen sind nicht Voraussetzung fuer Planung oder PREPARED. |
| M5b Implementierung read-only Drift | nein | M5b Drift ist read-only; die Limitation betrifft nur Mutationen wie Repair, Cleanup-Loeschen oder forced Reindex. |
| Spaetere mutierende Adminaktionen | ja | Vor Web-Admin-Mutationen ist `operational_governance_gate` mit Runbook, Auth-/Redaction-/Audit-Tests und PASS/GO erforderlich. |
