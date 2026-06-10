# M5b Drift Detection — Severity Model

Stand: 2026-06-10

Status: `DRAFT` (Planungsartefakt; keine Implementierung erlaubt, siehe `reports/current/m5b_implementation_gate.json`).

Maschinenlesbares Schema: `drift_severity_matrix.json`.
Governance: `docs/m5b-drift-governance.md`, `drift_governance.schema.json`.
Typ-Autorität: `schemas/drift_types.schema.json`.

---

## Severity Levels

| Level | Code | Gate-Auswirkung | Automatische Blockade |
|-------|------|-----------------|----------------------|
| `info` | 0 | keiner | nein |
| `warning` | 1 | Watch-Flag im Report | **nein** — darf nicht automatisch blockieren |
| `error` | 2 | Gate NO_GO | ja |
| `critical` | 3 | Gate NO_GO + Freeze des Workspace-Scope | ja |

### Binding Rules

**CRITICAL:** Ein einzelnes `critical`-Finding blockiert das Implementation Gate und friert den betroffenen Workspace-Scope für automatische Operationen ein, bis ein Operator die Situation bewertet und dokumentiert hat.

**WARNING:** `warning`-Findings dürfen unter keinen Umständen automatisch eine Gate-Blockade oder einen Freeze auslösen. Sie erzeugen einen Watch-Flag im Report; die Auswertung obliegt dem Operator.

**ERROR:** Ein oder mehrere `error`-Findings setzen den Gate-Status auf NO_GO. Kein einzelnes `error` löst einen Workspace-Freeze aus.

---

## Standard-Severity und Eskalationsregeln je Drift-Typ

### DOCUMENT_DRIFT

Beschreibung: Inhaltliche oder strukturelle Abweichung auf Dokumentebene (Content-Hash, Feldstruktur, Referenzintegrität).

| Szenario | Severity | Auslöser |
|----------|----------|----------|
| Standard | `warning` | Content-Hash weicht vom erwarteten ab |
| Eskalation → error | `error` | Dokument ist `import_status=completed`; Content-Hash-Abweichung nach Indexierungsabschluss |
| Eskalation → critical | `critical` | Dokument hat `lifecycle_status=deleted`; Content-Hash zeigt modifizierten Inhalt, der weiterhin suchbar ist |

**Gate-Auswirkung:**
- `warning`: Watch-Flag, kein NO_GO
- `error`: NO_GO
- `critical`: NO_GO + Freeze

---

### CHUNK_DRIFT

Beschreibung: Abweichung zwischen erwarteter und tatsächlicher Chunk-Menge oder -Zustand innerhalb eines Dokuments.

| Szenario | Severity | Auslöser |
|----------|----------|----------|
| Standard | `warning` | Chunk-Anzahl weicht von `expected_chunk_count` ab; innerhalb Toleranz |
| Eskalation → error | `error` | Chunk-Anzahl-Divergenz > 0 nach Ablauf des Validierungsfensters (typ. 10 min nach Import) |
| Eskalation → critical | `critical` | Orphaned Chunks im Search Index vorhanden, die nicht in `document_chunks` existieren (Phantom-Chunks) |

**Gate-Auswirkung:**
- `warning`: Watch-Flag
- `error`: NO_GO
- `critical`: NO_GO + Freeze

---

### METADATA_DRIFT

Beschreibung: Fehlende oder inkonsistente Metadatenfelder gegenüber dem erwarteten Schema.

| Szenario | Severity | Auslöser |
|----------|----------|----------|
| Standard | `info` | Optionale Metadatenfelder fehlen; kein Einfluss auf Indexierung |
| Eskalation → warning | `warning` | Pflichtfelder fehlen bei `import_status=completed` |
| Eskalation → error | `error` | Fehlende Metadaten beeinflussen Relevanz-Scoring oder Filterlogik in der Suche |

**Gate-Auswirkung:**
- `info`: kein Gate-Effekt
- `warning`: Watch-Flag; kein NO_GO
- `error`: NO_GO

**Hinweis:** `METADATA_DRIFT` kann grundsätzlich kein `critical` erreichen. Metadaten sind beschreibend, nicht integritätskritisch für Zugriffskontrolle oder Datenschutz.

---

### LIFECYCLE_DRIFT

Beschreibung: `lifecycle_status` eines Dokuments oder Chunks stimmt nicht mit dem tatsächlichen Suchbarkeitszustand (`is_searchable`, Index-Präsenz) überein.

| Szenario | Severity | Auslöser |
|----------|----------|----------|
| Standard | `error` | `lifecycle_status=archived` oder `lifecycle_status=deleted`; Entität ist weiterhin `is_searchable=true` |
| Eskalation → critical | `critical` | `lifecycle_status=deleted`; Dokument oder Chunk ist im Search Index auffindbar (Datenschutz/Compliance-Verletzung) |

**Gate-Auswirkung:**
- `error`: NO_GO (Standard-Severity ist bereits error)
- `critical`: NO_GO + Freeze

**Begründung für error als Standard:** Ein archiviertes Dokument, das suchbar bleibt, ist kein Watch-Fall — es ist ein Integritätsbruch. `warning` wäre hier semantisch falsch.

---

### SOURCE_STATUS_DRIFT

Beschreibung: Registrierter Status einer Datenquelle (`source_status`) weicht vom tatsächlich messbaren Zustand ab.

| Szenario | Severity | Auslöser |
|----------|----------|----------|
| Standard | `warning` | Quelle antwortet nicht; `source_status=active`; innerhalb des Retry-Fensters |
| Eskalation → error | `error` | Quelle ist für > konfigurierten Timeout nicht erreichbar; `source_status=active` bleibt unverändert |
| Eskalation → critical | `critical` | Quelle liefert nachweislich korrumpierte Daten; `source_status=active`; Chunks wurden bereits importiert |

**Gate-Auswirkung:**
- `warning`: Watch-Flag
- `error`: NO_GO
- `critical`: NO_GO + Freeze

---

### SEARCH_INDEX_DRIFT

Beschreibung: Abweichung zwischen Index-Inhalt und DB-Stand (`document_chunks`-Tabelle) auf workspace-scope Ebene.

| Szenario | Severity | Auslöser |
|----------|----------|----------|
| Standard | `error` | Index enthält Einträge, die nicht in DB existieren, oder umgekehrt; Divergenz > 0 |
| Eskalation → critical | `critical` | Divergenz wächst über aufeinander folgende Runs (≥ 2 Runs mit zunehmendem Delta) oder absoluter Delta > konfigurierter Schwelle |

**Gate-Auswirkung:**
- `error`: NO_GO (Standard-Severity ist error)
- `critical`: NO_GO + Freeze

**Begründung für error als Standard:** Jede Abweichung zwischen Index und DB degradiert die Retrieval-Qualität direkt und messbar. `warning` wäre eine Falschbewertung des Zustands.

---

### RETRIEVAL_DRIFT

Beschreibung: Retrieval-Qualität weicht von der definierten Golden-Baseline ab (metrisch).

| Szenario | Severity | Auslöser |
|----------|----------|----------|
| Standard | `warning` | Baseline-Delta ≤ 0.05; einmaliger Ausreißer möglich |
| Eskalation → error | `error` | Baseline-Delta > 0.05 in einem einzelnen Run |
| Eskalation → critical | `critical` | Baseline-Delta > 0.15 **oder** ≥ 3 aufeinander folgende Runs mit negativem Delta unabhängig von Absolutwert |

**Gate-Auswirkung:**
- `warning`: Watch-Flag; kein NO_GO
- `error`: NO_GO
- `critical`: NO_GO + Freeze

**Hinweis:** `RETRIEVAL_DRIFT` beginnt bei `warning`, weil Metrik-Rauschen bei einzelnen Runs legitim ist. Die Eskalation ist explizit an Schwellenwerte und Persistenz gebunden, nicht an absolute Einzelwerte.

---

## Aggregations-Logik für Gate-Entscheidung

Der Gate-Validator aggregiert alle Findings eines Reports nach folgendem Vorrang:

1. Mindestens ein `critical` → Gate = NO_GO + Freeze; kein weiteres Kriterium nötig
2. Mindestens ein `error` (und kein `critical`) → Gate = NO_GO
3. Nur `warning` und/oder `info` → Gate = GO mit Watch-Flag (falls warnings vorhanden)
4. Kein Finding → Gate = GO

Die Aggregation ist workspace-scoped. Cross-Workspace-Aggregation ist verboten.

---

## Severity-Verteilung nach Drift-Typ (Übersicht)

| Drift-Typ | info | warning | error | critical |
|-----------|------|---------|-------|---------|
| DOCUMENT_DRIFT | — | Standard | Eskalation | Eskalation |
| CHUNK_DRIFT | — | Standard | Eskalation | Eskalation |
| METADATA_DRIFT | Standard | Eskalation | Eskalation | nicht möglich |
| LIFECYCLE_DRIFT | — | — | Standard | Eskalation |
| SOURCE_STATUS_DRIFT | — | Standard | Eskalation | Eskalation |
| SEARCH_INDEX_DRIFT | — | — | Standard | Eskalation |
| RETRIEVAL_DRIFT | — | Standard | Eskalation | Eskalation |

---

## Quellen

| Quelle | Rolle |
|--------|-------|
| `drift_severity_matrix.json` | Maschinenlesbares Schema |
| `drift_governance.schema.json` | Governance-Constraints, Gate-Effect-Definitionen |
| `docs/m5b-drift-governance.md` | Governance-Regeln |
| `schemas/drift_types.schema.json` | Autoritative Typdefinition |
| `reports/current/m5b_gate_criteria.json` | Gate-Authority |
| `docs/m5b-risk-matrix.md` | R-01 (False Positive), R-02 (False Negative) |
