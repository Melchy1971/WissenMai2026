# M5b Risk Matrix — Drift Detection

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; kein `PREPARED`, kein `GO`, keine Implementierung, siehe `reports/current/m5b_release_decision.json`).

Maschinenlesbare Matrix: `m5b_risk_matrix.json`.
Gate-Authority: `reports/current/m5b_gate_criteria.json`.

---

## Bewertungsschema

| Dimension | Werte |
|-----------|-------|
| Wahrscheinlichkeit | low / medium / high |
| Auswirkung | low / medium / high / critical |
| Gate-Auswirkung | none / blocking / escalation |

---

## R-01 — False Positive Drift

**ID:** R-01

**Ursache:** Detektor klassifiziert valide Datenbankzustände als Drift. Beispiel: Dokument korrekt archiviert, aber Archivierungszeitpunkt aus Batch-Import stammt → `lifecycle_timestamp_mismatch` fälschlicherweise ausgelöst. Oder: Count-Schwellenwert zu eng, Index-Latenz erzeugt kurzzeitige Diskrepanz.

**Wahrscheinlichkeit:** medium

**Auswirkung:** medium — False Positives erhöhen operativen Aufwand; Gate wird fälschlicherweise auf BLOCKED gesetzt; Vertrauen in Drift-Reports sinkt.

**Frühindikator:**
- Anzahl der `warning`-Findings bei sauberem Testzustand > 0 in TS-02-01
- Deterministischer Testlauf auf leerem Workspace liefert `drift_score > 0.0`

**Gegenmaßnahme:**
- Schwellenwerte pro Drift-Typ in `schemas/drift_types.schema.json` `x-gate-threshold` festlegen
- Gate-Tests (TS-07) prüfen explizit: sauberer State → `go_no_go=GO`
- Severity-Tabelle in `docs/m5b-drift-types.md` per Typ dokumentieren
- Subtypes mit Latenztoleranz kennzeichnen (z.B. `stale_index_entry` nur nach definierter Synchronisationszeit)

**Gate-Auswirkung:** blocking — wenn False Positive Rate nicht kontrollierbar, bleibt Implementation-Gate NO_GO

---

## R-02 — False Negative Drift

**ID:** R-02

**Ursache:** Detektor erkennt tatsächlich vorhandenen Drift nicht. Beispiel: `deleted_document_searchable` wird nicht gefunden, weil JOIN-Bedingung falsch formuliert ist. Oder: `chunk_workspace_mismatch` bleibt unerkannt bei bestimmten Workspace-ID-Typen.

**Wahrscheinlichkeit:** medium

**Auswirkung:** critical — Unerkannter Drift erlaubt inkonsistenten Systemzustand produktiv. Gate gibt fälschlicherweise GO. Sicherheitsrelevant bei lifecycle-kritischen Typen (gelöschte Dokumente abrufbar).

**Frühindikator:**
- Injektionstest (TS-03-01, TS-04-03) liefert `0 findings` statt `critical`
- Detector-Logik geht davon aus, dass bestimmte Felder immer gesetzt sind (Nullpointer-äquivalent)

**Gegenmaßnahme:**
- Alle Injektionstests (TS-02 bis TS-05) müssen exakte Finding-Counts liefern
- Postgres-Truth-Tests laufen gegen echte DB, keine Mocks
- Für jeden Drift-Typ: mindestens ein critical-Injektionstest als Gate-Bedingung

**Gate-Auswirkung:** escalation — bei Lifecycle-Typen sofortige Eskalation; kein GO ohne Nachweis

---

## R-03 — Performance bei großen Datenmengen

**ID:** R-03

**Ursache:** Drift-Scan ist workspace-scoped, aber bei großen Workspaces (> 10.000 Chunks, > 100.000 Index-Einträgen) steigt Laufzeit auf inakzeptable Werte. Full-Table-Scans ohne Indexnutzung oder N+1-Queries in Detector-Logik.

**Wahrscheinlichkeit:** high

**Auswirkung:** medium — Scans blockieren kein Gate direkt, aber machen Drift Detection operativ unbrauchbar wenn Laufzeit > konfigurierbares Timeout.

**Frühindikator:**
- TS-02 bis TS-04 laufen auf Workspace mit 1.000 Chunks; Laufzeit > 5 Sekunden
- EXPLAIN-Analyse zeigt Seq Scan auf `document_chunks` ohne `workspace_id`-Index

**Gegenmaßnahme:**
- Queries müssen `workspace_id` als ersten Filter verwenden (Voraussetzung: Index auf `workspace_id`)
- Performance-Baseline bei PREPARED messen; Obergrenze in `schemas/drift_types.schema.json` `x-gate-threshold` dokumentieren
- Known Limitation KL-M5-T-001 verweist auf Performance-Aspekte; muss vor GO geschlossen sein

**Gate-Auswirkung:** blocking — wenn Performance-Baseline fehlt, ist Retrieval-Drift-Test (TS-05) Gate-relevant aber nicht interpretierbar

---

## R-04 — Retrieval Regression

**ID:** R-04

**Ursache:** Drift-Detektor für `RETRIEVAL_DRIFT` setzt valide Baseline voraus. Fehlt die Baseline, kann kein Delta berechnet werden. Oder: Baseline wurde auf einer Retrieval-Konfiguration gemessen, die sich inzwischen geändert hat.

**Wahrscheinlichkeit:** high

**Auswirkung:** high — ohne Baseline ist RETRIEVAL_DRIFT-Erkennung blind; Gate bleibt NO_GO; Retrieval-Verschlechterungen werden nicht erkannt.

**Frühindikator:**
- `reports/current/retrieval_quality_baseline_report.json` fehlt oder hat `baseline_release_grade=false`
- TS-05-05: Baseline nicht verfügbar → `warning` statt auswertbarem Ergebnis

**Gegenmaßnahme:**
- Baseline muss vor RETRIEVAL_DRIFT-Gate-Tests existieren; explizite Precondition in TS-05
- Kein Test darf Baseline automatisch aktualisieren (Boundary-Regel FORBID-04 analog)
- Baseline-Änderungen erfordern explizite Freigabe, dokumentiert in `docs/m5b-preparation-boundary.md`

**Gate-Auswirkung:** blocking — IG-02 Limitations KL-M5-T-001 und KL-M5-T-002 adressieren diesen Pfad; muss vor GO geschlossen sein

---

## R-05 — Gate-Blockade durch optionale Reports

**ID:** R-05

**Ursache:** Ein Gate-Kriterium referenziert einen Report (z.B. `retrieval_quality_baseline_report.json`), der optionaler Natur ist oder zu spät generiert wird. Dadurch bleibt das Gate dauerhaft BLOCKED ohne klar behebbare Ursache.

**Wahrscheinlichkeit:** medium

**Auswirkung:** medium — verhindert GO ohne direkten Qualitätsbezug; Druck zur Umgehung des Gate-Modells.

**Frühindikator:**
- `m5b_gate_criteria.json` listet Kriterium als `passed=false`, aber zugehöriger Report ist nicht in `reports/current/` vorhanden
- Start-Gate SG-02 (Report Integrity) aktuell BLOCKED aus demselben Grund

**Gegenmaßnahme:**
- Gate-Kriterien müssen bei PREPARED-Übergang gegen tatsächlich vorhandene Reports geprüft werden
- Optionale Reports, die Gate-relevant werden, müssen als Required-Precondition in `m5b_gate_criteria.json` dokumentiert werden
- Kein Gate-Kriterium auf einen Report setzen, der erst durch Implementierung entstehen kann

**Gate-Auswirkung:** none — strukturelles Risiko, kein direkter Blocker; Gegenmaßnahme ist Gate-Kriterien-Review bei PREPARED

---

## R-06 — Cleanup-Verwechslung

**ID:** R-06

**Ursache:** Drift-Detector-Ausgabe enthält `remediation_hint` mit Wortlaut, der wie eine automatische Repair/Cleanup-Anweisung klingt. Downstream-Systeme oder Entwickler interpretieren den Hint als auslösbare Aktion.

**Wahrscheinlichkeit:** low

**Auswirkung:** high — versehentlich ausgeführte Cleanup-Aktionen (Löschen, Reindex, Archivierung) können produktive Daten beschädigen. Verletzt FORBID-03 aus `docs/m5b-preparation-boundary.md`.

**Frühindikator:**
- TS-06-04 schlägt fehl: `remediation_hint` enthält verbotene Strings (`auto-repair`, `reindex`, `delete`, `cleanup` als Verb)
- Report-Review zeigt Hinweise wie "Führe Reindex aus" oder "Lösche verwaiste Einträge"

**Gegenmaßnahme:**
- `remediation_hint` ist ausschließlich deskriptiv: beschreibt den Zustand, nicht die Aktion
- Verbotene Verben: `auto-repair`, `reindex`, `delete`, `cleanup`, `korrigiere`, `führe aus`
- TS-06-04 ist Gate-Test für Report-Schema; Failure blockiert Schema-Abnahme

**Gate-Auswirkung:** blocking — wenn TS-06-04 fehlschlägt, darf kein Drift-Report als Gate-relevant gewertet werden

---

## R-07 — Repair ohne Governance

**ID:** R-07

**Ursache:** Auf Basis von Drift-Findings wird manuell oder halbautomatisch repariert, ohne dass ein Governance-Prozess (Runbook, Gate-Freigabe, Audit) existiert. Betrifft besonders LIFECYCLE_DRIFT und CHUNK_DRIFT, wo Repair direkten DB-Eingriff bedeutet.

**Wahrscheinlichkeit:** medium

**Auswirkung:** critical — unkontrollierte Repair-Aktionen ohne Runbook verletzen KL-GOV-001 (`Mutierende Admin-Aktionen ohne Runbook und Gate-Freigabe gesperrt`). Audit-Trail fehlt.

**Frühindikator:**
- `remediation_hint` enthält Aktionsverben (siehe R-06)
- KL-GOV-001 ist noch high/deferred; keine explizite Abgrenzung für read-only Drift Checks

**Gegenmaßnahme:**
- M5b Drift Detection ist explizit read-only; keine Repair-Funktion in M5b-Scope
- KL-GOV-001 muss vor GO explizit für read-only Drift Checks als nicht-anwendbar deklariert werden (IG-04)
- Repair-Prozesse gehören in ein separates Governance-Dokument außerhalb M5b

**Gate-Auswirkung:** blocking — IG-04 ist explizit dieser Abgrenzung gewidmet; bleibt BLOCKED bis KL-GOV-001 adressiert ist

---

## Risiko-Übersicht

| ID | Titel | Wahrscheinlichkeit | Auswirkung | Gate-Auswirkung |
|----|-------|--------------------|------------|-----------------|
| R-01 | False Positive Drift | medium | medium | blocking |
| R-02 | False Negative Drift | medium | critical | escalation |
| R-03 | Performance bei großen Datenmengen | high | medium | blocking |
| R-04 | Retrieval Regression | high | high | blocking |
| R-05 | Gate-Blockade durch optionale Reports | medium | medium | none |
| R-06 | Cleanup-Verwechslung | low | high | blocking |
| R-07 | Repair ohne Governance | medium | critical | blocking |

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `docs/m5b-preparation-boundary.md` | Forbidden-Scope-Definition |
| `docs/m5b-drift-types.md` | Severity-Referenz |
| `docs/m5b-test-strategy.md` | Test-Gegenmaßnahmen |
| `schemas/drift_types.schema.json` | Schwellenwert-Definition |
| `reports/current/m5b_gate_criteria.json` | Gate-Abhängigkeiten |
| `reports/current/known_limitations.json` | KL-M5-T-001, KL-M5-T-002, KL-GOV-001 |
| `m5b_risk_matrix.json` | Maschinenlesbare Matrix |
