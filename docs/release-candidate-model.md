# Release Candidate Modell

Dieses Modell definiert die Zwischenstufen zwischen Entwicklung und abgeschlossen. Es ist verbindlich fuer Masterplan-Statusaussagen, Gate-Freigaben und Release-Kommunikation. Quelle: `reports/current/masterplan_status.json`.

Maschinenlesbare Quelle: `docs/release-candidate-model.json`.

## Status

| Status | Bedeutung | Abschlussfaehig |
|---|---|---|
| `draft` | Scope, Akzeptanzkriterien und Gate-Zuordnung sind beschrieben. | nein |
| `implemented` | Code, Migrationen oder Dokumentation wurden umgesetzt. | nein |
| `tested` | Unit-, Contract- oder Integrationstests wurden ausgefuehrt. | nein |
| `truth_validated` | Passender Truth-Split-Report wurde erzeugt und Marker-Taxonomie ist gruen. | nein |
| `gate_passed` | Passendes Gate ist maschinenlesbar `PASS`. | nein |
| `released` | Gate-Report und Dokumentationsaudit liegen vor. | ja |

## Statusregeln

- `implemented` ohne `truth_validated` zaehlt nicht als abgeschlossen.
- `gate_passed` braucht einen maschinenlesbaren Gate-Report mit Status `PASS`.
- `released` braucht einen Dokumentationsaudit, der Masterplan, Doku und Reports abgleicht.
- Ein M4-RC darf bei M4-Bewertung keine M5- oder Governance-Abhaengigkeiten haben.
- Nur `released` ist ein abgeschlossener Status. `gate_passed` ist freigabefaehig, aber noch nicht final dokumentiert.

## Gate- und Reportbindung

| RC-Scope | Gate | Reports | Verboten bei Bewertung |
|---|---|---|---|
| M3a | `m3a_gate` | `m3a_truth_report.json`, `frontend_truth_report.json` | M4/M5/Governance |
| M4a | `m4a_gate` | `m4a_auth_truth_report.json` | M5/Governance |
| M4b | `m4b_gate` | `m4b_upload_queue_truth_report.json` | M5/Governance |
| M4c | `m4c_gate` | `m4c_lifecycle_retrieval_truth_report.json` | M5/Governance |
| M4e | `m4e_gate` | `m4e_backup_restore_truth_report.json` | M5/Governance |
| M4 Gesamt | `m4_overall_gate` | M3a + M4a/b/c/e Split-Reports | M5/Governance |
| M5 Start | `m5_start_gate` | `gate_hierarchy_result.json` | keine |
| Operational Governance | `operational_governance_gate` | `governance_truth_report.json`, `gate_hierarchy_result.json` | keine |

## Masterplan-Abbildung

| RC-Status | Masterplan-Abbildung |
|---|---|
| `draft` | Backlog-, Partial- oder Missing-Eintrag mit Akzeptanzkriterien und Gate-Zuordnung. |
| `implemented` | Darf in `Implemented` stehen, bleibt aber ohne Truth-Nachweis nicht abgeschlossen. |
| `tested` | Testnachweis vorhanden; weiterhin kein Abschlussclaim. |
| `truth_validated` | Truth-Split-Report existiert und `truth_marker_taxonomy` ist `PASS`. |
| `gate_passed` | `gate_hierarchy_result.json` enthaelt `PASS` fuer das betroffene Gate. |
| `released` | Masterplan, Doku und maschinenlesbare Reports wurden im Dokumentationsaudit abgeglichen. |

## Bewertungsregel fuer M4

M4 wird ausschliesslich mit M3a und M4a/b/c/e bewertet. `m5_truth`, `governance_truth`, Queue-Aging, Entropy, Cleanup Governance und Longevity duerfen M4 nicht blockieren. Diese Nachweise werden erst fuer M5 Start beziehungsweise Operational Governance herangezogen.
