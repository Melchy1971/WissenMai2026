
# Data Quality Architektur (M5)

Alle Aussagen, Status und Gates werden ausschließlich aus maschinenlesbaren Reports abgeleitet:

- Architektur: Siehe data_quality_report_generator.py, quality_score.py, models/data_quality.py
- Findings-Modell: Siehe DataQualityFinding (models/data_quality.py)
- Score: Siehe quality_score.py, data_quality_report.json
- APIs: Siehe OpenAPI, API-Implementierung (data-quality Endpunkte)
- Dashboard: Siehe React-Komponenten, HeroUI, Telekom CI
- M5a Gate: Siehe reports/current/m5a_data_quality_gate.json (Go/No-Go, Score)
- M5a Start-Gate: Siehe reports/current/m5a_start_gate.json.
- Duplicate Detector Slice: Siehe reports/current/m5a_duplicate_detector_gate.json.

## M5a Start-Gate Einordnung

Laut `reports/current/m5a_start_gate.json` bleibt M5a auf Vorbereitung beschraenkt, solange die dortige Entscheidung nicht `GO` ist. Fehlende oder blockierende Artefakte werden ausschliesslich in diesem Report und im aktuellen Dokumentationsaudit `reports/current/documentation_truth_lint.json` bewertet.

Wenn das Start-Gate spaeter `GO` meldet, ist der erste Implementierungsslice der Duplicate Detector. Dieser Slice darf nur read-only Findings erzeugen. Cleanup-, Merge- oder Repair-Actions bleiben ausser Scope und brauchen separate Governance.

## Report-Format

```json
{
  "report_schema_version": "1.0.0",
  "report_name": "data_quality_report",
  "timestamp": "2026-05-29T12:00:00Z",
  "total_documents": 1000,
  "duplicates": 5,
  "metadata_issues": 2,
  "lifecycle_issues": 1,
  "source_status_issues": 1,
  "orphan_objects": 3,
  "quality_score": 97,
  "findings": [
    { "id": "DQ-001", "type": "DUPLICATE_DOCUMENT", "severity": "high", "remediation": "Prüfen und bereinigen." }
  ]
}
```

## Gate-Bezug

Data-Quality-Gate (M5a) gilt als PASS, wenn alle Pflichtkomponenten vorhanden und der Score >= 90 ist (siehe m5a_data_quality_gate.json).

---

## Implementierungsanker

- CLI: `python -m app.cli m5 data-quality-check --workspace <id>`
- Geplantes Report-Artefakt: `m5_data_quality_report.json`
- Truth-Test-Block: `data_quality`
