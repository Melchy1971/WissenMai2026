# M5 Data Quality

Stand: 2026-05-29

## Status

- Phase: Vorbereitung abgeschlossen
- Implementierung: nicht gestartet
- Freigabestatus: kein produktiver Betrieb bis PostgreSQL-Truth-Block `data_quality` gruen
- Massgeblich: `reports/current/masterplan_status.json`

---

## Scope

- Invariantenprüfung für Dokumente, Versionen, Chunks, Citations
- Severity-Modell: Fehler vs. Warnung
- Prüfstrategie: read-only, keine automatische Reparatur
- Truth-Test-Anker für spätere PostgreSQL-Nachweise

---

## Regelkatalog

### Harte Fehler (blockieren Gate)

| Regel-ID | Prüfobjekt | Bedingung | Fehlerklasse |
|---|---|---|---|
| DQ-001 | Dokument | kein `current_version_id` verknüpft | `document_without_version` |
| DQ-002 | Version | keine Chunks und `import_status != failed` | `version_without_chunks` |
| DQ-003 | Chunk | `source_anchor` fehlt oder leer | `chunk_missing_anchor` |
| DQ-004 | Chunk | `document_version_id` referenziert keine existierende Version | `orphaned_chunk` |
| DQ-005 | Version | `document_id` referenziert kein existierendes Dokument | `orphaned_version` |
| DQ-006 | Dokument | `content_hash` mehrfach in derselben `workspace_id` | `duplicate_content_hash` |
| DQ-007 | Citation | `chunk_id` fehlt und `source_status = active` | `dangling_citation_active` |
| DQ-008 | Index | Index-Eintrag ohne korrespondierenden DB-Chunk | `stale_index_entry` |

### Warnungen (reportpflichtig, nicht gate-blockierend)

| Regel-ID | Prüfobjekt | Bedingung | Klasse |
|---|---|---|---|
| DQ-W-001 | Citation | `chunk_id` fehlt und `source_status != active` | `dangling_citation_archived` |
| DQ-W-002 | Version | `normalized_markdown` leer und `import_status = completed` | `empty_normalized_content` |
| DQ-W-003 | Dokument | `lifecycle_status = active` aber kein Index-Eintrag | `missing_index_entry` |
| DQ-W-004 | Job | `background_job` in `running` älter als Timeout | `stale_running_job` |

---

## Severity-Modell

| Severity | Wirkung |
|---|---|
| `error` | Gate-blockierend; Report-Status wird `failed` |
| `warning` | Reportpflichtig; Gate nicht blockiert; `watch`-Status |

---

## Prüfstrategie

Alle Prüfungen sind read-only. Keine automatische Reparatur.
Prüfreihenfolge: strukturelle Invarianten → Duplikatschutz → Citation-Integrität → Index-Konsistenz → Content-Validierung → Job-State.

Jede Prüfung läuft workspace-scoped. Globale Reports aggregieren Counts ohne Dokumenttexte oder Dateipfade.

---

## Report-Format

```json
{
  "report_type": "data_quality",
  "generated_at": "<iso8601>",
  "workspace_id": "<uuid>",
  "status": "passed | failed | watch",
  "error_count": 0,
  "warning_count": 0,
  "findings": [
    { "rule_id": "DQ-001", "severity": "error", "entity_type": "document", "count": 0, "sample_ids": [] }
  ]
}
```

`status = failed` wenn `error_count > 0`. `status = watch` wenn nur Warnungen. `status = passed` wenn beide Counts 0.

---

## Gate-Bezug

Data-Quality-Gate gilt als PASS, wenn alle Fehlerregeln `count = 0` und ein aktueller PostgreSQL-Truth-Report den Block `data_quality` grün belegt.

---

## Nicht-Scope

- Keine automatische Datenreparatur
- Keine produktive Cleanup-Freigabe
- Kein betrieblicher Dienst ohne Truth-Nachweis

---

## Implementierungsanker

- CLI: `python -m app.cli m5 data-quality-check --workspace <id>`
- Report-Ziel: `reports/current/m5_data_quality_report.json`
- Truth-Test-Block: `data_quality`
