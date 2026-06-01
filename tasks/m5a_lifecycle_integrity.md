# Tasks: M5a Lifecycle Integrity Detector Slice

Statusquellen:
- reports/current/m5a_duplicate_detector_gate.json (PASS)
- reports/current/m5a_metadata_detector_gate.json (PASS)
- reports/current/data_quality_report.json (status=completed)

Slice-Gate (neu): reports/current/m5a_lifecycle_integrity_gate.json

Implementierung erst nach Slice-Start-Gate. Dieses Dokument ist das Planungsartefakt.

---

## Task-Liste

### T-01 - LifecycleIntegrityDetector implementieren

Datei:
- backend/app/services/lifecycle_integrity_detector.py

Regeln:
- LI-1 archived Dokumente nicht in Search
- LI-2 deleted Dokumente nicht in Search
- LI-3 active Dokumente auffindbar
- LI-4 archived/deleted nicht im neuen Retrieval
- LI-5 lifecycle_status konsistent mit citation source_status

Ausgabe:
- list[dict] im Runner-kompatiblen Finding-Format
- read-only, workspace-scoped, keine Mutationen

---

### T-02 - Unit-Tests fuer LifecycleIntegrityDetector

Datei:
- backend/tests/test_lifecycle_integrity_detector.py

Coverage:
- archived in searchable index -> violation
- deleted in searchable index -> violation
- active nicht auffindbar -> violation
- source_status drift wird erkannt
- clean state erzeugt 0 Findings
- keine Dokumentmutation
- workspace isolation

---

### T-03 - Runner-Integration

Datei:
- backend/app/services/data_quality_runner.py

Aufgabe:
- LifecycleIntegrityDetector in detector pipeline einhaengen
- Findings in score/reports aufnehmen

---

### T-04 - PostgreSQL Truth-Tests

Datei:
- backend/tests/postgres_truth/test_m5a_lifecycle_integrity_truth.py

Muss pruefen:
- archived/deleted nicht in Search API
- active auffindbar
- SearchService und Retrieval nutzen nur active Chunks
- source_status folgt lifecycle_status nach archive/delete/restore

---

### T-05 - Gate-Generator erstellen

Datei:
- scripts/generate_m5a_lifecycle_integrity_gate.py

Output:
- reports/current/m5a_lifecycle_integrity_gate.json

Gate-Logik:
- PASS wenn Score >= 90
- BLOCKED bei NOT_RUN/fehlenden Inputs/invalid JSON

---

### T-06 - Dokumentation und Status aktualisieren

Nach Gate-PASS:
- docs/data-quality.md (Slice ergaenzen)
- Entwicklung.md (aktuellen Slice-Stand ergaenzen)
- masterplan.md nur ueber generierten Statusblock aktualisieren
- documentation_truth_lint auf PASS

---

## Sequenz

T-01 -> T-02 + T-04 -> T-03 -> T-05 -> Gate-Lauf -> T-06

---

## Gate-Kriterien (verbindlich)

| ID | Kriterium | Erwartung |
|---|---|---|
| C1 | archived Dokumente nicht in Search | 0 Verstosse |
| C2 | deleted Dokumente nicht in Search | 0 Verstosse |
| C3 | active Dokumente auffindbar | >= 1 aktiver Treffer |
| C4 | archived/deleted nicht im neuen Retrieval | 0 archived/deleted Retrieval-Treffer |
| C5 | lifecycle_status konsistent mit source_status | 0 Drift |
| C6 | Workspace Isolation | kein Cross-Workspace Leak |
| C7 | Keine Dokumentmutation | before/after identisch |
| C8 | Finding-Shape kompatibel | Pflichtfelder vorhanden |
| C9 | Runner-Integration | completed run, Findings persistierbar |
| C10 | PostgreSQL Truth-Nachweis | relevante tests PASS |

Score-Formel:
- Score = (passed / collected) * 100
- GO ab >= 90
