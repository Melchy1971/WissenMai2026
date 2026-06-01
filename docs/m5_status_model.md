# M5 Statusmodell

Quelle fuer die maschinelle Bewertung ist `reports/current/masterplan_status.json`.
Dieses Dokument definiert die erlaubten M5-Zustaende und die Gate-Regeln fuer die Status Engine v3.

## Statuswerte

| Status | Bedeutung |
|---|---|
| `NOT_STARTED` | M5 ist noch nicht startfaehig, weil M4e Operations nicht als aktuelles `PASS`/`GO`-Artefakt vorliegt. |
| `PREPARATION_ALLOWED` | M4e Operations ist `PASS`/`GO`; M5-Vorbereitung darf starten, aber kein Slice darf implementiert werden. |
| `PREPARATION_DONE` | Ein aktuelles Gate-Artefakt markiert den Done-Zustand der M5-Vorbereitung. |
| `SLICE_START_ALLOWED` | Mindestens ein konkreter M5-Slice hat sein eigenes Start-Gate mit `GO`. |
| `SLICE_IMPLEMENTING` | Ein gestarteter Slice befindet sich in aktiver Umsetzung. |
| `SLICE_GATE_PASSED` | Das Gate eines konkreten Slice liefert ein maschinenlesbares Slice-Gate-Ergebnis. |
| `M5_IMPLEMENTATION_ALLOWED` | Alle fuer die globale M5-Implementierungsfreigabe erforderlichen Slice-Gates sind erfuellt. |
| `BLOCKED` | Invalid JSON, Report-Widerspruch oder harter Gate-Blocker verhindert eine belastbare M5-Statusaussage. |

## Regeln

- M5-Vorbereitung darf erst nach M4e Operations `PASS`/`GO` starten. Quelle: `reports/current/m4e_operations_release_report.json`.
- M4e Operations `PASS`/`GO` erlaubt keine pauschale M5-Implementierung.
- Jeder M5-Slice braucht ein eigenes Start-Gate unter `reports/current/`.
- M5a Data Quality braucht `reports/current/m5a_start_gate.json` mit Entscheidung `GO`.
- Ein invalides JSON-Artefakt im M5-Gate-Kontext setzt das Statusmodell auf `BLOCKED`.
- Widersprueche zwischen aktuellen Reports setzen das Statusmodell auf `BLOCKED`.
- Offene Known Limitations fuer `m5_slice_start_gate` oder `m5_truth_gate` verhindern Slice-Start.

## M5a Data Quality

M5a Data Quality ist der erste explizit modellierte Slice.

Pflichtartefakte:

- `reports/current/m5a_start_gate.json`
- `reports/current/m5a_data_quality_gate.json`

Startregel:

- `m5a_start_gate.json` muss `GO` liefern.
- `m5a_data_quality_gate.json` darf nicht als bestanden bewertet werden, wenn `m5a_start_gate.json` fehlt oder nicht `GO` ist.

## Konfliktregeln

Die Status Engine blockiert bei diesen Widerspruechen:

- `m4e_operations_release_report.json` und `m4e_operations_release_gate.json` widersprechen sich.
- `m5_gate_assessment.json` erlaubt M5-Vorbereitung, obwohl M4e Operations nicht `PASS`/`GO` ist.
- `m5_gate_assessment.json` erlaubt M5-Implementierung, obwohl kein Slice-Start-Gate `GO` ist.
- `m5_gate_assessment.json` erlaubt Slice-Start, obwohl Slice-Pflichtbedingungen fehlen.
- `m5a_data_quality_gate.json` meldet `status = PASS`, aber `m5a_start_gate.json` ist nicht `GO`.

## Aktuelle Engine-Felder

`reports/current/masterplan_status.json` schreibt die M5-Bewertung in:

- `m5.status`
- `m5.preparation_allowed`
- `m5.slice_start_allowed`
- `m5.implementation_allowed`
- `m5.implementation_gate_dependency`
- `input_integrity_issues`
- `report_contradictions`
