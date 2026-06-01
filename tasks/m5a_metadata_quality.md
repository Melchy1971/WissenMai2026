# Tasks: M5a Metadata Quality Detector Slice

Statusquelle: `reports/current/m5a_duplicate_detector_gate.json` (GO — Voraussetzung erfüllt)
Slice-Gate: `reports/current/m5a_metadata_detector_gate.json` (noch nicht vorhanden — Slice nicht gestartet)

Implementierung erst nach Slice-Start-Gate. Dieser Task-Plan ist Planungsartefakt.

---

## Task-Liste

### T-01 — MetadataQualityDetector implementieren

**Datei:** `backend/app/services/metadata_quality_detector.py`

Regeln:
- MQ-1: `documents.title` leer oder Whitespace → `MISSING_METADATA`, `error`
- MQ-2: `DocumentVersion.metadata_["tags"]` fehlt oder leer → `MISSING_METADATA`, `warning`
- MQ-3: `DocumentVersion.metadata_["category"]` fehlt oder leer → `MISSING_METADATA`, `warning`
- MQ-4: `DocumentVersion.metadata_["doc_type"]` fehlt oder leer → `MISSING_METADATA`, `warning`
- MQ-5: `DocumentVersion.metadata_["summary"]` fehlt oder leer → `MISSING_METADATA`, `info`

Contracts: read-only, workspace-scoped, nur aktive Dokumente, DB-agnostische Queries.

Rückgabe: `list[dict]` — partial finding kwargs, kompatibel mit `DataQualityRunner`.

Abhängigkeiten: `app/models/documents.py` (Document, DocumentVersion), `app/models/data_quality.py` (FINDING_TYPE_VALUES)

Kein Schema-Change erforderlich.

---

### T-02 — Unit-Tests MetadataQualityDetector

**Datei:** `backend/tests/test_metadata_quality_detector.py`

Coverage:
- Leerer Titel → Finding MQ-1 (error)
- Vollständige Metadaten → 0 Findings (kein False Positive)
- Jede fehlende Metadata-Regel einzeln (MQ-2 bis MQ-5)
- Archived/deleted Dokument mit leerem Titel → 0 Findings
- Workspace Isolation
- Keine Dokumentmutation (snapshot before/after)
- Finding-Shape vollständig (alle Pflichtkeys, kein `run_id`)
- Severity je Regel korrekt

---

### T-03 — DataQualityRunner integrieren

**Datei:** `backend/app/services/data_quality_runner.py`

`MetadataQualityDetector` in `_execute_detectors()` nach `DuplicateDetector` eintragen.

---

### T-04 — PostgreSQL Truth-Tests

**Datei:** `backend/tests/postgres_truth/test_m5a_metadata_quality_truth.py`

Marker: `postgres_truth`, `m5_truth`

Tests:
- Detector läuft auf leerem Workspace → 0 Findings
- Dokument mit leerem Titel → Finding MQ-1, type=MISSING_METADATA, sev=error
- Dokument mit vollständigen Metadaten → 0 Findings für MQ-2..5
- DB-Constraint kompatibel: alle Findings via `DataQualityFinding` insertierbar ohne Constraint-Fehler
- Keine Dokumentmutation

---

### T-05 — Gate-Script generieren

**Datei:** `scripts/generate_m5a_metadata_detector_gate.py`

Prüft 11 Kriterien (siehe `docs/m5a-metadata-quality-slice.md`).
Output: `reports/current/m5a_metadata_detector_gate.json`
GO bei Score >= 90.

---

### T-06 — Dokumentation aktualisieren

Nach Gate-PASS:
- `docs/data-quality.md` — Metadata Quality Detector Scope ergänzen
- `docs/status.md` — Slice-Stand aktualisieren
- `Entwicklung.md` — aktiven Slice aktualisieren
- `docs/generated/status_section.md` + `masterplan_status.json` neu generieren
- `documentation_truth_lint` auf PASS prüfen

---

## Sequenz

```
T-01 → T-02 → T-03 → T-04 → T-05 → Gate-Lauf → T-06
```

T-02 und T-04 können parallel nach T-01 laufen.
T-05 erst nach grünem T-04.

---

## Gate-Kriterien (Kurzform)

| ID | Kriterium | Schwelle |
|---|---|---|
| C1 | MQ-1 leerer Titel erkannt | 1 Finding, error |
| C2 | MQ-2 fehlende Tags erkannt | 1 Finding, warning |
| C3 | MQ-3 fehlende Kategorie erkannt | 1 Finding, warning |
| C4 | MQ-4 fehlender Dokumenttyp erkannt | 1 Finding, warning |
| C5 | MQ-5 fehlende Zusammenfassung erkannt | 1 Finding, info |
| C6 | Kein False Positive bei vollständigen Metadaten | 0 Findings |
| C7 | Nur aktive Dokumente geprüft | 0 Findings auf archived/deleted |
| C8 | Workspace Isolation | Kein Cross-WS-Leak |
| C9 | Keine Dokumentmutation | Snapshot identisch |
| C10 | Finding-Shape Runner-kompatibel | Alle Pflichtkeys, kein run_id |
| C11 | Runner integriert MetadataQualityDetector | completed, >= 1 Finding |

Score >= 90 (min. 10/11) = GO.

---

## Offene Fragen vor Implementierungsstart

1. **Welche Metadata-Keys sind Pflicht?** `tags`, `category`, `doc_type`, `summary` sind im Parser-Protokoll referenziert (`AIProvider.suggest_tags`), aber nicht durch DB-Constraints erzwungen. Ist die Prüfung auf alle vier Schlüssel gewünscht oder nur auf eine Teilmenge?

2. **NULL vs. leeres JSON-Objekt:** Dokumente ohne `current_version_id` (Import noch nicht abgeschlossen) — MQ-2..5 überspringen oder als Fehler werten?

3. **Limit je Regel:** 500 Findings pro Regel pro Run angemessen, oder workspace-abhängige Konfiguration?
