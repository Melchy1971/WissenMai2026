
# Data Quality Architektur (M5)

Alle Aussagen, Status und Gates werden ausschließlich aus maschinenlesbaren Reports abgeleitet:

- Architektur: Siehe data_quality_report_generator.py, quality_score.py, models/data_quality.py
- Findings-Modell: Siehe DataQualityFinding (models/data_quality.py)
- Score: Siehe quality_score.py, data_quality_report.json
- APIs: Siehe OpenAPI, API-Implementierung (data-quality Endpunkte)
- Dashboard: Siehe React-Komponenten, HeroUI, Telekom CI
- M5a Gate: Siehe reports/current/m5a_data_quality_gate.json (Go/No-Go, Score)

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

# documentation_truth_lint PASS

## Implementierungsanker

- CLI: `python -m app.cli m5 data-quality-check --workspace <id>`
- Report-Ziel: `reports/current/m5_data_quality_report.json`
- Truth-Test-Block: `data_quality`
