# Governance Boundary M3a/M4/M5

Stand: 2026-05-20

## Ziel

Spaetere Anforderungen duerfen fruehere Gates nicht blockieren. Gate-Status wird aus maschinenlesbaren Artefakten berechnet; Dokumentation darf ihn nur referenzieren.

## Boundary-Regeln

| ID | Regel | Wirkung |
|---|---|---|
| GB-001 | M3a prueft GUI Foundation. | M3a wird nur durch `m3a_truth` und `frontend_truth` blockiert. |
| GB-002 | M4 prueft Produktisierung und Stabilisierung. | M4 wird durch M4-Truth-Marker und das M3a-Abhaengigkeitsgate blockiert. |
| GB-003 | M5 prueft Langzeitbetrieb und Governance. | M5 startet erst nach bestandenem M4-Gesamtgate. |
| GB-004 | M5-Tests duerfen M4 nicht blockieren. | `m5_truth` und `governance_truth` sind keine M4-Blocker. |
| GB-005 | M4-Tests duerfen M5 blockieren. | Rote M4-Gates blockieren `m5_start_gate`. |
| GB-006 | Frontend-GUI-Tests duerfen M4 nur blockieren, wenn M4 vom GUI-Slice abhaengig ist. | `frontend_truth` blockiert M4 nur bei `gui_dependency=true` im M4-Gate- oder RC-Artefakt. |

## Gate-Mapping

| Gate | Phase | Blockiert | Darf nicht blockiert werden durch |
|---|---|---|---|
| `m3a_gate` | M3a | M3a; spaeter M4 nur als bestandene Dependency | `m4_truth`, `m5_truth`, `governance_truth` |
| `m4_overall_gate` | M4 | M4 und `m5_start_gate` | `m5_truth`, `governance_truth` |
| `m5_start_gate` | M5 | M5 und Operational Governance | - |
| `operational_governance_gate` | Governance | Operational Governance | `governance_truth` vor bestandenem M5 Start |

## Testklassifikation

| Marker | Primaere Phase | Primaeres Gate | Blockiert | Blockiert nicht |
|---|---|---|---|---|
| `frontend_truth` | M3a | `m3a_gate` | `m3a_gate`; M4 nur bei `gui_dependency=true` | M4 ohne GUI-Abhaengigkeit, M5 |
| `m3a_truth` | M3a | `m3a_gate` | `m3a_gate` | M4 ausser als bestandene M3a-Dependency |
| `m4_truth` | M4 | `m4_overall_gate` | `m4_overall_gate`, `m5_start_gate` | - |
| `m4a_auth_truth` | M4 | `m4a_gate` | `m4a_gate`, `m4_overall_gate`, `m5_start_gate` | - |
| `m4b_upload_queue_truth` | M4 | `m4b_gate` | `m4b_gate`, `m4_overall_gate`, `m5_start_gate` | - |
| `m4c_lifecycle_retrieval_truth` | M4 | `m4c_gate` | `m4c_gate`, `m4_overall_gate`, `m5_start_gate` | - |
| `m4e_backup_restore_truth` | M4 | `m4e_gate` | `m4e_gate`, `m4_overall_gate`, `m5_start_gate` | - |
| `m5_truth` | M5 | `m5_start_gate` | `m5_start_gate` | `m4_overall_gate` |
| `governance_truth` | Governance | `operational_governance_gate` | Operational Governance nach M5 Start | M4, M5 vor M5 Start |
| `chaos_truth` | Cross-cutting | deklarierter Gate-Marker | nur Gate des begleitenden Gate-Markers | alle anderen Gates |
| `slow_truth` | Cross-cutting | deklarierter Gate-Marker | nur Gate des begleitenden Gate-Markers | alle anderen Gates |

## Maschinenlesbare Quelle

Die verbindliche Boundary steht in `docs/governance-boundary.json`. Gate-Validatoren und Status-Engines duerfen M4 nicht mit `m5_truth` oder `governance_truth` blockieren. M5 darf durch M4 blockiert werden, bis `m4_overall_gate` PASS ist.
