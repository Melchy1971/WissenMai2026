# M5b Drift Detection — Entity Mapping

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; keine Implementierung erlaubt, siehe `reports/current/m5b_implementation_gate.json`).

Maschinenlesbares Schema: `drift_entity_mapping.json`.
Severity-Referenz: `drift_severity_matrix.json`.
Typ-Autorität: `schemas/drift_types.schema.json`.

---

## Überblick

Drift Detection operiert auf 7 Entitäten. Jede Entität ist einer oder mehreren Primärquellen zugeordnet, hat eine definierte Validierungslogik und erzeugt spezifische Report-Artefakte. Die Entitäten sind workspace-scoped; kein Entitätszugriff über Workspace-Grenzen hinweg.

| Entität | Tabelle / Quelle (primär) | mögliche Drift-Typen |
|---------|--------------------------|---------------------|
| Document | `documents` | DOCUMENT_DRIFT, LIFECYCLE_DRIFT |
| Version | `document_versions` | DOCUMENT_DRIFT |
| Chunk | `document_chunks` | CHUNK_DRIFT, LIFECYCLE_DRIFT, SEARCH_INDEX_DRIFT |
| Citation | `document_citations` | DOCUMENT_DRIFT |
| SourceStatus | `data_sources` | SOURCE_STATUS_DRIFT |
| Lifecycle | `documents.lifecycle_status`, `document_chunks.is_searchable` | LIFECYCLE_DRIFT |
| SearchIndex | search index (extern) vs. `document_chunks` | SEARCH_INDEX_DRIFT, RETRIEVAL_DRIFT |

---

## Document

### Mögliche Drift-Typen

- `DOCUMENT_DRIFT` — Content-Hash, Struktur, Feldintegrität
- `LIFECYCLE_DRIFT` — lifecycle_status vs. tatsächlicher Indexierungszustand

### Datenquelle

| Quelle | Rolle |
|--------|-------|
| `documents` (PostgreSQL) | Primärquelle; content_hash, lifecycle_status, import_status |
| Search Index (Dokument-Ebene) | Vergleichsquelle für Indexierungszustand |

### Validierungslogik

1. Lese `content_hash` aus `documents` für workspace_id
2. Vergleiche mit erwartetem Hash aus letztem Snapshot (DriftSnapshot)
3. Prüfe `lifecycle_status` gegen `is_searchable`-Zustand im Index
4. Prüfe `import_status=completed`-Dokumente auf fehlende Pflichtfelder

Abweichung → Finding erzeugen mit `entity_type=document`, `entity_id=documents.id`.

### Reports

| Report | Inhalt |
|--------|--------|
| `drift_report.json` | Findings je workspace mit entity_type=document |
| `drift_summary.json` | Aggregation DOCUMENT_DRIFT-Findings |

---

## Version

### Mögliche Drift-Typen

- `DOCUMENT_DRIFT` — Versionsinhalte weichen von gespeicherten Hashes ab

### Datenquelle

| Quelle | Rolle |
|--------|-------|
| `document_versions` (PostgreSQL) | Primärquelle; version_hash, created_at, document_id |
| `documents.current_version_id` | FK-Konsistenz |

### Validierungslogik

1. Prüfe FK-Konsistenz: `current_version_id` in `documents` verweist auf vorhandenen Eintrag in `document_versions`
2. Prüfe `version_hash` auf Unveränderlichkeit nach `finalized_at`
3. Prüfe Versionskette auf Lücken (fehlende Zwischenversionen)

Abweichung → Finding mit `entity_type=document`, `entity_id=document_id` (Version hat keine eigene entity_type-Kategorie; wird unter Document gemeldet).

### Reports

| Report | Inhalt |
|--------|--------|
| `drift_report.json` | DOCUMENT_DRIFT-Findings mit version_context |

---

## Chunk

### Mögliche Drift-Typen

- `CHUNK_DRIFT` — Chunk-Anzahl, Chunk-Inhalt, Chunk-Zustand
- `LIFECYCLE_DRIFT` — is_searchable vs. Lifecycle-Status des Parent-Dokuments
- `SEARCH_INDEX_DRIFT` — Chunk im Index ohne DB-Eintrag (Phantom) oder umgekehrt

### Datenquelle

| Quelle | Rolle |
|--------|-------|
| `document_chunks` (PostgreSQL) | Primärquelle; chunk_hash, is_searchable, document_id |
| `documents.expected_chunk_count` | Erwartete Chunk-Anzahl nach Import |
| Search Index | Vergleichsquelle für Index-Präsenz |

### Validierungslogik

1. Zähle Chunks je `document_id` in `document_chunks`; vergleiche mit `expected_chunk_count`
2. Prüfe `is_searchable` aller Chunks gegen `lifecycle_status` des Parent-Dokuments
3. Führe workspace-scoped Index-DB-Abgleich durch: Index-Einträge ohne DB-Pendant → Phantom; DB-Einträge ohne Index → missing
4. Prüfe `chunk_hash` auf Unveränderlichkeit nach Indexierungsabschluss

Abweichung → Finding mit `entity_type=chunk`, `entity_id=document_chunks.id`.

### Reports

| Report | Inhalt |
|--------|--------|
| `drift_report.json` | CHUNK_DRIFT- und LIFECYCLE_DRIFT-Findings |
| `drift_gate_report.json` | Phantom-Chunk-Count als Gate-Kriterium |

---

## Citation

### Mögliche Drift-Typen

- `DOCUMENT_DRIFT` — Citation-Snapshot weicht von aktuellem Chunk-Content ab

### Datenquelle

| Quelle | Rolle |
|--------|-------|
| `document_citations` (PostgreSQL) | Primärquelle; snapshot_content_hash, chunk_id, created_at |
| `document_chunks.chunk_hash` | Vergleichsquelle für Content-Drift |

### Validierungslogik

1. Lese `snapshot_content_hash` je Citation
2. Vergleiche mit aktuellem `chunk_hash` des referenzierten Chunks
3. Abweichung → Citation-Snapshot ist veraltet; Chunk-Inhalt hat sich geändert

Abweichung → Finding mit `entity_type=document`, `entity_id=document_id` der Citation (Citation ist keine eigenständige gate-relevante Entität).

### Reports

| Report | Inhalt |
|--------|--------|
| `drift_report.json` | DOCUMENT_DRIFT mit citation_context |

---

## SourceStatus

### Mögliche Drift-Typen

- `SOURCE_STATUS_DRIFT` — Registrierter Status weicht von tatsächlichem Zustand ab

### Datenquelle

| Quelle | Rolle |
|--------|-------|
| `data_sources` (PostgreSQL) | Primärquelle; source_status, last_successful_sync |
| Connectivity-Check (read-only) | Verfügbarkeitstest zur Erkennungszeit |

### Validierungslogik

1. Lese `source_status` und `last_successful_sync` je data_source in workspace
2. Führe read-only Connectivity-Check durch (kein schreibender Zugriff)
3. Vergleiche: Quelle antwortet nicht + `source_status=active` → SOURCE_STATUS_DRIFT
4. Prüfe Zeitdelta seit `last_successful_sync` gegen konfigurierten Timeout

Abweichung → Finding mit `entity_type=source`, `entity_id=data_sources.id`.

### Reports

| Report | Inhalt |
|--------|--------|
| `drift_report.json` | SOURCE_STATUS_DRIFT-Findings |
| `drift_summary.json` | source_status_drift_rate |

---

## Lifecycle

Lifecycle ist keine eigenständige DB-Tabelle, sondern ein Zustandsattribut auf `documents` und `document_chunks`. Es wird als eigenständige Entität im Entity Mapping geführt, weil `LIFECYCLE_DRIFT` eine eigene Validierungslogik mit zwei Datenquellen erfordert.

### Mögliche Drift-Typen

- `LIFECYCLE_DRIFT` — lifecycle_status vs. Suchbarkeitszustand

### Datenquelle

| Quelle | Rolle |
|--------|-------|
| `documents.lifecycle_status` (PostgreSQL) | Erwarteter Zustand |
| `document_chunks.is_searchable` (PostgreSQL) | Tatsächlicher Suchbarkeitszustand auf Chunk-Ebene |
| Search Index | Tatsächlicher Indexierungszustand |

### Validierungslogik

1. Lese alle Dokumente mit `lifecycle_status IN (archived, deleted)` im workspace
2. Prüfe zugehörige Chunks: `is_searchable=true` → LIFECYCLE_DRIFT (error)
3. Prüfe Search Index: gelöschtes Dokument mit Index-Eintrag → LIFECYCLE_DRIFT (critical)
4. Prüfe umgekehrt: aktives Dokument mit `is_searchable=false` trotz abgeschlossenem Import → LIFECYCLE_DRIFT (warning-Kandidat, kein Datenschutzproblem)

Abweichung → Finding mit `entity_type=document` oder `entity_type=chunk`, je nach Scope.

### Reports

| Report | Inhalt |
|--------|--------|
| `drift_report.json` | LIFECYCLE_DRIFT-Findings |
| `drift_gate_report.json` | lifecycle_drift_count als Gate-Kriterium |
| `drift_summary.json` | lifecycle_drift_rate |

---

## SearchIndex

### Mögliche Drift-Typen

- `SEARCH_INDEX_DRIFT` — Index vs. DB-Divergenz auf Chunk-Ebene
- `RETRIEVAL_DRIFT` — Retrieval-Qualität vs. Golden-Baseline

### Datenquelle

| Quelle | Rolle |
|--------|-------|
| Search Index (workspace-scoped query) | Tatsächlicher Index-Inhalt |
| `document_chunks` (PostgreSQL) | Erwarteter Inhalt |
| Golden Baseline (`drift_baseline.json`) | Erwartete Retrieval-Qualität |

### Validierungslogik

**SEARCH_INDEX_DRIFT:**
1. Lese alle index_entry-IDs im workspace aus dem Search Index (read-only)
2. Lese alle `document_chunks.id` mit `is_searchable=true` im workspace
3. Differenzmenge: Index-only → Phantom; DB-only → Missing
4. Phantom- oder Missing-Einträge → SEARCH_INDEX_DRIFT

**RETRIEVAL_DRIFT:**
1. Führe definierte Retrieval-Testqueries gegen workspace durch (read-only)
2. Berechne Metrik-Delta gegen Golden Baseline
3. Delta > Schwelle → RETRIEVAL_DRIFT

Abweichung → Finding mit `entity_type=index_entry`, `entity_id=chunk_id`.

### Reports

| Report | Inhalt |
|--------|--------|
| `drift_report.json` | SEARCH_INDEX_DRIFT- und RETRIEVAL_DRIFT-Findings |
| `drift_gate_report.json` | index_divergence_count, retrieval_baseline_delta |
| `drift_history.json` | Trend über Runs: wachsende vs. schrumpfende Divergenz |

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `drift_entity_mapping.json` | Maschinenlesbare Version |
| `schemas/drift_types.schema.json` | Typ-Autorität |
| `drift_severity_matrix.json` | Severity pro Typ |
| `drift_governance.schema.json` | Verbotene Operationen |
| `docs/m5b-drift-governance.md` | Governance |
| `reports/current/m5b_gate_criteria.json` | Gate-Authority |
