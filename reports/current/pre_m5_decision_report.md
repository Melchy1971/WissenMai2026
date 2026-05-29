# Pre-M5 Decision Report

Stand: 2026-05-29
Report: `reports/current/pre_m5_decision_report.json`

> Alle Entscheidungen werden ausschliesslich aus maschinenlesbaren Reports abgeleitet.
> Manuelle Statusaussagen in diesem Dokument sind nicht autoritativ.

---

## Eingaben

| Report | Status | Entscheidung | Zeitstempel |
|---|---|---|---|
| `masterplan_status.json` | PASS | GO | 2026-05-29T08:57 |
| `m3a_release_candidate.json` | PASS | GO | 2026-05-29T08:51 |
| `m4_backend_release_candidate.json` | PASS (102/102) | GO | 2026-05-29T06:38 |
| `m4e_operations_release_gate.json` | PASS (9/9) | GO | 2026-05-29T09:02 |

---

## 1. M5 Vorbereitung erlaubt?

**GO**

Basis:
- M3a RC GO — `reports/current/m3a_release_candidate.json`
- M4 Backend RC GO (102/102) — `reports/current/m4_backend_release_candidate.json`
- M5 Preparation Gate PASS — `reports/current/masterplan_status.json`

Preparation Package vollständig:

| Dokument | Status |
|---|---|
| `docs/m5-preparation.md` | finalisiert |
| `docs/data-quality.md` | finalisiert |
| `docs/drift.md` | finalisiert |
| `docs/cleanup.md` | finalisiert |
| `docs/health-score.md` | finalisiert |
| `docs/m5-retrieval-quality-baseline.md` | finalisiert |

---

## 2. M5 Implementierung erlaubt?

**GO**

Gate-Regel: *M5 Implementierung bleibt NO-GO, solange `m4e_operations_release_gate` nicht PASS ist.*

Gate-Regel erfüllt: `m4e_operations_release_gate` = PASS/GO (9/9 Regeln).

Basis:
- `m4e_operations_release_gate.json` PASS/GO — `reports/current/m4e_operations_release_gate.json`
- `masterplan_status.json`: M5 `implementation_decision` = GO

Implementierung ist gate-freigegeben. Jeder einzelne Slice bleibt NO-GO bis Truth-Block, Baseline und Dry-Run vorliegen.

---

## 3. Welche Blocker bleiben?

2 aktive Slice-Level-Blocker. Diese verhindern nicht die Implementierungsfreigabe, aber jede Slice-Aktivierung im Produktivbetrieb.

### KL-M5-T-001 — M5 Truth Failures

15 M5 Entropy-/Drift-Truth-Failures in der aktuellen PostgreSQL-Truth-Suite. Kein M5-Slice darf produktiv gehen, bevor sein Truth-Block grün ist.

- Blocks Gate: `m5_truth_gate`
- Workaround: M5-Slices einzeln implementieren; Truth-Block je Slice grün nachweisen
- Evidence: `reports/current/m4_truth_report.json`

### KL-M5-T-002 — Fehlende Slice-Start-Artefakte

Vor Start jedes M5-Slices müssen drei Pflicht-Artefakte vorliegen: (1) Retrieval-Baseline, (2) Cleanup Dry-Run mit `blocked_count = 0`, (3) Truth-Block grün. Keines dieser Artefakte existiert.

- Blocks Gate: `m5_slice_start_gate`
- Workaround: Artefakte vor jedem Slice-Start sequenziell erstellen
- Evidence: `docs/m5-preparation.md`

---

## 4. Welche Artefakte fehlen für Implementierung?

6 Pflicht-Artefakte fehlen. Ausführungsreihenfolge ist verbindlich: Truth-Block grün → Baseline setzen → Dry-Run → Slice aktivieren.

| ID | Artefakt | Befehl | Report-Ziel | Pflicht vor |
|---|---|---|---|---|
| PRE-ART-01 | Retrieval-Baseline | `python -m app.cli m5 retrieval-benchmark --set-baseline` | `m5_retrieval_baseline.json` | erstem Benchmark-Lauf |
| PRE-ART-02 | Cleanup Dry-Run (`blocked_count = 0`) | `python -m app.cli m5 cleanup-dry-run --workspace <id>` | `m5_cleanup_dry_run_report.json` | jedem Cleanup-Lauf |
| PRE-ART-03 | Truth-Block `data_quality` grün | `pytest --pg tests/truth/m5/ -k data_quality` | `m5_data_quality_truth.json` | Aktivierung Data-Quality-Slice |
| PRE-ART-04 | Truth-Block `drift_detection` grün | `pytest --pg tests/truth/m5/ -k drift_detection` | `m5_drift_truth.json` | Aktivierung Drift-Detection-Slice |
| PRE-ART-05 | Truth-Block `cleanup_dry_run` grün | `pytest --pg tests/truth/m5/ -k cleanup_dry_run` | `m5_cleanup_truth.json` | Aktivierung Cleanup-Slice |
| PRE-ART-06 | Truth-Block `health_score` grün | `pytest --pg tests/truth/m5/ -k health_score` | `m5_health_score_truth.json` | Aktivierung Health-Score-Slice |

---

## Zusammenfassung

| Frage | Antwort |
|---|---|
| M5 Vorbereitung erlaubt? | **GO** |
| M5 Implementierung erlaubt? | **GO** |
| Gate-Regel erfüllt? | **ja** (`m4e_operations_release_gate` = PASS) |
| Aktive Slice-Blocker | 2 (`KL-M5-T-001`, `KL-M5-T-002`) |
| Fehlende Vorab-Artefakte | 6 |
| Preparation Package vollständig? | **ja** |
