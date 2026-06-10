# M5b Drift Detection — Testdatenstrategie

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; keine Implementierung erlaubt, siehe `reports/current/m5b_implementation_gate.json`).

Maschinenlesbares Schema: `drift_test_dataset_plan.json`.
Test-Matrix-Referenz: `test_matrix_m5b.json`.

---

## Grundsätze

1. **Reproduzierbarkeit:** Alle Testdatensätze sind deterministisch. Fixture-IDs sind statisch und versioniert. Kein zufällig generierter State ohne Seed.
2. **PostgreSQL als finale Wahrheit:** Kein Mock als finale Grundlage für gate-relevante Tests. Tests des Markers `m5b_truth` laufen gegen echte PostgreSQL-Instanz.
3. **Workspace-Isolation:** Jedes Szenario verwendet eine dedizierte, versionierte `workspace_id`. Kein Szenario teilt Workspace mit einem anderen Szenario.
4. **Teardown-Pflicht:** Jede Fixture hat obligatorisches Teardown nach Testabschluss. Kein Test hinterlässt persistente State-Änderungen in der Testdatenbank.
5. **Keine Produktionsdaten:** Testdatensätze enthalten ausschließlich synthetische Daten. Kein Export oder Abbild aus Produktionsdatenbanken.

---

## Szenarien

### Szenario 1: Korrekte Daten (Baseline / Happy Path)

**Zweck:** Verifiziert, dass ein fehlerfreier Workspace keine False Positives erzeugt.

**Zustand:**
- N Dokumente mit korrektem `lifecycle_status=active`, alle `is_searchable=true`
- Chunk-Anzahl entspricht `expected_chunk_count`
- Search Index ist synchron mit `document_chunks`
- Alle Quellen erreichbar, `source_status=active`
- Retrieval-Metriken innerhalb Baseline-Toleranz (delta ≤ 0.0)
- Alle Metadaten-Pflichtfelder gesetzt

**Erwartetes Ergebnis:** `total_drifts=0`; Gate = GO

**Fixture-Prefix:** `SC01_`
**Marker:** `m5b_truth`, `drift_detection`

---

### Szenario 2: Lifecycle Drift

**Zweck:** Verifiziert Erkennung eines gelöschten Dokuments, das weiterhin suchbar ist.

**Zustand:**
- 1 Dokument mit `lifecycle_status=deleted`
- Zugehörige Chunks haben `is_searchable=true` (absichtlich nicht korrigiert)
- Dokument ist im Search Index vorhanden

**Erwartetes Ergebnis:**
- `LIFECYCLE_DRIFT` Finding mit `severity=critical` (gelöschtes Dokument suchbar)
- Gate = NO_GO_FREEZE

**Fixture-Prefix:** `SC02_`
**Marker:** `m5b_truth`, `drift_detection`

**Variante 2a:** `lifecycle_status=archived`, Chunks `is_searchable=true`, nicht im Index → `severity=error`, Gate NO_GO

---

### Szenario 3: Source Status Drift

**Zweck:** Verifiziert Erkennung einer nicht erreichbaren Quelle mit Status `active`.

**Zustand:**
- 1 Quelle mit `source_status=active`
- Connectivity-Check schlägt fehl (simuliert durch Test-Stub; kein echter Netzwerk-Call)
- `last_successful_sync` ist älter als konfigurierter Timeout

**Erwartetes Ergebnis:**
- `SOURCE_STATUS_DRIFT` Finding mit `severity=error`
- Gate = NO_GO

**Fixture-Prefix:** `SC03_`
**Marker:** `m5b_truth`, `drift_detection`

**Hinweis:** Connectivity-Check-Stub ist kein Mock als finale Wahrheit; PostgreSQL-Zustand (`data_sources`) ist die autoritative Quelle. Der Stub simuliert ausschließlich die externe Netzwerkantwort.

---

### Szenario 4: Retrieval Drift

**Zweck:** Verifiziert Erkennung einer Retrieval-Qualitäts-Degradierung gegenüber Baseline.

**Zustand:**
- Baseline (`drift_baseline.json`) mit definierten Retrieval-Metriken gesetzt
- Workspace enthält absichtlich veraltete Chunks (Content nicht aktuell, aber noch indexiert)
- Retrieval-Testqueries ergeben metric_delta > 0.05

**Erwartetes Ergebnis:**
- `RETRIEVAL_DRIFT` Finding mit `severity=error`
- Gate = NO_GO

**Fixture-Prefix:** `SC04_`
**Marker:** `m5b_truth`, `drift_detection`

**Variante 4a:** metric_delta ≤ 0.05 → `severity=warning`; Gate GO_WITH_WATCH_FLAG (kein NO_GO)

---

### Szenario 5: Metadata Drift

**Zweck:** Verifiziert Erkennung fehlender Metadaten-Pflichtfelder.

**Zustand:**
- N Dokumente mit `import_status=completed`
- Pflichtfeld `language` fehlt bei allen Dokumenten
- Kein weiterer Drift

**Erwartetes Ergebnis:**
- `METADATA_DRIFT` Finding mit `severity=warning` (Pflichtfeld fehlt, kein Relevanz-Impact)
- Gate = GO_WITH_WATCH_FLAG (warning darf nicht blockieren)

**Fixture-Prefix:** `SC05_`
**Marker:** `m5b_truth`, `drift_detection`

**Variante 5a:** Fehlendes Feld beeinflusst Relevanz-Scoring → `severity=error`; Gate NO_GO

**Kritischer Test:** Dieser Szenario verifiziert die WARNING-Binding-Rule: Gate darf bei reinem `warning` nicht auf NO_GO wechseln.

---

### Szenario 6: Search Index Drift

**Zweck:** Verifiziert Erkennung von Phantom-Chunks im Search Index.

**Zustand:**
- Search Index enthält Chunk-Einträge für chunk_ids, die nicht in `document_chunks` existieren (Phantom-Chunks)
- `document_chunks` enthält Einträge ohne korrespondierenden Index-Eintrag (Missing-Chunks)

**Erwartetes Ergebnis:**
- `SEARCH_INDEX_DRIFT` Finding mit `severity=critical` (Phantom-Chunks)
- `SEARCH_INDEX_DRIFT` Finding mit `severity=error` (Missing-Chunks)
- Gate = NO_GO_FREEZE

**Fixture-Prefix:** `SC06_`
**Marker:** `m5b_truth`, `drift_detection`

**Variante 6a:** Nur Missing-Chunks, keine Phantoms → `severity=error`; Gate NO_GO

---

## Fixture-Struktur

Jede Fixture ist ein versioniertes Python-Objekt (TruthIds-Pattern aus `docs/m5b-test-strategy.md`):

```python
# Beispiel-Struktur (Planungsartefakt; kein implementierter Code)
SC01_WORKSPACE_ID = "11111111-1111-1111-1111-111111111111"
SC02_WORKSPACE_ID = "22222222-2222-2222-2222-222222222222"
# ... usw.; statische UUIDs, versioniert
```

**Teardown:** Jede Fixture-Klasse implementiert `teardown_fixture(workspace_id)`, das alle Testdaten aus der PostgreSQL-Instanz entfernt.

---

## Nicht-Scope

| Ausgeschlossen | Begründung |
|----------------|-----------|
| Mocks als finale Wahrheit für gate-relevante Tests | Verletzt PostgreSQL-Truth-Constraint |
| Produktionsdaten als Testbasis | Datenschutz; Reproduzierbarkeit nicht gegeben |
| Automatische Baseline-Updates aus Testergebnissen | Würde Baseline korrumpieren |
| Cross-Workspace-Fixtures (ein Fixture für mehrere Workspaces) | Workspace-Isolation |
| Tests, die `reports/current/` direkt mutieren | Verletzt PROHIBIT-08 |

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `drift_test_dataset_plan.json` | Maschinenlesbare Version |
| `test_matrix_m5b.json` | Marker, Suites, Gate-Relevanz |
| `drift_governance.schema.json` | PROHIBIT-Regeln |
| `drift_severity_matrix.json` | Erwartete Severities je Szenario |
| `docs/m5b-test-strategy.md` | TruthIds-Pattern, Fixture-Regeln |
| `reports/current/m5b_gate_criteria.json` | Gate-Authority |
