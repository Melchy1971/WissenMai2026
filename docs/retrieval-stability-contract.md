# Retrieval Stability Contract

Stand: 2026-05-13

## Ziel

RAG- und Retrieval-Verhalten duerfen sich nicht unkontrolliert aendern. Jede Aenderung an Search, Chat Retrieval, Citation Mapping oder insufficient-context-Policy muss versioniert, regressionsgeprueft und gegen Golden Queries bewertet werden.

Dieser Vertrag stabilisiert die Grenze zwischen:

- `GET /api/v1/search/chunks`
- Chat-/RAG-Orchestrierung
- Context Builder
- Citation Mapper
- Lifecycle-Filterung
- Retrieval Quality Benchmark

Verwandte Dokumente:

- `docs/retrieval.md`
- `docs/rag.md`
- `docs/chat-rag-api-contract.md`
- `docs/m5-retrieval-quality-baseline.md`
- `docs/feature-governance-model.md`
- `docs/architecture-change-governance.md`

---

## 1. Stabilitaetsbereiche

### 1.1 Citation Schema

Das Citation-Schema ist ein stabiler Vertrag. Eine Citation muss fuer neue Chat-Antworten mindestens maschinenlesbar enthalten:

- `chunk_id`
- `document_id`
- `document_title`
- `source_anchor`
- `quote_preview`
- `source_status`

Historische Citations muessen weiterhin lesbar bleiben, auch wenn das referenzierte Dokument spaeter archiviert, geloescht oder vermisst ist.

Stabilitaetsregel: Entfernen, Umbenennen, Typaendern oder Semantikwechsel eines Citation-Feldes ist ein Breaking Retrieval Change.

### 1.2 source_anchor

`source_anchor` ist der stabile Quellenanker fuer Search-Treffer und Citations.

Stabile Felder:

- `type`
- `page`
- `paragraph`
- `char_start`
- `char_end`

Stabilitaetsregel: `source_anchor` darf additiv erweitert werden. Nicht-additive Aenderungen an Feldnamen, Nullability, Typen, Bedeutung oder Normalisierung sind Breaking Retrieval Changes.

### 1.3 source_status

`source_status` beschreibt den aktuellen Live-Zustand einer historischen Citation-Quelle.

Stabile Werte:

- `active`
- `archived`
- `deleted`
- `missing`

Stabilitaetsregel: Neue Werte sind nur additiv erlaubt, wenn alte Werte unveraendert bleiben und Clients unbekannte Werte tolerieren koennen. Umbenennungen oder Bedeutungswechsel sind Breaking Retrieval Changes.

### 1.4 Retrieval Ranking

Die Ranking-Baseline fuer Search ist Teil des Vertrags:

1. `rank DESC`
2. `document.created_at DESC`
3. `chunk_index ASC`
4. `chunk_id ASC`

`rank` basiert im aktuellen Vertrag auf PostgreSQL FTS `ts_rank`.

Stabilitaetsregel: Jede Aenderung an Query Parsing, Ranking-Funktion, Gewichtung, Tie-Breakern, Re-Ranking oder semantischem Ranking ist mindestens ein regressionpflichtiger Retrieval Change. Wenn bestehende Golden Queries andere Top-K-Ergebnisse erwarten muessen, ist die Aenderung breaking oder braucht eine neue Vertragsversion.

### 1.5 Lifecycle Filtering

Neue Search- und Chat-Retrieval-Ergebnisse duerfen nur aktive, aktuelle und workspace-zulaessige Inhalte verwenden.

Stabile Ausschlussregeln:

- keine archivierten Dokumente in neuen Retrieval-Treffern
- keine soft-geloeschten Dokumente in neuen Retrieval-Treffern
- keine alten Dokumentversionen
- keine `pending`- oder `failed`-Imports
- keine Chunks ausserhalb des aktuellen Workspaces

Historische Citations sind davon getrennt: Sie bleiben sichtbar und werden nicht rueckwirkend geloescht.

Stabilitaetsregel: Jede Aenderung an Lifecycle-Filterung, `is_searchable`, Reindex-Synchronisierung oder historischer Citation-Sichtbarkeit ist ein Breaking Retrieval Change, wenn sie bestehende Sichtbarkeitsgarantien veraendert.

### 1.6 insufficient_context Verhalten

Bei unzureichendem Kontext muss Chat/RAG deterministisch keinen fachlichen Antwortinhalt ausgeben.

Stabile Erwartungen:

- kein Halluzinations-Fallback
- keine Assistant-Antwort ohne ausreichende Retrieval-Grundlage
- keine erfolgreiche Antwort ohne gueltige Citation
- maschinenlesbarer Status oder Fehlerpfad fuer insufficient context
- Golden Query fuer No-Answer-Verhalten bleibt Teil des Benchmarks

Stabilitaetsregel: Jede Aenderung an Schwellwerten, Kontextauswahl, Antwortpolicy oder Fehler-/Statussemantik fuer insufficient context ist regressionpflichtig. Wenn Clients andere Kontrollfluesse sehen, ist sie breaking.

### 1.7 Search vs Chat Konsistenz

Search und Chat Retrieval muessen auf derselben fachlichen Sichtbarkeit beruhen.

Stabile Konsistenzregeln:

- Chat darf keine Chunks zitieren, die Search fuer dieselbe Query und denselben Workspace wegen Lifecycle oder Isolation ausschliesst.
- Chat-Citations muessen auf tatsaechlich verwendete Retrieval-Chunks zurueckfuehrbar sein.
- Search- und Chat-Retrieval muessen dieselben Workspace-Grenzen respektieren.
- Unterschiedliche Ranking- oder Kontextlogik ist erlaubt, muss aber dokumentiert und benchmarked sein.

Stabilitaetsregel: Jede Divergenz zwischen Search und Chat muss im Retrieval Stability Assessment dokumentiert werden. Unbegruendete Divergenz ist ein Gate-Blocker.

---

## 2. Versionierungsstrategie

### 2.1 Vertragsversionen

Retrieval-Verhalten wird ueber eine explizite Vertragsversion beschrieben.

Aktuelle Basisversion:

```text
retrieval-contract-v1
```

Diese Version umfasst:

- Citation Schema v1
- source_anchor v1
- source_status v1
- PostgreSQL FTS Ranking Baseline v1
- Lifecycle Filtering v1
- insufficient_context Policy v1
- Search-vs-Chat Consistency v1
- Golden Dataset `m5-retrieval-golden-v1`

### 2.2 Versionierungsebenen

| Ebene | Versionierung | Beispiel |
|---|---|---|
| API-Vertrag | Endpoint/API-Version oder dokumentierte Contract-Version | `GET /api/v1/search/chunks` |
| Retrieval-Vertrag | `retrieval-contract-vN` | `retrieval-contract-v2` |
| Golden Dataset | `m5-retrieval-golden-vN` | `m5-retrieval-golden-v2` |
| Citation Schema | `citation-schema-vN` | neues Pflichtfeld |
| Ranking Policy | `ranking-policy-vN` | FTS plus gewichtete Titel |
| insufficient_context Policy | `insufficient-context-policy-vN` | neuer Schwellenwert oder Statuscode |

### 2.3 Additive Aenderungen

Additive Aenderungen duerfen innerhalb derselben Major-Vertragsversion bleiben, wenn:

- bestehende Felder unveraendert bleiben
- bestehende Golden Queries weiter bestehen
- bestehende Schwellen nicht still gesenkt werden
- Clients neue Felder ignorieren koennen
- Search-vs-Chat-Konsistenz erhalten bleibt

### 2.4 Breaking Aenderungen

Breaking Retrieval Changes brauchen eine neue Vertragsversion. Die alte Version muss entweder weiter unterstuetzt oder bewusst mit Migrationsplan abgeloest werden.

Pflicht fuer neue Version:

- neue oder aktualisierte Contract-Dokumentation
- aktualisiertes Golden Dataset
- Regression Report gegen alte und neue Golden Queries
- Migrationsnotiz fuer Clients und interne Services
- Gate-Policy, wenn die Aenderung architecture-changing ist

---

## 3. Breaking-Change-Regeln

Ein Breaking Retrieval Change ist jede Aenderung, die bestehendes Search-, Chat-, Citation- oder RAG-Verhalten ohne explizite Vertragsversion veraendert.

Breaking sind insbesondere:

| Bereich | Breaking Change |
|---|---|
| Citation Schema | Feld entfernen, umbenennen, Typ aendern, Required/Nullable aendern, Snapshot-Semantik aendern |
| source_anchor | Feld entfernen, Positionssemantik aendern, Normalisierung aendern, Anker ungenauer machen |
| source_status | Werte umbenennen, Bedeutung aendern, historische Status nicht mehr aufloesen |
| Retrieval Ranking | Ranking-Funktion, Gewichtung, Tie-Breaker oder Top-K-Verhalten so aendern, dass Golden Queries andere Erwartungen brauchen |
| Lifecycle Filtering | archivierte/geloeschte/alte/nicht importierte Inhalte neu sichtbar machen oder aktive Inhalte unbegruendet ausschliessen |
| insufficient_context | No-Answer-Policy, Schwellen, Statuscode, Antwortformat oder Citation-Pflicht aendern |
| Search vs Chat | Chat zitiert Inhalte, die Search fachlich ausschliesst, oder nutzt andere Isolation ohne dokumentierten Vertrag |

Nicht breaking, aber regressionpflichtig:

- neue optionale Response-Felder
- zusaetzliche Golden Queries
- Performance-Optimierung ohne Ranking- oder Sichtbarkeitsaenderung
- interne Refactorings ohne Verhaltenseffekt
- klar dokumentierte Erweiterung, die alte Clients ignorieren koennen

---

## 4. Regression Detection

Regression Detection ist fuer jede Retrieval-Aenderung verpflichtend.

Pflichtsignale:

- Golden Query Benchmark
- Search Precision@5
- Search Recall@5
- Search MRR
- Chat Precision@5
- Chat Recall@5
- Chat MRR
- Citation Completeness
- Insufficient Context Accuracy
- Lifecycle Exclusion Violations
- Search-vs-Chat-Konsistenz

Pflichtartefakte:

- `reports/m5_retrieval/latest.json`
- versionierter Benchmark-Report unter `reports/m5_retrieval/`
- Summary in `reports/m5_retrieval_summary.md`
- `reports/m5_retrieval_regression/latest.json`
- versionierter Regression-Report unter `reports/m5_retrieval_regression/`
- Regression Summary in `reports/m5_retrieval_regression_summary.md`
- Truth-Test-Plan fuer betroffene postgres_truth-Slices

Stop-Regeln:

- `Lifecycle Exclusion Violations > 0` blockiert Merge.
- Citation Completeness unter Schwelle blockiert RAG-Freigabe.
- Insufficient Context Accuracy unter Schwelle blockiert Chat/RAG-Freigabe.
- Missing Context Rate ueber Schwelle blockiert RAG-Freigabe.
- Baseline-Regression groesser als `0.05` blockiert Merge, wenn sie nicht als versionierter Breaking Change freigegeben ist.
- Nicht erklaerte Top-K-Verschiebungen in Golden Queries blockieren Merge.
- Search-vs-Chat-Divergenz ohne dokumentierte Policy blockiert Merge.

---

## 5. Golden Query Benchmark

Der Golden Query Benchmark ist Teil des Retrieval-Vertrags.

Aktuelle Dataset-Version:

```text
m5-retrieval-golden-v1
```

Aktualisierung ist verpflichtend, wenn:

- ein neuer Retrieval-Modus eingefuehrt wird
- Ranking, Query Parsing oder Context Builder geaendert wird
- `source_anchor`, Citation Mapping oder `source_status` geaendert wird
- insufficient-context Verhalten geaendert wird
- Lifecycle- oder Workspace-Filterung geaendert wird
- Search-vs-Chat-Konsistenz neue Faelle abdecken muss

Regeln fuer Golden Query Updates:

1. Alte Golden Queries duerfen nicht geloescht werden, nur weil sie fehlschlagen.
2. Erwartungswerte duerfen nur mit Begruendung geaendert werden.
3. Neue Query-Faelle muessen den betroffenen Stabilitaetsbereich benennen.
4. Dataset-Version muss erhoeht werden, wenn erwartetes Verhalten bewusst geaendert wird.
5. Benchmark-Report muss alte und neue Erwartungen nachvollziehbar referenzieren.

---

## 6. Retrieval Stability Assessment

Jede Retrieval-Aenderung braucht vor Merge ein Assessment:

```
Retrieval Contract Version:
Golden Dataset Version:

Citation Schema:
  Bewertung:
  Nachweis:

source_anchor:
  Bewertung:
  Nachweis:

source_status:
  Bewertung:
  Nachweis:

Retrieval Ranking:
  Bewertung:
  Nachweis:

Lifecycle Filtering:
  Bewertung:
  Nachweis:

insufficient_context:
  Bewertung:
  Nachweis:

Search vs Chat Konsistenz:
  Bewertung:
  Nachweis:

Breaking Change:
  ja/nein
  falls ja: neue Version, Migrationsplan, Gate

Regression Detection:
  Benchmark-Report:
  postgres_truth-Slices:
  Ergebnis:
```

Bewertungen: `keine Auswirkung`, `additiv`, `regressionpflichtig`, `breaking`, `blockierend`.

---

## 7. Gate-Regeln

1. Breaking Retrieval Changes muessen versioniert werden.
2. Jede Retrieval-Aenderung braucht Regression Detection.
3. Der Golden Query Benchmark muss aktualisiert werden, wenn sich erwartetes Verhalten aendert.
4. Architecture-changing Retrieval-Aenderungen brauchen ein neues oder erweitertes Gate.
5. Ein Retrieval-Gate darf nur `pass` sein, wenn maschinenlesbare Reports die Schwellen belegen.
6. Dokumentation darf RAG-Verhalten nur als stabil beschreiben, wenn Contract-Version, Golden Dataset und Report referenziert sind.

---

## 8. Kurzcheckliste

```
[ ] Retrieval Stability Assessment ausgefuellt
[ ] Citation Schema bewertet
[ ] source_anchor bewertet
[ ] source_status bewertet
[ ] Retrieval Ranking bewertet
[ ] Lifecycle Filtering bewertet
[ ] insufficient_context Verhalten bewertet
[ ] Search vs Chat Konsistenz bewertet
[ ] Breaking-Change-Entscheidung dokumentiert
[ ] Falls breaking: neue Retrieval-Vertragsversion definiert
[ ] Regression Detection ausgefuehrt
[ ] Golden Query Benchmark aktualisiert oder bewusst unveraendert begruendet
[ ] Benchmark-Report referenziert
[ ] Betroffene postgres_truth-Slices gruen
```
