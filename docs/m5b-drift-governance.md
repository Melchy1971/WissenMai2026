# M5b Drift Findings — Governance

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; kein `PREPARED`, kein `GO`, keine Implementierung, siehe `reports/current/m5b_release_decision.json`).

Maschinenlesbares Schema: `drift_governance.schema.json`.
Gate-Authority: `reports/current/m5b_gate_criteria.json`.

---

## Kernprinzip

**Drift Detection erkennt. Sie repariert nicht.**

Jede Erkennung eines Drift Findings erzeugt einen Read-only-Report. Das Finding beschreibt eine Abweichung zwischen erwartetem und tatsächlichem Systemzustand. Die Entscheidung, ob und wie reagiert wird, liegt ausschließlich beim autorisierten Operator — nicht beim Detektor.

---

## Pflichtfelder eines Drift Findings

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `drift_id` | UUID | Eindeutiger Identifier des Findings; unveränderlich nach Erstellung |
| `drift_type` | string (enum) | Einer der 7 finalen Typen aus `schemas/drift_types.schema.json` |
| `severity` | string (enum) | `info`, `warning`, `error`, `critical` |
| `workspace_id` | UUID | Workspace-Scope des Findings; kein Cross-Workspace-Zugriff |
| `entity_type` | string | Betroffene Entität: `document`, `chunk`, `source`, `index_entry`, `metadata_record` |
| `entity_id` | UUID | Primärschlüssel der betroffenen Entität |
| `expected_state` | object | Erwarteter Systemzustand zum Erkennungszeitpunkt |
| `actual_state` | object | Tatsächlich vorgefundener Systemzustand |
| `remediation_hint` | string | Deskriptiver Hinweis; keine Aktionsanweisung (siehe Abschnitt Remediation) |
| `created_at` | ISO 8601 | Zeitstempel der Erkennung; unveränderlich |

Alle 10 Felder sind Pflicht. Ein Finding ohne vollständige Pflichtfelder wird nicht als Gate-relevant gewertet.

---

## Erlaubte Drift-Typen

Die finalen 7 Typen sind in `schemas/drift_types.schema.json` definiert:

| Typ | entity_type typischerweise |
|-----|---------------------------|
| `DOCUMENT_DRIFT` | `document` |
| `CHUNK_DRIFT` | `chunk` |
| `METADATA_DRIFT` | `metadata_record` |
| `LIFECYCLE_DRIFT` | `document`, `chunk` |
| `SOURCE_STATUS_DRIFT` | `source` |
| `SEARCH_INDEX_DRIFT` | `index_entry` |
| `RETRIEVAL_DRIFT` | `chunk`, `document` |

---

## Severity-Semantik

| Severity | Bedeutung | Gate-Effekt |
|----------|-----------|-------------|
| `info` | Abweichung bekannt, kein Handlungsbedarf | keiner |
| `warning` | Abweichung beobachtenswert; kein sofortiger Ausfall | Watch-Flag im Report |
| `error` | Abweichung erfordert Operator-Entscheidung | Gate NO_GO |
| `critical` | Abweichung hat unmittelbaren Integritätsbruch; z.B. gelöschtes Dokument suchbar | Gate NO_GO + Freeze-Flag |

Ein einzelnes `critical`-Finding friert den betroffenen Workspace-Scope für automatische Operationen ein, bis ein Operator die Situation bewertet hat.

---

## Remediation Hint — Regeln

`remediation_hint` ist ein **deskriptiver Text**, der den vorgefundenen Zustand und den erwarteten Zustand beschreibt. Er ist keine Anweisung.

**Erlaubt:**
- "Dokument `{entity_id}` hat `lifecycle_status=deleted`, Chunk `{chunk_id}` ist weiterhin `is_searchable=true`."
- "Index enthält Eintrag für Chunk `{entity_id}`, der nicht in `document_chunks` existiert."
- "Metadatenfeld `language` fehlt; erwartet: gesetzt bei `import_status=completed`."

**Verboten** — folgende Formulierungen dürfen in `remediation_hint` nicht vorkommen:

| Verbotenes Muster | Grund |
|-------------------|-------|
| Aktionsverb im Imperativ: `Führe aus`, `Starte`, `Lösche`, `Archiviere` | Impliziert automatische Ausführung |
| `auto-repair`, `auto-reindex`, `auto-fix` | Verletzt read-only-Constraint |
| `reindex`, `delete`, `cleanup` als Verb | Verletzt FORBID-01 bis FORBID-03 aus `docs/m5b-preparation-boundary.md` |
| `wird automatisch korrigiert` | Falschaussage; kein Repair in M5b |
| Referenz auf konkrete API-Endpunkte für mutierende Aktionen | Verletzt Governance-Boundary |

Ein Report-Schema-Test (`TS-06-04` in `test_matrix_m5b.json`) prüft maschinell, dass keine verbotenen Strings in `remediation_hint` vorkommen.

---

## Verbotene Aktionen des Detektors

| Aktion | Verboten | Begründung |
|--------|----------|------------|
| Lifecycle-Status eines Dokuments ändern | ja | Mutierende DB-Operation |
| `is_searchable` eines Chunks setzen | ja | Mutierende DB-Operation |
| Reindex eines Workspace oder Chunks auslösen | ja | Mutierende Systemoperation |
| Metadatenfelder schreiben oder überschreiben | ja | Mutierende DB-Operation |
| Finding automatisch schließen oder löschen | ja | Audit-Trail-Verlust |
| Repair-Funktion aufrufen | ja | Außerhalb M5b-Scope |
| Cross-Workspace-Abfragen ausführen | ja | Workspace-Isolation verletzt |
| `reports/current/` direkt mutieren (außer durch Gate-Validator) | ja | Gate-Integrität verletzt |

---

## Unveränderlichkeit von Findings

Ein erzeugtes Finding darf nach `created_at` nicht geändert werden. Das schließt ein:

- Keine Nachkorrektur von `expected_state` oder `actual_state`
- Kein Löschen von Findings ohne Operator-Entscheidung + Audit-Eintrag
- `drift_id` bleibt über Report-Generierungsläufe stabil, solange der Zustand unverändert ist

Wenn ein Finding durch einen späteren Scan nicht mehr reproduzierbar ist, wird es im neuen Report nicht mehr aufgeführt — das alte Finding bleibt im historischen Report erhalten.

---

## Workspace-Isolation

- Jedes Finding enthält `workspace_id`; Detektoren laufen workspace-scoped
- Ein Scan für Workspace A darf keine Daten aus Workspace B lesen
- Cross-Workspace-Aggregation ist verboten (Boundary-Regel, `docs/m5b-preparation-boundary.md`)
- `entity_id` ist immer im Kontext des jeweiligen `workspace_id` zu interpretieren

---

## Gate-Effekte

Findings beeinflussen Gate-Entscheidungen ausschließlich durch den Report-Mechanismus:

1. Detector erzeugt Findings → schreibt Report nach `reports/current/`
2. Gate-Validator liest Report, evaluiert Schwellenwerte aus `schemas/drift_types.schema.json` `x-gate-threshold`
3. Gate-Status wird aus Report abgeleitet; kein manueller Override erlaubt

| Finding-Situation | Gate-Ergebnis |
|-------------------|---------------|
| Kein Finding | GO |
| Nur `info` / `warning` | GO mit Watch-Flag |
| Mindestens ein `error` | NO_GO |
| Mindestens ein `critical` | NO_GO + Freeze |
| Error-Rate > Schwellenwert (typ-abhängig) | BLOCKED |

---

## Operator-Verantwortung

Findings lösen keine automatische Aktion aus. Der Operator entscheidet:

- ob ein Finding ein echter Defekt oder ein akzeptierter Zustand ist
- ob Repair ausgelöst wird (erfordert separates Governance-Gate außerhalb M5b)
- ob ein Finding als bekannte Ausnahme registriert wird

Repair-Prozesse sind außerhalb des M5b-Scope dokumentiert. M5b kennt kein Repair-Konzept.

---

## Risiko-Referenz

Governance-relevante Risiken aus `docs/m5b-risk-matrix.md`:

| Risiko | ID | Gate-Auswirkung |
|--------|----|-----------------|
| False Positive Drift | R-01 | blocking |
| Cleanup-Verwechslung | R-06 | blocking |
| Repair ohne Governance | R-07 | blocking |

R-07 ist der direkte Auslöser dieser Governance-Definition. KL-GOV-001 (`Mutierende Admin-Aktionen ohne Runbook und Gate-Freigabe gesperrt`) muss vor M5b GO explizit als nicht-anwendbar für read-only Drift Checks deklariert werden (IG-04).

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `drift_governance.schema.json` | Maschinenlesbares Schema |
| `schemas/drift_types.schema.json` | Autoritative Typdefinition |
| `docs/m5b-preparation-boundary.md` | Forbidden-Scope |
| `docs/m5b-drift-types.md` | Typ-Definitionen |
| `docs/m5b-test-strategy.md` | Test-Gegenmaßnahmen |
| `docs/m5b-risk-matrix.md` | Risiken R-01, R-06, R-07 |
| `reports/current/m5b_gate_criteria.json` | Gate-Authority |
| `reports/current/known_limitations.json` | KL-GOV-001 |
