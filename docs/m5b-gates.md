# M5b Gate-Kriterien

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; kein `PREPARED`, kein `GO`, keine Implementierung, siehe `reports/current/m5b_release_decision.json`).

Maschinenlesbare Kriterien: `reports/current/m5b_gate_criteria.json`.
Gate-Authority: `reports/current/m5b_release_decision.json`.

---

## Gate-Modell

M5b hat drei Statusebenen:

| Status | Bedeutung | Voraussetzung |
|--------|-----------|---------------|
| `DRAFT` | Nur Architekturplanung erlaubt | Standardzustand |
| `PREPARED` | Vorbereitung abgeschlossen; Implementierung weiterhin gesperrt | Start-Gate PASS |
| `GO` | Implementierung erlaubt | Implementation-Gate PASS |

Ein Slice-PASS aus M5a reicht nicht für `PREPARED`. M5a muss über `reports/current/m5a_final_readiness_review.json` `READY_FOR_M5B` melden.

---

## M5b Start-Gate

**ID:** `m5b_start_gate`
**Ziel:** M5b PREPARED
**Aktueller Status: BLOCKED** (2 von 6 Kriterien erfüllt)

### Kriterien

#### SG-01 — M5a READY_FOR_M5B

| Attribut | Wert |
|----------|------|
| Quelle | `reports/current/m5a_final_readiness_review.json` |
| Bedingunq | `status = READY_FOR_M5B` |
| Aktuell | BLOCKED |
| Blocker | ja |

M5a Final Readiness Review muss `READY_FOR_M5B` melden. Dieser Status wird erst gesetzt, wenn alle M5a Slice-Gates (`duplicate_detector_gate`, `metadata_detector_gate`, `lifecycle_integrity_gate`, `source_status_integrity_gate`, `orphan_detector_gate`) und `report_integrity_v2` PASS sind.

#### SG-02 — Report Integrity PASS

| Attribut | Wert |
|----------|------|
| Quelle | `reports/current/report_integrity_v2.json` |
| Bedingung | `status = PASS` |
| Aktuell | BLOCKED |
| Blocker | ja |

Report Integrity verifiziert die Konsistenz aller Gate-Reports untereinander. PASS ist Voraussetzung dafür, dass M5b-Planungsartefakte als verifiziert gelten können.

#### SG-03 — M5b Preparation Boundary vorhanden

| Attribut | Wert |
|----------|------|
| Quelle | `docs/m5b-preparation-boundary.md` |
| Bedingung | Datei existiert; definiert Erlaubt/Verboten-Scope |
| Aktuell | PASS |
| Blocker | ja |

Definiert 7 erlaubte Vorbereitungsschritte und 5 verbotene Aktionen. Boundary-Dokument ist vorhanden.

#### SG-04 — Drift Types definiert

| Attribut | Wert |
|----------|------|
| Quelle | `docs/m5b-drift-types.md` |
| Bedingung | Datei existiert; alle 7 Drift-Typen definiert; Schema-Referenz vorhanden |
| Aktuell | PASS |
| Blocker | ja |

Finale 7 Drift-Typen: `DOCUMENT_DRIFT`, `CHUNK_DRIFT`, `METADATA_DRIFT`, `LIFECYCLE_DRIFT`, `SOURCE_STATUS_DRIFT`, `SEARCH_INDEX_DRIFT`, `RETRIEVAL_DRIFT`. Autoritative Typdefinition in `schemas/drift_types.schema.json`.

#### SG-05 — Drift Report Schema vorhanden

| Attribut | Wert |
|----------|------|
| Quellen | `drift_schema.json`, `schemas/drift_types.schema.json` |
| Bedingung | Beide Dateien existieren |
| Aktuell | PASS (mit offenem Folgeschritt) |
| Blocker | ja |

Beide Schemata existieren. `drift_schema.json` kennt aktuell 5 Typen; `schemas/drift_types.schema.json` ist autoritative Typdefinition mit 7 Typen. `drift_schema.json` muss beim PREPARED-Übergang auf 7 Typen erweitert werden.

#### SG-06 — Documentation Truth PASS

| Attribut | Wert |
|----------|------|
| Quelle | `reports/current/documentation_truth_lint.json` |
| Bedingung | `status = PASS` |
| Aktuell | PASS (2026-06-10T08:51:22Z) |
| Blocker | ja |

Documentation Truth Lint prüft Konsistenz und Vollständigkeit der Dokumentationsbasis.

### Start-Gate Blocker (aktuell)

| ID | Kriterium | Quelle |
|----|-----------|--------|
| SG-BLOCKER-01 | M5a READY_FOR_M5B | `reports/current/m5a_final_readiness_review.json`: BLOCKED |
| SG-BLOCKER-02 | Report Integrity | `reports/current/report_integrity_v2.json`: BLOCKED |

---

## M5b Implementation-Gate

**ID:** `m5b_implementation_gate`
**Ziel:** M5b GO
**Aktueller Status: BLOCKED** (0 von 4 Kriterien erfüllt)

Das Implementation-Gate ist sequenziell: es kann nicht PASS sein, solange das Start-Gate nicht GO ist.

Report `reports/current/m5b_implementation_gate.json` existiert noch nicht. Er wird erzeugt, wenn alle Kriterien erfüllt sind.

### Kriterien

#### IG-01 — Start-Gate GO

| Attribut | Wert |
|----------|------|
| Quelle | `reports/current/m5b_start_gate.json` |
| Bedingung | `decision.go_no_go = GO` und `status = PASS` |
| Aktuell | DRAFT / NO_GO |
| Blocker | ja |

Sequenzielle Precondition. Implementation-Gate setzt voraus, dass das Start-Gate vollständig PASS ist.

#### IG-02 — Keine kritischen M5B_IMPL Limitations

| Attribut | Wert |
|----------|------|
| Quelle | `reports/current/known_limitations.json` |
| Bedingung | Keine open high-severity Limitation mit Category `spätere M5b Implementierung` |
| Aktuell | 2 offene Blocker |
| Blocker | ja |

Offene Limitations:

| ID | Titel | Severity | Status |
|----|-------|----------|--------|
| KL-M5-T-001 | M5 Entropy-/Drift-Truth-Failures blockieren Slice-Start | high | open |
| KL-M5-T-002 | Drei Pflicht-Artefakte pro M5-Slice fehlen vor Slice-Start | high | open |

Beide müssen vor Implementierungsstart geschlossen sein.

#### IG-03 — Teststrategie vorhanden

| Attribut | Wert |
|----------|------|
| Quelle erwartet | `docs/m5b-test-strategy.md` |
| Bedingung | Eigenständiges Teststrategiedokument mit Testplänen für alle 7 Drift-Typen existiert |
| Aktuell | Fehlt |
| Blocker | ja |

In `docs/m5b-preparation-boundary.md` (Abschnitt 6) ist eine Teststrategie-Skizze vorhanden. Für das Implementation-Gate wird ein eigenständiges Dokument erwartet, das Unit-, Fixture-, Boundary-, Integration- und Regressions-Tests für alle 7 Drift-Typen spezifiziert.

#### IG-04 — Keine offenen Governance-Blocker für Drift Checks

| Attribut | Wert |
|----------|------|
| Quelle | `reports/current/known_limitations.json` |
| Bedingung | KL-GOV-001 geschlossen oder explizit als nicht-blockierend für read-only Drift Checks deklariert |
| Aktuell | KL-GOV-001: high / deferred |
| Blocker | ja |

KL-GOV-001 (`Mutierende Admin-Aktionen ohne Runbook und Gate-Freigabe gesperrt`) ist high/deferred. Drift Checks sind read-only und führen keine Admin-Aktionen oder mutierende Operationen aus. Trotzdem muss die Abgrenzung explizit dokumentiert sein, bevor Implementierung startet, damit keine Governance-Überschneidung entsteht.

### Implementation-Gate Blocker (aktuell)

| ID | Kriterium | Detail |
|----|-----------|--------|
| IG-BLOCKER-01 | IG-01 Start-Gate GO | Start-Gate ist DRAFT/NO_GO |
| IG-BLOCKER-02 | IG-02 Keine M5B_IMPL Limitations | KL-M5-T-001 und KL-M5-T-002 offen |
| IG-BLOCKER-03 | IG-03 Teststrategie | `docs/m5b-test-strategy.md` fehlt |
| IG-BLOCKER-04 | IG-04 Governance | KL-GOV-001 nicht abgegrenzt |

---

## M5b Alpha Gate

**ID:** `m5b_alpha_gate`
**Ziel:** Nachweis, dass alle Pflicht-Komponenten der M5b Drift Detection implementiert und getestet sind.
**Aktueller Status: PASS** (2026-06-11)
**Score:** 100/100 (Schwelle: 90)

### Ergebnis

| Komponente | ID | Datei | Tests | Status |
|---|---|---|---|---|
| Persistence Layer | M5B-PERSIST | `backend/app/models/drift.py` | 20/20 | PASS |
| Drift Run Engine | M5B-ENGINE | `backend/app/services/drift_run_engine.py` | 21/21 | PASS |
| Document Drift Detector | M5B-DOC | `backend/app/services/drift/document_drift_detector.py` | 20/20 | PASS |
| Metadata Drift Detector | M5B-META | `backend/app/services/drift/metadata_drift_detector.py` | 18/18 | PASS |
| Lifecycle Drift Detector | M5B-LIFECYCLE | `backend/app/services/drift/lifecycle_drift_detector.py` | 16/16 | PASS |
| Source Status Drift Detector | M5B-SOURCE | `backend/app/services/source_status_integrity_detector.py` | 11/11 | PASS |

Gesamt: 106/106 Tests gruen. Score-Formel: (6/6) × 100 = 100.

### Constraints (unveraendert)

- Cleanup-Aktionen: NO_GO (PROHIBIT-02)
- Repair-Aktionen: NO_GO (PROHIBIT-06)
- M5c: NOT_STARTED, BLOCKED bis M5b Beta PASS

Quelle: `reports/current/m5b_alpha_gate.json`

---

## Pfad zu PREPARED

1. M5a alle Slice-Gates auf PASS
2. `report_integrity_v2.json` → PASS
3. `m5a_final_readiness_review.json` → READY_FOR_M5B
4. `drift_schema.json` auf 7 Typen erweitern
5. Start-Gate neu generieren → PASS / GO

## Pfad zu GO

1. Start-Gate PASS/GO
2. KL-M5-T-001 schliessen
3. KL-M5-T-002 schliessen
4. `docs/m5b-test-strategy.md` erstellen
5. KL-GOV-001 fuer read-only Drift Checks explizit abgrenzen
6. `reports/current/m5b_implementation_gate.json` generieren → PASS / GO

---

## Zusammenfassung

| Gate | Kriterien gesamt | Bestanden | Geblockt | Status |
|------|-----------------|-----------|----------|--------|
| Start-Gate | 6 | 2 | 4 | BLOCKED |
| Implementation-Gate | 4 | 0 | 4 | BLOCKED |
| Alpha Gate | 6 | 6 | 0 | PASS |

M5b Alpha Gate: PASS (2026-06-11). Start-Gate und Implementation-Gate bleiben BLOCKED durch externe Preconditions (M5a READY_FOR_M5B, Report Integrity).
Naechster Meilenstein: M5a `READY_FOR_M5B` + Report Integrity `PASS` → Start-Gate `PASS`.

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `reports/current/m5b_gate_criteria.json` | Maschinenlesbare Kriterien |
| `reports/current/m5b_release_decision.json` | Gate-Authority |
| `reports/current/m5b_start_gate.json` | Start-Gate Zustand |
| `reports/current/m5a_final_readiness_review.json` | SG-01 Quelle |
| `reports/current/report_integrity_v2.json` | SG-02 Quelle |
| `reports/current/known_limitations.json` | IG-02 und IG-04 Quelle |
| `docs/m5b-preparation-boundary.md` | SG-03 Quelle |
| `docs/m5b-drift-types.md` | SG-04 Quelle |
| `drift_schema.json` | SG-05 Quelle |
| `schemas/drift_types.schema.json` | SG-05 Quelle |
| `reports/current/documentation_truth_lint.json` | SG-06 Quelle |
