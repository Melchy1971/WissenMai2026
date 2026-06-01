# M5a Metadata Quality Detector — Slice-Planung

Statusquelle: `reports/current/m5a_duplicate_detector_gate.json` (GO, Score 100/100)

Voraussetzung: Duplicate Detector Gate PASS. Erfüllt.

Dieser Slice ist planning-only. Implementierung beginnt erst nach eigenem Slice-Start-Gate.

---

## Scope

Erkennt Dokumente mit fehlenden oder unvollstaendigen Pflichtmetadaten innerhalb eines Workspace.
Nur aktive Dokumente (`lifecycle_status = active`). Read-only. Keine Mutations.

### Erkennungsregeln (5 Finding-Typen)

| ID | Regel | Feld | Finding-Typ | Severity |
|---|---|---|---|---|
| MQ-1 | Titel leer oder nur Whitespace | `documents.title` | `MISSING_METADATA` | `error` |
| MQ-2 | Tags fehlen oder leeres Array | `DocumentVersion.metadata_["tags"]` | `MISSING_METADATA` | `warning` |
| MQ-3 | Kategorie fehlt oder leer | `DocumentVersion.metadata_["category"]` | `MISSING_METADATA` | `warning` |
| MQ-4 | Dokumenttyp fehlt oder leer | `DocumentVersion.metadata_["doc_type"]` | `MISSING_METADATA` | `warning` |
| MQ-5 | Zusammenfassung fehlt oder leer | `DocumentVersion.metadata_["summary"]` | `MISSING_METADATA` | `info` |

Finding-Typ für alle: `MISSING_METADATA` (bereits in `FINDING_TYPE_VALUES` definiert).

### Scope-Grenzen

Nicht in diesem Slice:

- Automatische Befüllung fehlender Metadaten
- KI-basierte Tag- oder Kategorievorschläge (`AIProvider.suggest_tags` bleibt M5b-Scope)
- Mutations an Dokumenten, Versionen oder Chunks
- Validierung von Metadatenwerten (nur Präsenz wird geprüft)

---

## Datenmodell-Abhängigkeiten

Kein Schema-Change erforderlich. Alle benötigten Tabellen und Felder existieren:

- `documents.title` — String(500), NOT NULL — MQ-1 prüft `trim(title) == ""`
- `document_versions.metadata_` — JSON NOT NULL — MQ-2 bis MQ-5 lesen `metadata_["tags"]` etc.

Die Metadata-Keys `tags`, `category`, `doc_type`, `summary` sind nicht durch DB-Constraints
erzwungen. Der Detector prüft deren Präsenz und Nicht-Leer-Wert im JSON-Feld.

---

## Detector-Design

```python
class MetadataQualityDetector:
    """Erkennt fehlende Pflichtmetadaten in aktiven Dokumenten.

    Contracts:
    - Read-only. Keine Mutations.
    - Workspace-scoped.
    - Gibt list[dict] zurück — partial finding kwargs, kompatibel mit DataQualityRunner.
    """

    RULES = [
        # (id, field_path, severity, title, description_tmpl)
        ("MQ-1", "title",             "error",   "Leerer Dokumenttitel", ...),
        ("MQ-2", "metadata.tags",     "warning", "Fehlende Tags", ...),
        ("MQ-3", "metadata.category", "warning", "Fehlende Kategorie", ...),
        ("MQ-4", "metadata.doc_type", "warning", "Fehlender Dokumenttyp", ...),
        ("MQ-5", "metadata.summary",  "info",    "Fehlende Zusammenfassung", ...),
    ]

    def detect(self) -> list[dict[str, Any]]: ...
```

Abfragestrategie:

- MQ-1: `SELECT id FROM documents WHERE workspace_id=? AND lifecycle_status='active' AND trim(title)=''`
- MQ-2 bis MQ-5: JOIN auf `document_versions` über `documents.current_version_id`, dann Python-seitige Auswertung des JSON-Felds (DB-agnostisch)

---

## Gate-Kriterien (m5a_metadata_detector_gate)

| ID | Kriterium | Methode | Schwelle |
|---|---|---|---|
| C1 | MQ-1: leerer Titel erkannt | SQLite in-memory, seed doc mit `title=""` | min. 1 Finding, typ=MISSING_METADATA, sev=error |
| C2 | MQ-2: fehlende Tags erkannt | SQLite in-memory, `metadata_={}` | min. 1 Finding, sev=warning |
| C3 | MQ-3: fehlende Kategorie erkannt | SQLite in-memory | min. 1 Finding, sev=warning |
| C4 | MQ-4: fehlender Dokumenttyp erkannt | SQLite in-memory | min. 1 Finding, sev=warning |
| C5 | MQ-5: fehlende Zusammenfassung erkannt | SQLite in-memory | min. 1 Finding, sev=info |
| C6 | Keine False Positives bei vollstaendigen Metadaten | Dokument mit allen Feldern gesetzt | 0 Findings |
| C7 | Nur aktive Dokumente geprüft | Archived/deleted doc mit leerem Titel | 0 Findings |
| C8 | Workspace Isolation | 2 Workspaces, Findings nur in eigenem WS | 0 Findings in WS B |
| C9 | Keine Dokumentmutation | Snapshot before/after Detector | Snapshots identisch |
| C10 | Finding-Shape Runner-kompatibel | Alle Pflichtkeys vorhanden | `run_id` nicht in dict |
| C11 | Runner integriert MetadataQualityDetector | Runner.run() liefert >= 1 Finding bei leerem Titel | status=completed |

Schwelle: Score >= 90 (10/11 oder alle 11) = GO.

---

## Abhängigkeiten zu anderen Slices

- Kein Blocking durch andere offene Slices.
- `MISSING_METADATA` Finding-Typ bereits in `FINDING_TYPE_VALUES` — kein Modell-Change.
- Gate-Report: `reports/current/m5a_metadata_detector_gate.json` (wird nach Implementierung durch `scripts/generate_m5a_metadata_detector_gate.py` erzeugt)

---

## Risiken

| Risiko | Schwere | Mitigation |
|---|---|---|
| `metadata_["tags"]` fehlt im JSON-Feld ganz (KeyError) | mittel | `.get("tags")` statt `["tags"]`; None und `[]` gelten als fehlend |
| `current_version_id` ist NULL für neue Dokumente | niedrig | LEFT JOIN + NULL-Check; kein Finding wenn keine Version vorhanden |
| Grosse Workspaces: viele Dokumente ohne Metadaten → Performance | niedrig | LIMIT 500 je Regel; M5-Retrieval-Benchmark als Referenz |
| `trim(title)` verhält sich unterschiedlich in SQLite vs PostgreSQL | niedrig | Python-seitiger Strip nach DB-Query; keine DB-spezifische Funktion |
