# M5b Drift Detection — History Model

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; keine Implementierung erlaubt, siehe `reports/current/m5b_implementation_gate.json`).

Maschinenlesbares Schema: `drift_history_model.json`.

---

## Überblick

Das History Model definiert drei Entitäten für die lückenlose Historisierung von Drift-Erkennungen. Es ermöglicht Trendanalyse ohne Datenmutation oder -löschung.

| Entität | Zweck |
|---------|-------|
| `DriftRun` | Metadaten eines einzelnen Scan-Durchlaufs |
| `DriftFinding` | Einzelner Drift-Befund mit Zustandsvergleich |
| `DriftSnapshot` | Zustandsabbild eines Workspace zum Erkennungszeitpunkt |

---

## DriftRun

**Definition:** Ein DriftRun repräsentiert einen vollständigen Scan-Durchlauf für genau einen Workspace. Mehrere Workspaces erfordern mehrere DriftRuns; kein gemeinsamer Run über Workspace-Grenzen.

### Felder

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `run_id` | UUID | ja | Eindeutiger Identifier; unveränderlich |
| `workspace_id` | UUID | ja | Workspace-Scope; unveränderlich nach Erstellung |
| `started_at` | ISO 8601 | ja | Startzeitpunkt des Runs; unveränderlich |
| `completed_at` | ISO 8601 | nein | Abschlusszeitpunkt; null wenn noch laufend oder fehlgeschlagen |
| `status` | enum | ja | `running`, `completed`, `failed` |
| `total_checks` | integer | ja | Anzahl ausgeführter Prüfungen |
| `total_findings` | integer | ja | Anzahl erzeugter Findings |
| `snapshot_id` | UUID | ja | FK auf DriftSnapshot, der diesem Run zugrunde liegt |
| `metrics` | DriftMetrics | ja | Kennzahlen des Runs (Referenz: `drift_metrics.schema.json`) |

### Regeln

- Ein `failed` Run ist vollständig historisiert; keine nachträgliche Korrektur
- `completed_at` bleibt `null` bis der Run tatsächlich abgeschlossen ist
- Ein Run ohne `completed_at` nach konfigurierbarem Timeout gilt als `failed`

---

## DriftFinding

**Definition:** Ein DriftFinding ist ein unveränderlicher Befund einer Abweichung, erzeugt innerhalb eines DriftRun.

Schema-Referenz: `drift_governance.schema.json` (autoritative Felddefinition).

### Felder (aus `drift_governance.schema.json` + History-Erweiterung)

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `drift_id` | UUID | ja | Eindeutig; stabil über Runs solange Zustand unverändert |
| `run_id` | UUID | ja | FK auf DriftRun |
| `drift_type` | enum (7 Typen) | ja | Typ des Drifts |
| `severity` | enum | ja | info, warning, error, critical |
| `workspace_id` | UUID | ja | Workspace-Scope |
| `entity_type` | enum | ja | document, chunk, source, index_entry, metadata_record |
| `entity_id` | UUID | ja | PK der betroffenen Entität |
| `expected_state` | object | ja | Erwarteter Zustand; unveränderlich |
| `actual_state` | object | ja | Tatsächlicher Zustand; unveränderlich |
| `remediation_hint` | string | ja | Deskriptiv; keine Aktionsanweisung |
| `created_at` | ISO 8601 | ja | Erkennungszeitpunkt; unveränderlich |
| `first_seen_run_id` | UUID | ja | Run-ID bei Erstauftreten dieses Findings (Tracking-Zweck) |
| `last_seen_run_id` | UUID | ja | Run-ID des letzten Runs, der dieses Finding reproduziert hat |
| `occurrence_count` | integer | ja | Anzahl der Runs, in denen dieses Finding aufgetreten ist |

### Stabilität der drift_id

`drift_id` ist stabil über mehrere Runs, wenn die Kombination aus `(workspace_id, entity_type, entity_id, drift_type)` identisch bleibt. Ein Finding mit neuer Kombination erhält eine neue `drift_id`.

---

## DriftSnapshot

**Definition:** Ein DriftSnapshot ist ein Zustandsabbild des Workspace zum Zeitpunkt eines DriftRun. Er dient als Vergleichsbasis für Trendanalyse und Reproduzierbarkeit.

### Felder

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `snapshot_id` | UUID | ja | Eindeutig; unveränderlich |
| `workspace_id` | UUID | ja | Workspace-Scope |
| `captured_at` | ISO 8601 | ja | Zeitstempel der Snapshot-Erstellung; unveränderlich |
| `document_count` | integer | ja | Anzahl Dokumente im Workspace zum Zeitpunkt |
| `chunk_count` | integer | ja | Anzahl Chunks im Workspace zum Zeitpunkt |
| `indexed_chunk_count` | integer | ja | Anzahl indizierter Chunks |
| `active_source_count` | integer | ja | Anzahl Quellen mit `source_status=active` |
| `content_hash_digest` | string | ja | Aggregierter Hash über alle `content_hash`-Werte (deterministisch) |
| `baseline_ref` | string | nein | Referenz auf Baseline-Datei für RETRIEVAL_DRIFT-Vergleich |

### Regeln

- Ein DriftSnapshot wird ausschließlich zu Beginn eines DriftRun erzeugt (kein manuelles Erstellen)
- Snapshots werden nie gelöscht; Retention-Policy ist konfigurierbar (Standard: unbegrenzt)
- `content_hash_digest` muss deterministisch reproduzierbar sein für denselben Datenbankzustand

---

## Historisierung

Jedes DriftFinding bleibt permanent im History Store. Gelöscht wird nie. Wenn ein Finding in einem späteren Run nicht mehr reproduzierbar ist, wird es im neuen Run nicht aufgeführt — das Finding aus früheren Runs bleibt bestehen.

**Retention:**

| Artefakt | Retention |
|----------|-----------|
| DriftRun | unbegrenzt |
| DriftFinding | unbegrenzt |
| DriftSnapshot | unbegrenzt (Standard); konfigurierbar |
| Reports in `reports/current/` | letzter Run (aktuell); Archiv separat |

---

## Trendanalyse

Trendanalyse erfolgt durch Vergleich von Metriken über mehrere DriftRuns desselben Workspace. Folgende Trends sind definiert:

| Trend | Erkennung | Gate-Relevanz |
|-------|-----------|---------------|
| Wachsende Index-Divergenz | SEARCH_INDEX_DRIFT: absolute_delta wächst über ≥ 2 Runs | CRITICAL nach 2 Runs |
| Persistente Retrieval-Degradierung | RETRIEVAL_DRIFT: negatives Delta in ≥ 3 aufeinander folgenden Runs | CRITICAL |
| Zunehmende lifecycle_drift_rate | lifecycle_drift_rate steigt über Runs | Operator-Flag |
| Abnehmende Scan-Vollständigkeit | total_checks fällt unter expected_checks | Warn-Flag |

Trendanalyse ist ausschließlich lesend; sie mutiert keine Findings und löst keine automatischen Korrekturen aus.

---

## Workspace-Isolation

- History-Abfragen sind immer workspace-scoped
- Kein Run umfasst mehrere Workspaces
- Cross-Workspace-Aggregation über History-Daten ist verboten
- `workspace_id` ist in allen drei History-Entitäten Pflichtfeld und unveränderlich nach Erstellung

---

## Keine Löschung

Weder DriftRun noch DriftFinding noch DriftSnapshot werden gelöscht. Ausnahmen erfordern einen expliziten Operator-Entscheid mit Audit-Eintrag. Das Löschen von Findings ohne Audit-Eintrag verletzt `PROHIBIT-05` aus `drift_governance.schema.json`.

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `drift_history_model.json` | Maschinenlesbares Schema |
| `drift_governance.schema.json` | DriftFinding-Felddefinition, PROHIBIT-05 |
| `drift_metrics.schema.json` | Metriken-Felder in DriftRun |
| `drift_severity_matrix.json` | Eskalationsregeln für Trendanalyse |
| `reports/current/m5b_gate_criteria.json` | Gate-Authority |
