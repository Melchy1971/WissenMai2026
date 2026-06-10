# M5b Teststrategie — Drift Detection

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; kein `PREPARED`, kein `GO`, keine Implementierung, siehe `reports/current/m5b_release_decision.json`).

Maschinenlesbare Testmatrix: `test_matrix_m5b.json`.
Gate-Authority: `reports/current/m5b_gate_criteria.json`.

---

## Leitprinzipien

- Keine Mocks für finale Truth Tests. PostgreSQL ist die einzige Wahrheit für Gate-relevante Ergebnisse.
- Alle Drift-Prüfungen sind read-only. Kein Test darf Repair, Reindex, Cleanup oder mutierende Datenbankoperationen auslösen.
- Fixtures sind workspace-scoped und deterministic. Jeder Test erzeugt seinen eigenen Workspace-Scope mit stabilen IDs.
- Gate-relevante Tests schreiben Reports nach `reports/current/`. Kein manueller Status ohne Reportreferenz.
- Testdaten werden über `postgres_truth`-Fixtures gesät, nicht aus Produktionsdaten gelesen.
- Ein Slice-Testlauf belegt nur seinen Scope. Kein lokaler Lauf ersetzt Gate-Entscheidungen.

---

## Pytest-Marker

Folgende Marker sind für M5b zu registrieren (Ergänzung zu `pytest.ini`):

| Marker | Bedeutung | Gate-Relevant |
|--------|-----------|---------------|
| `m5b_truth` | M5b Drift Detection postgres_truth Tests; blockiert M5b Gate | ja |
| `m5b_unit` | Schnelle Unit Tests ohne DB; non-blocking | nein |
| `m5b_schema` | Report-Schema-Validierungstests; non-blocking | nein |
| `drift_detection` | Sub-Kategorie; immer mit `m5b_truth` kombiniert | — |

---

## 1. Unit Tests pro Drift Detector

### Scope

Jeder der 7 Drift-Typen bekommt eine dedizierte Unit-Test-Datei. Unit Tests prüfen Severity-Zuordnung, Subtype-Logik und Report-Feldkorrektheit gegen synthetische Python-Objekte. Kein Datenbankzugriff.

### Testdateien (geplant)

| Datei | Drift-Typ |
|-------|-----------|
| `backend/tests/test_m5b_document_drift_unit.py` | DOCUMENT_DRIFT |
| `backend/tests/test_m5b_chunk_drift_unit.py` | CHUNK_DRIFT |
| `backend/tests/test_m5b_metadata_drift_unit.py` | METADATA_DRIFT |
| `backend/tests/test_m5b_lifecycle_drift_unit.py` | LIFECYCLE_DRIFT |
| `backend/tests/test_m5b_source_status_drift_unit.py` | SOURCE_STATUS_DRIFT |
| `backend/tests/test_m5b_search_index_drift_unit.py` | SEARCH_INDEX_DRIFT |
| `backend/tests/test_m5b_retrieval_drift_unit.py` | RETRIEVAL_DRIFT |

### Prüfinhalte pro Unit Test

- Severity-Zuordnung für jeden erlaubten Subtype (positiv und negativ)
- `critical`-Pfad korrekt ausgelöst bei Cross-Workspace- oder Lifecycle-Exposure-Bedingungen
- `remediation_hint` enthält keine automatische Repair-Anweisung
- `drift_subtype` ist ein erlaubter Wert aus `schemas/drift_types.schema.json`
- Report-Felder sind vollständig für Pflichtfelder

### Marker

```python
pytestmark = [pytest.mark.m5b_unit]
```

---

## 2. Integration Tests mit PostgreSQL

### Scope

Jeder Drift-Typ wird gegen eine real laufende PostgreSQL-Instanz getestet. Testdaten werden durch Fixtures in einem isolierten Workspace gesät. Alle Prüfungen sind read-only.

### Testdatei

`backend/tests/postgres_truth/test_m5b_drift_truth.py`

### Fixture-Strategie

- Jeder Test-Case erhält einen eigenen Workspace mit stabilen deterministischen IDs (nach `TruthIds`-Muster)
- Fixtures erzeugen validen Ausgangszustand, dann gezielten Drift-Zustand durch direkte SQL-Mutationen
- Nach dem Test werden Testdaten via Fixture-Teardown entfernt; kein Produktionszustand wird berührt
- Kein Fixture darf Repair-Logic enthalten

### Prüfinhalte

- Detector findet genau die injizierten Findings; keine False Positives auf sauberem State
- Report-Output enthält korrekte Counts für `findings_by_drift_type` und `findings_by_severity`
- `drift_score` ist 0.0 bei sauberem Workspace
- `workspace_id` ist korrekt gesetzt; kein Cross-Workspace-Leak

### Marker

```python
pytestmark = [pytest.mark.m5b_truth, pytest.mark.postgres_truth, pytest.mark.drift_detection]
```

---

## 3. Lifecycle Drift Tests

### Scope

Prüft, dass LIFECYCLE_DRIFT-Detector den Zustand zwischen `documents.lifecycle_status`, `document_chunks.is_searchable` und Retrieval-Sichtbarkeit korrekt bewertet.

### Testdatei

`backend/tests/postgres_truth/test_m5b_lifecycle_drift_truth.py`

### Prüfinhalte

| Test-Case | Injizierter Zustand | Erwartetes Finding |
|-----------|--------------------|--------------------|
| `deleted_document_searchable` | `lifecycle_status=deleted`, Chunk `is_searchable=true` | `critical` |
| `archived_document_searchable` | `lifecycle_status=archived`, Chunk `is_searchable=true` | `error` |
| `active_document_not_searchable` | `lifecycle_status=active`, Chunk `is_searchable=false`, Import abgeschlossen | `error` |
| `lifecycle_timestamp_mismatch` | `archived_at` gesetzt, `lifecycle_status=active` | `warning` |
| `missing_lifecycle_audit_evidence` | Status nicht-aktiv, kein Timestamp | `warning` |
| Sauberer Zustand | Alle Lifecycle-Constraints erfüllt | Keine Findings |

### Regel

Kein Test darf `lifecycle_status`, `is_searchable` oder `archived_at` reparieren. Detector ist read-only.

### Marker

```python
pytestmark = [pytest.mark.m5b_truth, pytest.mark.postgres_truth, pytest.mark.drift_detection]
```

---

## 4. Search Index Drift Tests

### Scope

Prüft strukturelle Konsistenz zwischen Suchindex und `document_chunks`/`documents`. Stale entries, missing entries und lifecycle-excluded content im Index.

### Testdatei

`backend/tests/postgres_truth/test_m5b_search_index_drift_truth.py`

### Prüfinhalte

| Test-Case | Injizierter Zustand | Erwartetes Finding |
|-----------|--------------------|--------------------|
| `stale_index_entry` | Chunk in Index, nicht mehr in DB | `warning` |
| `missing_index_entry` | Eligible aktiver Chunk in DB, fehlt im Index | `error` |
| `lifecycle_excluded_deleted_in_index` | Gelöschter Chunk im Index abrufbar | `critical` |
| `lifecycle_excluded_archived_in_index` | Archivierter Chunk im Index aktiv | `error` |
| `index_count_discrepancy` | Index-Count weicht > 5 % von DB-Count ab | `warning` |
| Sauberer Zustand | Index und DB synchron | Keine Findings |

### Besonderheit

Search-Index-Tests erfordern eine laufende Search-Index-Komponente oder einen Test-Double für die Index-Abfrage. Test-Doubles dürfen für die Index-Abfrage verwendet werden; PostgreSQL bleibt die Wahrheit für DB-Counts. Finale Gate-relevante Tests laufen gegen echten Index.

### Marker

```python
pytestmark = [pytest.mark.m5b_truth, pytest.mark.postgres_truth, pytest.mark.drift_detection]
```

---

## 5. Retrieval Drift Tests

### Scope

Golden-Query-Benchmark gegen Retrieval-Pipeline. Metrik-Vergleich gegen genehmigte Baseline. Lifecycle-Ausschlussregeln im Retrieval.

### Testdateien

| Datei | Scope |
|-------|-------|
| `backend/tests/retrieval_benchmark/test_m5b_retrieval_drift.py` | Golden-Query-Metriken |
| `backend/tests/postgres_truth/test_m5b_retrieval_lifecycle_truth.py` | Lifecycle-Ausschluss im Retrieval |

### Prüfinhalte — Qualität

- Precision@K, Recall@K, MRR gegen `retrieval_quality_baseline_report.json`
- `score_delta` bleibt ≤ 0.05
- Negative 7d-Bewegung erzeugt `warning`; Delta > 0.25 auf einer Query erzeugt `error`

### Prüfinhalte — Lifecycle-Ausschluss (postgres_truth)

| Test-Case | Injizierter Zustand | Erwartetes Finding |
|-----------|--------------------|--------------------|
| Gelöschtes Dokument in Retrieval-Ergebnis | `lifecycle_status=deleted` | `critical` |
| Archiviertes Dokument in Default-Retrieval | `lifecycle_status=archived` | `error` |
| Aktives Dokument nicht in Retrieval | Eligible, korrekte Lifecycle | `error` |

### Baseline-Regel

Die Baseline in `reports/current/retrieval_quality_baseline_report.json` muss `baseline_release_grade=true` sein, bevor Retrieval Drift Tests Gate-relevant werden. Kein Test aktualisiert die Baseline automatisch.

### Marker

```python
# Qualitätstests
pytestmark = [pytest.mark.m5b_truth, pytest.mark.slow_truth]

# Lifecycle-Ausschluss
pytestmark = [pytest.mark.m5b_truth, pytest.mark.postgres_truth, pytest.mark.drift_detection]
```

---

## 6. Report Schema Tests

### Scope

Validiert den JSON-Output aller Drift-Detektoren gegen `drift_schema.json` und `schemas/drift_types.schema.json`. Non-blocking; kein PostgreSQL erforderlich.

### Testdatei

`backend/tests/test_m5b_drift_report_schema.py`

### Prüfinhalte

- Jeder erzeugte Report ist valides JSON gegen `drift_schema.json`
- Alle `finding_type`-Werte sind in `schemas/drift_types.schema.json` registriert
- Alle `drift_subtype`-Werte sind erlaubte Subtypes des jeweiligen `drift_type`
- Pflichtfelder `drift_id`, `workspace_id`, `severity`, `expected_state`, `observed_state`, `remediation_hint` sind gesetzt
- `remediation_hint` enthält keine der verbotenen Strings: `"automatisch"`, `"auto-repair"`, `"reindex"`, `"delete"`, `"cleanup"` als Aktion
- Leerer Workspace erzeugt Report mit `total_findings=0` und `status=ok`
- Report mit `critical`-Finding hat `status=blocked`

### Schema-Gap-Test

Bis `drift_schema.json` auf 7 Typen erweitert ist: Test prüft, dass `CHUNK_DRIFT` und `SEARCH_INDEX_DRIFT` in `schemas/drift_types.schema.json` registriert sind, und flaggt fehlende Registrierung in `drift_schema.json` als `warning` (nicht `error`).

### Marker

```python
pytestmark = [pytest.mark.m5b_schema]
```

---

## 7. Gate Tests

### Scope

Prüft, dass Gate-Logik korrekt auf Detector-Output reagiert: Schwellenwerte, Blocking-Conditions, `go_no_go`-Entscheidung.

### Testdatei

`backend/tests/test_m5b_gate_logic.py`

### Prüfinhalte

| Test-Case | Input | Erwartetes Gate-Ergebnis |
|-----------|-------|--------------------------|
| Kein Finding | `total_findings=0`, alle Counts 0 | `go_no_go=GO` |
| Ein `error` | DOCUMENT_DRIFT error | `go_no_go=NO_GO` |
| Ein `critical` | LIFECYCLE_DRIFT critical | `go_no_go=NO_GO`, `freeze=true` |
| Error-Rate > Schwelle | DOCUMENT_DRIFT errors > 5 % aktiver Dokumente | Gate BLOCKED |
| Nur `warning` und `info` | Keine errors, keine critical | `go_no_go=GO` mit `watch` |
| `critical` CHUNK_DRIFT workspace_mismatch | Cross-Workspace-Finding | Sofortige Eskalation |
| Missing Index Entry > 0 | SEARCH_INDEX_DRIFT missing_index_entry | Gate BLOCKED |
| Retrieval Baseline-Delta > 0.05 | RETRIEVAL_DRIFT | Gate BLOCKED |

### Marker

```python
pytestmark = [pytest.mark.m5b_unit]
```

---

## Testdatenstrategie

- Fixtures erzeugen minimalen validen Workspace-State, dann gezielten Drift
- Stabile IDs nach `TruthIds`-Muster (`hashlib.sha1` + Namespace)
- Kein Test liest Produktionsdaten
- Kein Test schreibt in `reports/current/` direkt; Reports werden durch Gate-Validator erzeugt
- Testdaten-Teardown ist Pflicht; kein Test hinterlässt Residualzustand

## Testdatenbeispiel — Lifecycle Drift Fixture

```python
def seed_deleted_searchable_chunk(session, workspace_id, document_id, chunk_id):
    """Injiziert: Dokument deleted, Chunk is_searchable=true → critical LIFECYCLE_DRIFT"""
    session.execute(text(
        "UPDATE documents SET lifecycle_status='deleted', deleted_at=now() "
        "WHERE id=:doc_id AND workspace_id=:ws_id"
    ), {"doc_id": document_id, "ws_id": workspace_id})
    session.execute(text(
        "UPDATE document_chunks SET is_searchable=true WHERE id=:chunk_id"
    ), {"chunk_id": chunk_id})
    session.commit()
    # Kein Repair in diesem Fixture
```

---

## Nicht-Scope

| Ausgeschlossen | Begründung |
|----------------|------------|
| Tests, die Repair auslösen | Repair ist außerhalb M5b Scope |
| Tests gegen Produktionsdaten | Isolation ist Pflicht |
| Automatische Baseline-Updates | Baseline-Update erfordert explizite Freigabe |
| Tests, die `reports/current/` direkt mutieren | Reports werden durch Gate-Validator erzeugt |
| Cross-Workspace-Aggregationsqueries | Verboten laut `docs/m5b-preparation-boundary.md` |

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `schemas/drift_types.schema.json` | Autoritative Typdefinition |
| `drift_schema.json` | Report-Envelope-Schema |
| `docs/m5b-drift-types.md` | Drift-Typ-Definitionen |
| `docs/m5b-preparation-boundary.md` | Boundary-Regeln |
| `reports/current/m5b_gate_criteria.json` | Gate-Kriterien |
| `backend/tests/postgres_truth/conftest.py` | Fixture-Basis |
| `pytest.ini` | Marker-Registry (zu erweitern) |
