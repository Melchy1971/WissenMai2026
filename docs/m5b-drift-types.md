# M5b Drift-Typen

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; kein `PREPARED`, kein `GO`, keine Implementierung, siehe `reports/current/m5b_release_decision.json`).

Dieses Dokument definiert die sieben finalen Drift-Typen für M5b. Alle Prüfungen sind read-only, workspace-scoped und nicht-mutierend. Repair und Cleanup liegen außerhalb dieses Scope.

Autoritative Typdefinition: `schemas/drift_types.schema.json`.
Report-Envelope-Schema: `drift_schema.json` (muss bei PREPARED-Übergang auf 7 Typen erweitert werden).

---

## Gemeinsames Modell

### Severity-Werte

| Severity | Bedeutung |
|----------|-----------|
| `info` | Beobachtbare Abweichung ohne unmittelbares Risiko. Nur Trend verfolgen. |
| `warning` | Abweichung kann Qualität oder Betriebsvertrauen beeinträchtigen. Review erforderlich. |
| `error` | Abweichung verletzt Daten-, Lifecycle-, Source- oder Retrieval-Korrektheit. Blockiert M5b Gate. |
| `critical` | Abweichung kann gelöschte Daten exponieren, aktive Daten verstecken, Workspace-Grenzen überschreiten oder Recovery invalidieren. Freeze mutierende Operationen, sofortige Eskalation. |

### Gemeinsame Report-Felder aller Findings

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `drift_id` | `uuid` | Stabiler Finding-Identifier für den Lauf |
| `drift_type` | `string` | Einer der 7 finalen Typen |
| `drift_subtype` | `string` | Spezifische Regelkennung innerhalb des Typs |
| `workspace_id` | `uuid` | Workspace-Scope des Findings |
| `severity` | `string` | `info`, `warning`, `error`, `critical` |
| `entity` | `object` | Betroffene Objekt-Referenzen (IDs) |
| `expected_state` | `string/object` | Maschinenlesbarer Sollzustand |
| `observed_state` | `string/object` | Maschinenlesbarer Istzustand |
| `detection_strategy` | `string` | Regel oder Query-Familie |
| `remediation_hint` | `string` | Handlungsempfehlung; darf keine automatische Aktion implizieren |
| `escalation` | `string` | Operative Aktion nach Severity und Schwelle |
| `created_at` | `datetime` | Zeitstempel des Findings im Lauf |

---

## 1. DOCUMENT_DRIFT

### Definition

Ein Dokument weicht über die Zeit von seinem kanonischen Strukturzustand ab. Die Beziehung zwischen `documents`-Zeile, aktuellem Versionszeiger (`current_version_id`), Versionssequenz, Content-Hash und Chunk-Set muss das gleiche logische Dokument beschreiben. DOCUMENT_DRIFT liegt vor, wenn diese Kohärenz ohne valides Import-, Versionierungs- oder Lifecycle-Event zerfallen ist.

Abgrenzung: DOCUMENT_DRIFT vergleicht ein Dokument gegen seinen eigenen Sollzustand, nicht gegen andere Dokumente (das ist M5a Duplicate Detection).

### Ursache

- `documents.current_version_id` zeigt auf eine nicht existierende `document_versions.id`
- Dokument hat keinen Versionszeiger trotz abgeschlossenem Import
- Aktives, import-abgeschlossenes Dokument hat keine Chunks in der aktuellen Version
- Versionsnummern fehlen, sind doppelt oder nicht monoton
- Content-Hash des Dokuments stimmt nicht mehr mit dem Hash der aktuellen Version überein
- `updated_at` hat sich verändert, ohne dass eine neue Version oder ein Lifecycle-Event vorliegt

### Erkennungsidee

Read-only, workspace-scoped Joins über `documents`, `document_versions` und `document_chunks`. Vergleich von Dokumentzeigern, Versions-Cardinality, Chunk-Cardinality und Timestamp/Hash-Invarianten. Kein Zugriff auf Rohdateien.

### Severity

| Bedingung | Severity |
|-----------|----------|
| `current_version_id` zeigt ins Leere | `error` |
| Aktives, abgeschlossenes Dokument ohne Versionszeiger | `error` |
| Aktives, abgeschlossenes Dokument ohne Chunks | `error` |
| Versionslücke oder Versionsduplikat | `warning` |
| Hash-Abweichung ohne Inhaltsverlust-Evidenz | `warning` |
| Timestamp-Drift ohne strukturellen Schaden | `info` |

Gate-Schwelle: DOCUMENT_DRIFT errors > 5 % aktiver Dokumente → Gate-Blocker.

### Betroffene Tabellen

| Tabelle | Felder |
|---------|--------|
| `documents` | `id`, `workspace_id`, `current_version_id`, `content_hash`, `import_status`, `lifecycle_status`, `updated_at` |
| `document_versions` | `id`, `document_id`, `version_number`, `markdown_hash` |
| `document_chunks` | `id`, `document_id`, `document_version_id`, `chunk_index` |

### Betroffene Gates

| Gate | Wirkung |
|------|---------|
| `m5b_release_decision` | errors > 0 blockieren PREPARED |
| `m5b_start_gate` | errors blockieren Implementierungsfreigabe |

### Report-Felder (finding-spezifisch)

| Feld | Typ | Pflicht |
|------|-----|---------|
| `document_id` | `uuid` | ja |
| `version_id` | `uuid\|null` | nein |
| `drift_subtype` | `string` | ja |

Erlaubte Subtypes: `missing_current_version`, `broken_version_reference`, `active_document_without_chunks`, `version_sequence_gap`, `version_sequence_duplicate`, `hash_contract_mismatch`, `timestamp_without_version_event`.

---

## 2. CHUNK_DRIFT

### Definition

Der gespeicherte Chunk-Zustand stimmt nicht mehr mit dem erwarteten Chunk-Set der aktuellen Dokumentversion überein. Chunks sind Retrieval-Einheiten: Document-ID, Version-ID, Content-Hash, Normalisierungs-Hash, Reihenfolge, Lifecycle-Sichtbarkeit und Index-Eligibility müssen konsistent mit der kanonischen Version sein.

Abgrenzung: CHUNK_DRIFT vergleicht den aktuellen Chunk-Set gegen den erwarteten Set derselben Version und desselben Workspace. M5a Duplicate Detection vergleicht inhaltlich äquivalente Chunks über Dokumente hinweg.

### Ursache

- Aktive Version hat weniger Chunks als der genehmigte Baseline-Count oder Chunk-Hash-Baseline
- Chunks referenzieren eine ältere Version, während `documents.current_version_id` woanders zeigt
- Chunk-Reihenfolge hat Lücken, Duplikate oder nicht-monotone Positionen
- `content_hash` oder `metadata`-Hash hat sich ohne Versionierungs-, Parser- oder Restore-Event verändert
- `document_id`, `document_version_id` oder `workspace_id` eines Chunks stimmt nicht mit dem Eigentümer-Dokument überein
- Chunk `is_searchable` divergiert von Dokument-Lifecycle oder Source-Status

### Erkennungsidee

Read-only, workspace-scoped Joins über `documents`, `document_versions` und `document_chunks`. Prüfung von Chunk-Mitgliedschaft in aktueller Version, Positionssequenz, Hash-Stabilität, Ownership-Konsistenz und lifecycle-abgeleiteter Suchbarkeit. Kein Reparse, keine Chunk-Generierung, keine Index-Mutation.

### Severity

| Bedingung | Severity |
|-----------|----------|
| Chunk referenziert fehlendes Dokument oder Version | `error` |
| Chunk gehört zu einem anderen Workspace als sein Dokument | `critical` |
| Aktive Version hat weniger Chunks als Baseline | `error` |
| Chunk-Reihenfolge hat Lücken oder Duplikate | `warning` |
| Chunk-Hash ohne Versions- oder Parser-Event verändert | `warning` |
| `is_searchable` inkonsistent mit Lifecycle-Status | `error` |
| Historische Baseline nicht verfügbar | `info` |

Gate-Schwelle: CHUNK_DRIFT errors > 2 % eligibler aktiver Chunks → Gate-Blocker. `critical` → sofortige Workspace-Isolation-Review.

### Betroffene Tabellen

| Tabelle | Felder |
|---------|--------|
| `document_chunks` | `id`, `document_id`, `document_version_id`, `chunk_index`, `content_hash`, `is_searchable`, `metadata`, `created_at` |
| `document_versions` | `id`, `document_id`, `version_number` |
| `documents` | `id`, `workspace_id`, `current_version_id`, `lifecycle_status` |

### Betroffene Gates

| Gate | Wirkung |
|------|---------|
| `m5b_release_decision` | `critical` blockiert PREPARED sofort; errors > 2 % blockieren Gate |
| `m5b_start_gate` | `critical` blockiert Implementierungsfreigabe |

### Report-Felder (finding-spezifisch)

| Feld | Typ | Pflicht |
|------|-----|---------|
| `chunk_id` | `uuid` | ja |
| `document_id` | `uuid` | ja |
| `version_id` | `uuid\|null` | nein |
| `drift_subtype` | `string` | ja |

Erlaubte Subtypes: `chunk_missing_from_current_version`, `chunk_wrong_version_reference`, `chunk_position_gap`, `chunk_position_duplicate`, `chunk_hash_changed_without_event`, `chunk_workspace_mismatch`, `chunk_searchability_mismatch`, `chunk_baseline_missing`.

---

## 3. METADATA_DRIFT

### Definition

Dokument- oder Versions-Metadaten haben sich ohne valides Versionierungs- oder Import-Event über die Zeit verschlechtert: Felder fehlen, Typen haben sich geändert, Schlüssel sind weggefallen oder Timestamps sind inkonsistent geworden.

Abgrenzung: M5a Metadata Detection prüft den aktuellen Zustand. M5b METADATA_DRIFT prüft Regression von einem früheren validen Zustand zu einem späteren degradierten Zustand.

### Ursache

- Metadaten-Schlüssel wie `tags`, `category`, `doc_type`, `summary` waren in einer früheren Version vorhanden und fehlen in der aktuellen
- Wert-Typ eines bekannten Feldes hat sich unerwartet geändert (z. B. `tags`: Array → String)
- Pflicht-Metadaten-Schlüssel in `document_versions.metadata` verschwunden
- Metadaten-Timestamp-Felder sind rückwärts gegangen oder nicht mehr mit dem Versions-Erstellzeitpunkt konsistent
- Dokument-Level-Titel/Source-Metadaten weichen von Versions-Metadaten ohne Version-Event ab

### Erkennungsidee

Vergleich historischer Versionen desselben Dokuments in Versionsreihenfolge. Baseline: die letzte valide frühere Version. Prüfung von JSON-Shape und bekannten Feldtypen. Read-only, workspace-scoped. Keine KI-Inference, kein Dokument-Reparse, keine Metadaten-Anreicherung.

### Severity

| Bedingung | Severity |
|-----------|----------|
| Pflicht-Schlüssel von befüllt zu fehlend regriert | `warning` |
| Metadaten-Typ zu ungültigem Shape geändert | `warning` |
| Metadaten-Timestamp rückwärts gegangen | `info` |
| Metadatenverlust betrifft Retrieval-Filter oder Source-Klassifikation | `error` |
| Cross-Workspace-Metadaten-Referenz | `critical` |

Gate-Schwelle: METADATA_DRIFT errors > 2 % aktiver Dokumente → Gate-Blocker. `critical` → Workspace-Reporting-Freeze.

### Betroffene Tabellen

| Tabelle | Felder |
|---------|--------|
| `document_versions` | `id`, `document_id`, `version_number`, `metadata`, `created_at` |
| `documents` | `id`, `workspace_id`, `title`, `updated_at` |

### Betroffene Gates

| Gate | Wirkung |
|------|---------|
| `m5b_release_decision` | errors blockieren PREPARED |
| `m5b_start_gate` | `critical` blockiert Implementierungsfreigabe |

### Report-Felder (finding-spezifisch)

| Feld | Typ | Pflicht |
|------|-----|---------|
| `document_id` | `uuid` | ja |
| `version_id` | `uuid` | ja |
| `previous_version_id` | `uuid\|null` | nein |
| `affected_fields` | `string[]` | ja |
| `drift_subtype` | `string` | ja |

Erlaubte Subtypes: `metadata_key_regression`, `metadata_type_regression`, `metadata_timestamp_drift`, `document_version_metadata_mismatch`, `retrieval_filter_metadata_loss`, `cross_workspace_metadata_reference`.

---

## 4. LIFECYCLE_DRIFT

### Definition

Der Lifecycle-Status eines Dokuments und das Verhalten abhängiger Systeme divergieren über die Zeit. `lifecycle_status`, Import-Status, Chunk-Suchbarkeit, Citations, Retrieval-Sichtbarkeit, Timestamps und Audit-Evidenz müssen ein konsistentes Bild ergeben.

Abgrenzung: M5a Lifecycle Integrity prüft aktuelle Konsistenz. M5b LIFECYCLE_DRIFT prüft zeitliche Divergenz nach validen Lifecycle-Transitionen, Restore, Reindex oder Recovery.

### Ursache

- Gelöschte oder archivierte Dokumente erscheinen in Such- oder Retrieval-Ergebnissen
- Aktive Dokumente nicht suchbar, obwohl Import- und Chunk-Status valide sind
- `lifecycle_status` hat sich ohne entsprechenden Timestamp oder Audit-Evidenz geändert
- `archived_at` oder `deleted_at` konfligiert mit `lifecycle_status`
- Chunk `is_searchable` spiegelt Dokument-Lifecycle nicht wider
- Restore oder Reindex ändert Retrieval-Sichtbarkeit ohne passenden Lifecycle-Status

### Erkennungsidee

Kombination aus DB-Prüfung (Lifecycle-Werte, Timestamp-Konsistenz, Chunk-`is_searchable`) und Retrieval-Sichtbarkeits-Sonden (workspace-scoped, read-only). DB- und Index-Inkonsistenzen werden getrennt gemeldet. Kein Reindex, keine Status-Mutation, keine Citation-Aktualisierung.

### Severity

| Bedingung | Severity |
|-----------|----------|
| Gelöschtes Dokument ist suchbar oder abrufbar | `critical` |
| Archiviertes Dokument erscheint in aktiver Standardsuche | `error` |
| Aktives Dokument mit validen Chunks nicht suchbar | `error` |
| Lifecycle-Status und Timestamp konfligieren | `warning` |
| Audit-Evidenz für nicht-aktives Dokument fehlt | `warning` |
| Pending-Dokument-Sichtbarkeit ist mehrdeutig, aber nicht exponiert | `info` |

Gate-Schwelle: LIFECYCLE_DRIFT errors > 2 % aktiver Dokumente → Gate-Blocker. `critical` → sofortige Freeze mutierende Operationen im betroffenen Workspace.

### Betroffene Tabellen

| Tabelle | Felder |
|---------|--------|
| `documents` | `id`, `workspace_id`, `lifecycle_status`, `import_status`, `archived_at`, `deleted_at` |
| `document_chunks` | `id`, `document_id`, `is_searchable` |

### Betroffene Gates

| Gate | Wirkung |
|------|---------|
| `m5b_release_decision` | `critical` und errors blockieren PREPARED |
| `m5b_start_gate` | `critical` blockiert Implementierungsfreigabe |

### Report-Felder (finding-spezifisch)

| Feld | Typ | Pflicht |
|------|-----|---------|
| `document_id` | `uuid` | ja |
| `lifecycle_status` | `string` | ja |
| `import_status` | `string` | ja |
| `chunk_id` | `uuid\|null` | nein |
| `drift_subtype` | `string` | ja |

Erlaubte Subtypes: `deleted_document_searchable`, `archived_document_searchable`, `active_document_not_searchable`, `lifecycle_timestamp_mismatch`, `chunk_searchability_mismatch`, `missing_lifecycle_audit_evidence`, `restore_lifecycle_visibility_mismatch`.

---

## 5. SOURCE_STATUS_DRIFT

### Definition

Der `source_status` einer Citation spiegelt nicht mehr den aktuellen Lifecycle-Status des referenzierten Dokuments wider. Citations sind Vertrauensartefakte: sie müssen historischen Kontext erhalten, aber auch exponieren, ob die Quelle noch aktiv, archiviert, gelöscht oder nicht auffindbar ist.

Abgrenzung: Kein automatisches Citation-Rewriting. M5b erkennt nur veralteten oder inkonsistenten Source-Status.

### Ursache

- Citation hat `source_status=active`, während das referenzierte Dokument archiviert oder gelöscht ist
- Citation hat `source_status=archived`, während das Dokument gelöscht ist
- Citation referenziert fehlendes Dokument, ist aber nicht als `missing` markiert
- Citation ist als `missing` markiert, obwohl ein Dokument mit dieser ID im gleichen Workspace existiert
- Citation-Workspace-Kontext stimmt nicht mit dem Eigentümer-Workspace des Dokuments überein

### Erkennungsidee

Read-only Joins über `chat_citations`, `chat_messages`, `chat_sessions`, `documents`. Vergleich `chat_citations.source_status` mit `documents.lifecycle_status`. Workspace-Scope wird über den Session-Kontext abgeleitet. Kein Rewrite historischer Quote-Snapshots.

### Severity

| Bedingung | Severity |
|-----------|----------|
| Citation `active`, Dokument `deleted` | `error` |
| Citation `active`, Dokument `archived` | `warning` |
| Citation `archived`, Dokument `deleted` | `warning` |
| Citation referenziert fehlendes Dokument, Status nicht `missing` | `error` |
| Citation überschreitet Workspace-Grenze | `critical` |
| Citation `missing`, Dokument wieder vorhanden | `info` |

Gate-Schwelle: SOURCE_STATUS_DRIFT errors > 10 % non-missing Citations → Eskalation zu Technical Review. `critical` blockiert M5b sofort.

### Betroffene Tabellen

| Tabelle | Felder |
|---------|--------|
| `chat_citations` | `id`, `message_id`, `chunk_id`, `document_id`, `source_status`, `document_title`, `quote_preview` |
| `chat_messages` | `id`, `session_id`, `role` |
| `chat_sessions` | `id`, `workspace_id`, `owner_user_id` |
| `documents` | `id`, `workspace_id`, `lifecycle_status` |

### Betroffene Gates

| Gate | Wirkung |
|------|---------|
| `m5b_release_decision` | `critical` und errors blockieren PREPARED |
| `m5b_start_gate` | `critical` blockiert Implementierungsfreigabe |

### Report-Felder (finding-spezifisch)

| Feld | Typ | Pflicht |
|------|-----|---------|
| `citation_id` | `uuid` | ja |
| `message_id` | `uuid\|null` | nein |
| `document_id` | `uuid` | ja |
| `chunk_id` | `uuid\|null` | nein |
| `current_source_status` | `string` | ja |
| `current_lifecycle_status` | `string` | ja |
| `drift_subtype` | `string` | ja |

Erlaubte Subtypes: `source_status_stale`, `active_citation_deleted_source`, `active_citation_archived_source`, `missing_document_not_flagged`, `missing_status_but_document_exists`, `cross_workspace_citation_source`.

---

## 6. SEARCH_INDEX_DRIFT

### Definition

Der Suchindex weicht strukturell von der Datenbank als Source of Truth ab. Index enthält Chunks, die in `document_chunks` nicht mehr existieren (stale entries), oder eligiblen aktiven Chunks fehlen im Index (missing entries). Lifecycle-ausgeschlossene Inhalte sind im Index auffindbar.

Abgrenzung: SEARCH_INDEX_DRIFT prüft strukturelle Index-Konsistenz. RETRIEVAL_DRIFT prüft Retrieval-Qualität (Golden-Query-Regression). Beide Typen werden getrennt gemeldet.

### Ursache

- Suchindex enthält Chunk-IDs, die in `document_chunks` nicht mehr existieren
- Eligiblen aktiven Chunks (aktives Dokument, abgeschlossener Import, valide aktuelle Version, `is_searchable=true`) fehlen im Index
- Archivierte oder gelöschte Chunks sind im Suchindex auffindbar
- Index-Count und DB-Count eligibler Chunks divergieren über definierten Schwellenwert
- Reindex, Restore oder Migrations-Event hat Index-DB-Alignment gebrochen

### Erkennungsidee

Struktureller Vergleich: eligiblen DB-Chunks des Workspace gegen indexierte Chunks. Eligibilität: aktives Dokument, abgeschlossener Import, valide aktuelle Version, `is_searchable=true`. Meldung von stale entries, missing entries, lifecycle-excluded entries und Count-Diskrepanz. Kein Reindex, keine Index-Mutation.

### Severity

| Bedingung | Severity |
|-----------|----------|
| Gelöschter Content im Index abrufbar | `critical` |
| Archivierter Content in Standard-Retrieval | `error` |
| Eligibler aktiver Chunk fehlt im Index | `error` |
| Stale Index-Eintrag nicht abrufbar | `warning` |
| Count-Diskrepanz > 5 % | `warning` |

Gate-Schwelle: Missing entries > 0 für eligible aktive Chunks → Gate-Blocker (außer genehmigtem Maintenance-Window). `critical` → sofortige Freeze.

### Betroffene Tabellen

| Tabelle | Felder |
|---------|--------|
| `document_chunks` | `id`, `document_id`, `document_version_id`, `is_searchable` |
| `documents` | `id`, `workspace_id`, `lifecycle_status`, `import_status`, `current_version_id` |
| Search-Index | `chunk_id` (externe Komponente; kein DB-Table) |

### Betroffene Gates

| Gate | Wirkung |
|------|---------|
| `m5b_release_decision` | missing entries > 0 und `critical` blockieren PREPARED |
| `m5b_start_gate` | `critical` blockiert Implementierungsfreigabe |

### Report-Felder (finding-spezifisch)

| Feld | Typ | Pflicht |
|------|-----|---------|
| `chunk_id` | `uuid\|null` | nein |
| `document_id` | `uuid\|null` | nein |
| `index_count` | `integer` | ja |
| `db_count` | `integer` | ja |
| `discrepancy_percent` | `number` | nein |
| `drift_subtype` | `string` | ja |

Erlaubte Subtypes: `stale_index_entry`, `missing_index_entry`, `lifecycle_excluded_content_in_index`, `index_count_discrepancy`.

---

## 7. RETRIEVAL_DRIFT

### Definition

Die Retrieval-Qualität weicht von der genehmigten Golden-Query-Baseline ab. Metriken wie Precision@k, Recall@k und MRR regredieren über Zeit. Lifecycle-Ausschlussregeln werden im Retrieval verletzt.

Abgrenzung: RETRIEVAL_DRIFT prüft Qualität. SEARCH_INDEX_DRIFT prüft Struktur. Beide werden getrennt gemeldet.

### Ursache

- Golden-Query-Metriken weichen um mehr als definierten Threshold von Baseline ab
- Negative 7-Tage-Bewegung in Retrieval-Metriken
- Lifecycle-Ausschlussregeln werden im Retrieval verletzt (archivierte/gelöschte Docs abrufbar)
- Reindex, Import-Recovery oder Parser-Änderung hat Retrieval-Qualität verändert
- Baseline wurde nicht aktualisiert nach genehmigtem Reindex

### Erkennungsidee

Golden-Query-Benchmark gegen Retrieval-Pipeline: fixiertes Query-Set mit erwarteten Ergebnissen und dokumentierter Baseline. Metrik-Vergleich: Delta > Threshold → Finding. Lifecycle-Sonden: kontrollierte Queries auf archivierte/gelöschte Workspace-Inhalte. Beides read-only. Kein Reindex, keine Retrieval-Einstellungs-Mutation.

### Severity

| Bedingung | Severity |
|-----------|----------|
| Lifecycle-Ausschluss-Verletzung (gelöschter Content abrufbar) | `critical` |
| Lifecycle-Ausschluss-Verletzung (archivierter Content abrufbar) | `error` |
| Golden-Query-Regression > 25 % oder Lifecycle-Exclusion-Failure | `error` |
| Golden-Query-Regression > 10 % | `warning` |
| Negative 7d-Bewegung ohne Threshold-Überschreitung | `info` |

Gate-Schwelle: Retrieval-Baseline-Delta > 0,05 (5 %) → Gate-Blocker. Regression > 25 % auf mehr als einer Golden-Query → Gate-Blocker. Lifecycle-Exclusion-Failure → Gate-Blocker unabhängig von Count.

### Betroffene Tabellen

| Tabelle | Felder |
|---------|--------|
| Retrieval-Pipeline | externes System; Golden-Query-Ergebnisse |
| `document_chunks` | `id`, `is_searchable` (Eligibilitätsprüfung) |
| `documents` | `id`, `lifecycle_status` |

### Betroffene Gates

| Gate | Wirkung |
|------|---------|
| `m5b_release_decision` | `critical`, errors und Baseline-Delta > 5 % blockieren PREPARED |
| `m5b_start_gate` | Retrieval-Baseline-Release-Grade muss `true` vor Implementierungsstart |

### Report-Felder (finding-spezifisch)

| Feld | Typ | Pflicht |
|------|-----|---------|
| `query_id` | `string\|null` | nein |
| `baseline_score` | `number` | ja |
| `current_score` | `number` | ja |
| `drift_subtype` | `string` | ja |

Erlaubte Subtypes: `golden_query_quality_regression`, `retrieval_lifecycle_exclusion_failure`, `retrieval_baseline_missing`.

---

## Typ-Übersicht

| # | Typ | Prüft | Tabellen (Kern) | `critical` möglich |
|---|-----|-------|-----------------|-------------------|
| 1 | DOCUMENT_DRIFT | Strukturelle Dokumentkohärenz | `documents`, `document_versions`, `document_chunks` | nein |
| 2 | CHUNK_DRIFT | Chunk-Set-Integrität | `document_chunks`, `document_versions`, `documents` | ja |
| 3 | METADATA_DRIFT | Metadaten-Regression über Zeit | `document_versions`, `documents` | ja |
| 4 | LIFECYCLE_DRIFT | Lifecycle-Konsistenz DB + Retrieval | `documents`, `document_chunks` | ja |
| 5 | SOURCE_STATUS_DRIFT | Citation-Source-Status vs. Dokument-Lifecycle | `chat_citations`, `documents`, `chat_sessions` | ja |
| 6 | SEARCH_INDEX_DRIFT | Strukturelle Index-DB-Konsistenz | `document_chunks`, `documents`, Search-Index | ja |
| 7 | RETRIEVAL_DRIFT | Retrieval-Qualität vs. Golden-Baseline | Retrieval-Pipeline, `documents` | ja |

---

## Schema-Konsistenz-Hinweis

`drift_schema.json` (Root) kennt aktuell 5 Typen ohne `CHUNK_DRIFT` und `SEARCH_INDEX_DRIFT`. Autoritative Typdefinition: `schemas/drift_types.schema.json`. Bei PREPARED-Übergang muss `drift_schema.json` auf 7 Typen erweitert werden.
