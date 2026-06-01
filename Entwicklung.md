# Entwicklung

Statusquelle: `reports/current/m5a_start_gate.json`

M5a folgt dem maschinellen Start-Gate. Wenn `reports/current/m5a_start_gate.json` keine `GO`-Entscheidung meldet, bleibt M5a vorbereitet und es werden fehlende oder blockierende Artefakte ueber die Reports unter `reports/current/` bewertet.

Wenn das Start-Gate spaeter `GO` meldet, startet M5a mit dem Duplicate Detector als erstem Slice. Der Slice darf nur read-only Findings erzeugen. Cleanup-, Merge- und Repair-Actions bleiben ohne separate Governance ausser Scope.
