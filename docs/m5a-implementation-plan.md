# M5a Implementation Plan

Statusquelle: `reports/current/m5a_start_gate.json`

## Gate-Einordnung

M5a bleibt vorbereitet, wenn `reports/current/m5a_start_gate.json` keine `GO`-Entscheidung meldet. In diesem Zustand ist nur Planung erlaubt; Implementierungsslices duerfen nicht als gestartet oder freigegeben dokumentiert werden.

Wenn das Start-Gate spaeter `GO` meldet, ist der erste Slice der Duplicate Detector. Der Slice erzeugt ausschliesslich read-only Findings. Cleanup-, Merge- und Repair-Actions bleiben ausser Scope, bis eine separate Governance-Freigabe vorliegt.

## Phasen

| Phase | Artefakte | Tests | Gate-Artefakt | Rollback |
|---|---|---|---|---|
| Datenmodell | `DataQualityRun`, `DataQualityFinding`, `DataQualityMetric`, `DataQualitySnapshot` | Modell- und PostgreSQL-Truth-Tests | `reports/current/m5a_data_quality_gate.json` | Migration zuruecknehmen oder Tabellen ungenutzt lassen |
| Alembic Migration | Data-Quality-Migration | Migrations-Compile und DB-Truth-Lauf | `reports/current/m5a_data_quality_gate.json` | Alembic Downgrade nach Review |
| Duplicate Detector | Duplicate-Detector-Service | Detector-Tests mit Workspace-Isolation | `reports/current/m5a_duplicate_detector_gate.json` | Slice deaktivieren, Findings unveraendert lassen |
| Metadata Quality Detector | Metadatenregeln | Unit- und Truth-Tests | `m5a_metadata_detector_gate.json` | Detector deaktivieren |
| Lifecycle Integrity Detector | Lifecycle-Regeln | Truth-Tests gegen echte DB | `m5a_lifecycle_detector_gate.json` | Detector deaktivieren |
| Source Status Integrity Detector | Source-Status-Regeln | Truth-Tests | `m5a_source_status_detector_gate.json` | Detector deaktivieren |
| Report Generator | JSON/Markdown-Report | Schema-Validierung | `reports/current/m5a_data_quality_gate.json` | Report nicht als Gate-Input verwenden |
| Quality Score | Score-Berechnung | Score-Tests mit Grenzfaellen | `reports/current/m5a_data_quality_gate.json` | Score als unknown behandeln |
| Read-only API | Data-Quality-Endpunkte | API-Tests | `m5a_read_only_api_gate.json` | Endpunkte deaktivieren |
| Dashboard | Read-only Ansicht | Frontend-Tests | `m5a_dashboard_gate.json` | Ansicht aus Navigation entfernen |
| M5a Gate | Gesamtgate | Report-Validator | `reports/current/m5a_data_quality_gate.json` | Gate auf BLOCKED setzen |

## Risiken

- Start ohne `GO` in `reports/current/m5a_start_gate.json` wuerde dem Statusmodell widersprechen.
- Detectoren duerfen keine Dokumente, Versionen, Chunks oder Quellen mutieren.
- Findings bleiben read-only, bis Cleanup-Governance separat freigegeben ist.
