# M5a Lifecycle Integrity Detector - Slice-Planung

Statusquellen:
- reports/current/m5a_duplicate_detector_gate.json
- reports/current/m5a_metadata_detector_gate.json
- reports/current/data_quality_report.json

Voraussetzungen (erfuellt):
- Duplicate Detector Gate: PASS (GO), laut reports/current/m5a_duplicate_detector_gate.json
- Metadata Detector Gate: PASS (GO), laut reports/current/m5a_metadata_detector_gate.json
- Data Quality Run: ausfuehrbar, letzter Lauf status=completed, laut reports/current/data_quality_report.json

Aktueller Stand: Detector, Unit-Tests und PostgreSQL-Truth sind implementiert; Gate ist `PASS` (siehe reports/current/m5a_lifecycle_integrity_gate.json).

---

## Ziel

Der Lifecycle Integrity Detector soll inkonsistente Lifecycle-Zustaende finden, die Search/Retrieval und Citation-Status verletzen.

Pflichtpruefungen fuer diesen Slice:
1. archived Dokumente nicht in Search
2. deleted Dokumente nicht in Search
3. active Dokumente auffindbar
4. archived/deleted nicht in neuem Retrieval
5. Lifecycle-Status konsistent mit source_status

---

## Technischer Bezug (Ist-System)

- Search filtert auf aktive Dokumente: backend/app/repositories/search.py
- Lifecycle-Transitionen synchronisieren Chunk-Searchability und Citation source_status:
  backend/app/services/documents/lifecycle_service.py
- Truth-Referenzen fuer Search/Retrieval/Lifecycle:
  backend/tests/postgres_truth/test_m4c_lifecycle_retrieval_truth.py
  backend/tests/postgres_truth/test_m4_truth_flows.py

---

## Scope

### In Scope

- Neuer Detector: LifecycleIntegrityDetector
- Findings fuer Lifecycle/Search/Retrieval-Inkonsistenzen
- Integration in DataQualityRunner
- Unit- und PostgreSQL-Truth-Tests
- Gate-Generator fuer m5a_lifecycle_integrity_gate

### Out of Scope

- Automatische Reparatur (nur read-only Detection)
- Lifecycle-Mutationen im Detector
- Index-Rebuild-Aktionen im Detector

---

## Detector-Regeln (fachlich)

Empfohlene Finding-Typen aus bestehendem Enum:
- INVALID_LIFECYCLE
- INVALID_SOURCE_STATUS
- RETRIEVAL_RISK

Regeln:

- LI-1: archived Dokument darf nicht in Search-Rueckgabe erscheinen.
  - violation -> RETRIEVAL_RISK (error)
- LI-2: deleted Dokument darf nicht in Search-Rueckgabe erscheinen.
  - violation -> RETRIEVAL_RISK (error)
- LI-3: active Dokument mit searchable Chunk muss in Search auffindbar sein.
  - violation -> RETRIEVAL_RISK (warning)
- LI-4: archived/deleted Chunks duerfen nicht im neuen Retrieval-Set (SearchService/RAG retrieval) erscheinen.
  - violation -> INVALID_LIFECYCLE (error)
- LI-5: chat_citations.source_status muss dem aktuellen documents.lifecycle_status entsprechen
  (mit missing als erlaubtem Sonderfall fuer nicht mehr vorhandenes Dokument).
  - violation -> INVALID_SOURCE_STATUS (warning)

---

## SQL/Abfrage-Strategie (DB-agnostisch)

- Search-Visibility-Checks ueber Join document_chunks -> documents mit is_searchable und lifecycle_status.
- Source-Status-Check ueber Join chat_citations -> documents:
  - drift, wenn citation.source_status != document.lifecycle_status
  - Ausnahme: document fehlt und citation.source_status == missing

---

## Gate-Kriterien (m5a_lifecycle_integrity_gate)

Schwelle: Score >= 90 = GO.

| ID | Kriterium | Erwartung |
|---|---|---|
| C1 | archived Dokumente nicht in Search | 0 Verstosse |
| C2 | deleted Dokumente nicht in Search | 0 Verstosse |
| C3 | active Dokumente auffindbar | >= 1 aktiver Treffer in Seed-Setup |
| C4 | archived/deleted nicht in neuem Retrieval | 0 archived/deleted Chunks im Retrieval-Set |
| C5 | source_status konsistent zu lifecycle_status | 0 Drift-Faelle |
| C6 | Workspace Isolation | kein Cross-Workspace Leak |
| C7 | Keine Dokumentmutation durch Detector | before/after Snapshot identisch |
| C8 | Finding-Shape Runner-kompatibel | Pflichtfelder vorhanden, kein run_id im Finding |
| C9 | Runner integriert LifecycleIntegrityDetector | Run status=completed, Findings verarbeitbar |
| C10 | PostgreSQL Truth fuer Search/Retrieval/Lifecycle ausgefuehrt | keine FAIL/ERROR im Gate-Lauf |

Gate-Output:
- reports/current/m5a_lifecycle_integrity_gate.json (aktueller Stand: PASS)

---

## Risiken und Mitigation

| Risiko | Schwere | Mitigation |
|---|---|---|
| Falsch-positive LI-3 bei unvollstaendigem Index | mittel | Seed-Setup mit validem active searchable chunk, klare Preconditions |
| Unterschied Search API vs Retrieval Pipeline | mittel | C4 mit identischem Query-Term und Vergleich der Chunk-IDs |
| Citation-Drift bei race conditions | niedrig | Test ueber LifecycleService-Transitions + refresh/expire Session |
