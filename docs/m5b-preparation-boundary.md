# M5b Preparation Boundary

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; kein `PREPARED`, kein `GO`, keine Implementierung, siehe `reports/current/m5b_release_decision.json`).

Dieses Dokument definiert ausschließlich, was im M5b-Vorbereitungsstatus erlaubt ist und was nicht. Es autorisiert keine Implementierung, keine Datenbankänderung, keine API-Route, keinen Hintergrundjob, keine Repair-Aktion und keine Adminoperation.

Solange `reports/current/m5a_final_readiness_review.json` nicht `READY_FOR_M5B` meldet, bleibt jedes M5b-Artefakt `DRAFT`.

---

## Gate-Statusmodell

| Status | Bedeutung |
|--------|-----------|
| `DRAFT` | Architekturplanung und Vorbereitungsdokumentation erlaubt. Kein Code, keine Implementierung. |
| `PREPARED` | Vorbereitung abgeschlossen, Implementierung weiterhin gesperrt. Erfordert M5a `READY_FOR_M5B`. |
| `GO` | Implementierung erlaubt. Erfordert explizites `GO` aus `reports/current/m5b_release_decision.json`. |

Aktueller Status: `DRAFT`.
Quelle: `reports/current/m5b_release_decision.json`, `reports/current/m5b_start_gate.json`.

---

## Erlaubt im DRAFT-Status

### 1. Architektur-Dokument

`docs/m5b-drift-architecture.md` darf fortgeführt, präzisiert und versioniert werden. Erlaubt: Scope-Definition, Detektorkonzepte, Datenmodell-Beschreibungen, Abgrenzung zu M5a. Nicht erlaubt: Implementierungsanker, die Migration, Code oder DB-Änderung voraussetzen.

### 2. Drift-Typen

Folgende Drift-Typen sind architektonisch definiert und dürfen dokumentiert werden:

| Drift-Typ | Primärquelle | Erkennungslogik (read-only) | Severity-Bereich |
|-----------|-------------|-----------------------------|-----------------|
| `document` | `documents`, `document_versions`, `document_chunks` | Strukturelle Konsistenz: current_version_id, Version-Sequenz, Chunk-Cardinality, Hash-Vertrag | `info` – `error` |
| `chunk` | `document_chunks` | Chunk-Integrität: Token-Verlust, Sequenzlücken, Waisen-Chunks ohne gültige Version | `warning` – `error` |
| `metadata` | Pflichtfelder auf Dokument/Chunk-Ebene | Feldvollständigkeit und Wertgültigkeit über Zeit | `warning` – `error` |
| `lifecycle` | `lifecycle_status` vs. Index-Präsenz | Archivierte/gelöschte Dokumente im Suchindex aktiv | `error` – `critical` |
| `source_status` | Source-Status vs. Import-Zustand | Inaktive/gelöschte Quellen mit aktiven Chunks | `warning` – `error` |
| `retrieval` | Retrieval-Benchmark vs. Golden Baseline | Metrik-Delta > 0,05 gegen Baseline; negative 7d-Bewegung | `warning` – `error` |

Severity-Werte: `info`, `warning`, `error`, `critical` (Definition: `docs/m5b-drift-architecture.md`).

### 3. Report-Schema

```json
{
  "report_schema_version": 1,
  "report_type": "drift_detection",
  "report_name": "m5b_drift_report",
  "generated_at": "<iso8601>",
  "generated_by": "<detector_id>",
  "environment": "<local|staging|production>",
  "workspace_id": "<uuid>",
  "status": "ok | watch | blocked",
  "drift_score": 0.0,
  "counters": {
    "total_findings": 0,
    "by_severity": {
      "info": 0,
      "warning": 0,
      "error": 0,
      "critical": 0
    },
    "by_drift_type": {
      "document": 0,
      "chunk": 0,
      "metadata": 0,
      "lifecycle": 0,
      "source_status": 0,
      "retrieval": 0
    }
  },
  "findings": [
    {
      "drift_id": "<stable_id>",
      "drift_type": "<document|chunk|metadata|lifecycle|source_status|retrieval>",
      "drift_subtype": "<rule_id>",
      "workspace_id": "<uuid>",
      "severity": "<info|warning|error|critical>",
      "entity": {
        "document_id": "<uuid|null>",
        "version_id": "<uuid|null>",
        "chunk_id": "<uuid|null>"
      },
      "expected_state": "<machine_readable>",
      "observed_state": "<machine_readable>",
      "detection_strategy": "<rule_or_query_family>",
      "remediation_hint": "<human_readable; kein automatischer Repair>",
      "escalation": "<operational_action_by_severity>"
    }
  ]
}
```

Felddefinitionen: `docs/m5b-drift-architecture.md` (Common Model).

### 4. Gate-Kriterien

| Kriterium | Schwelle | Wirkung |
|-----------|----------|---------|
| `document_drift_errors` | = 0 | Blockiert M5b Gate wenn > 0 |
| `lifecycle_exclusion_violations` | = 0 | Blockiert M5b Gate wenn > 0 |
| `chunk_integrity_errors` | = 0 | Blockiert M5b Gate wenn > 0 |
| `critical_findings` | = 0 | Freeze mutierender Operationen; sofortige Eskalation |
| `retrieval_baseline_delta` | ≤ 0,05 | Warnung bei negativer 7d-Bewegung; Blocker bei > 0,05 |
| `source_status_violations` | = 0 | Blockiert M5b Gate wenn > 0 |
| `metadata_completeness_failures` | = 0 | Blockiert M5b Gate wenn > 0 |

Gate-Quelle: `reports/current/m5b_release_decision.json`.
M5b Gate `PASS` erfordert alle Fehlercounts = 0 und keine `critical`-Findings.

### 5. Risiken

| ID | Risiko | Eintrittswahrscheinlichkeit | Auswirkung | Gegenmaßnahme |
|----|--------|----------------------------|------------|---------------|
| R-M5B-01 | Lifecycle-Drift deckt gelöschte Dokumente im Index auf: Datenschutzrelevanz | mittel | hoch | `critical`-Severity; Freeze mutierender Operationen sofort bei Fund |
| R-M5B-02 | Retrieval-Baseline-Delta überschreitet Schwelle nach Reindex: Suchqualität degradiert unbemerkt | mittel | mittel | Baseline-Vergleich vor und nach jedem Reindex-Event; separates Gate |
| R-M5B-03 | Drift-Score-Berechnung läuft workspace-übergreifend: falsche Aggregation | niedrig | hoch | Workspace-Scoping als Pflichtfeld; Cross-Workspace-Queries verboten |
| R-M5B-04 | Detector läuft ohne M5a PASS: ungültige Baseline | hoch (aktuell) | mittel | Implementierung gesperrt bis M5a READY_FOR_M5B |
| R-M5B-05 | Repair wird durch Hint-Text impliziert: unbeabsichtigte Aktion | niedrig | mittel | `remediation_hint` darf keine automatische Aktion auslösen; explizite Freigabe erforderlich |
| R-M5B-06 | Chunk-Orphan-Erkennung erzeugt falsche Positive bei laufendem Import | mittel | niedrig | Detector nur außerhalb aktiver Import-Windows ausführen |

### 6. Teststrategie

**Erlaubt im DRAFT-Status:** Testplanung, Testspezifikation, Testdaten-Design. Keine Testimplementierung, keine Testausführung gegen Produktionsdaten.

| Testart | Scope | Ziel |
|---------|-------|------|
| Unit-Tests (geplant) | Einzelne Drift-Regel pro Typ | Korrekte Severity-Zuordnung je Condition |
| Fixture-Tests (geplant) | Synthetische Workspace-Snapshots | Deterministisches Report-Output bei bekanntem Drift-Zustand |
| Boundary-Tests (geplant) | Schwellenwerte je Gate-Kriterium | Gate reagiert korrekt auf Grenzwerte |
| Integration-Tests (geplant) | Detector + Report-Schema + Gate | End-to-End-Lauf ohne Mutation; nur lesende DB-Queries |
| Regression-Tests (geplant) | Alle Drift-Typen gegen Golden-Fixtures | Keine Regression nach Architekturänderungen |

Teststrategie-Prinzipien:
- Alle Tests laufen read-only gegen Fixtures oder Testschemas
- Kein Test darf Repair, Reindex oder Cleanup auslösen
- Baseline-Verifikation: Retrieval-Benchmark gegen Golden-Set vor Implementierungsstart
- Truth-Block: `drift_detection` muss grün sein vor Freigabe

### 7. Nicht-Scope

Folgendes ist explizit ausgeschlossen. Ein Fund außerhalb des DRAFT-Vorbereitungsstatus gegen diese Punkte ist ein Boundary-Verstoß.

| Ausgeschlossen | Begründung |
|----------------|------------|
| Drift Detection Code (Detector-Implementierung) | Erfordert M5b `GO`; aktuell `BLOCKED` |
| Repair Code (Reindex, Snapshot-Repair, Queue-Recovery) | Separates Repair-Gate erforderlich; nicht durch M5b Prep autorisiert |
| Cleanup Code | Kein Cleanup ohne explizite Freigabe; mutierender Eingriff |
| Neue Adminaktionen (Web-Admin, API-Endpunkte) | Kein neues UI oder Endpoint im DRAFT-Status |
| Automatische Korrekturen | Repair ist explizit ausgelöst, nie automatisch (Quelle: `docs/drift.md`) |
| Datenbankmigrationen | Keine Schema-Änderung im DRAFT-Status |
| Hintergrundjobs (Worker-Registrierung) | Kein Job-Scheduling vor `GO` |
| Cross-Workspace-Queries | Workspace-Scoping ist Pflicht; keine workspace-übergreifenden Detector-Läufe |

---

## Boundary-Verletzung

Ein Boundary-Verstoß liegt vor, wenn:

- Code gegen einen der Nicht-Scope-Punkte committed wird, solange `m5b_release_decision.json` nicht `GO` meldet
- Ein `remediation_hint` eine automatische Aktion impliziert
- Ein Detector-Lauf Daten mutiert
- Ein Admin-Endpunkt für Drift-Operationen registriert wird ohne `GO`
- Repair-Logik in Detektoren eingebaut wird

Eskalation bei Verstoß: Sofortige Reversion; keine manuelle Override-Erlaubnis (`manual_override_allowed: false` laut `m5b_release_decision.json`).

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `reports/current/m5b_release_decision.json` | Gate-Authority; aktueller Status BLOCKED |
| `reports/current/m5b_start_gate.json` | Startzustand; DRAFT-Entscheidung |
| `docs/m5b-drift-architecture.md` | Architektur-Referenz; DRAFT |
| `docs/drift.md` | Drift-Typen, Schwellen, Repair-Steuerung |
| `reports/current/m5a_final_readiness_review.json` | M5a-Status; PREPARED-Voraussetzung |
