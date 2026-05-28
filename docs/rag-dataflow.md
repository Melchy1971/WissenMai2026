# RAG-Datenfluss

Stand: 2026-05-04

Zweck:

- Dieses Dokument definiert den minimalen, kontrollierten RAG-Datenfluss fuer den naechsten Ausbauschritt nach M3b.
- Es beschreibt Sequenz, Komponenten, Fehlerverhalten sowie Logging- und Testverantwortung.
- Der Fluss baut auf der bestehenden Chunk-basierten Retrieval-Basis auf und fuehrt noch keine semantische Suche oder komplexes Re-Ranking ein.

Leitregeln:

- Keine Antwort ohne Quellen.
- Jede Quelle muss mindestens `chunk_id` enthalten.
- Die Kontextgroesse muss explizit begrenzt werden.
- Der Prompt muss deterministisch aus denselben Eingaben zusammengesetzt werden.

## 1. Sequenzbeschreibung

Pfad:

`User Question -> Query Normalisierung -> Retrieval -> Context Builder -> Prompt Builder -> LLM Call -> Citation Mapper -> Response Persistenz -> API Response`

### 1. User Question

Input:

- Benutzerfrage als String
- `workspace_id`
- optionale Request-Metadaten wie `session_id`, `user_id`, `request_id`

Output:

- validierter Question-Request fuer den RAG-Workflow

Verantwortliche Komponente:

- `ChatQuestionRouter` oder spaeterer `RagQueryController`

Fehlerfaelle:

- Frage fehlt oder ist leer
- `workspace_id` fehlt
- Request verletzt Format- oder Laengenregeln

Logging:

- `request_id`
- `workspace_id`
- Eingangslaenge der Frage
- keine unmaskierten sensitiven Inhalte in Fehlerlogs

Tests:

- API-Validierung fuer Pflichtfelder
- Leere oder ueberlange Fragen
- Fehlerformat bei ungueltigem Input

### 2. Query Normalisierung

Input:

- validierte Benutzerfrage

Output:

- deterministisch normalisierte Retrieval-Query
- optionale Zusatzfelder wie `normalized_question`, `retrieval_query`, `query_tokens`

Verantwortliche Komponente:

- `QueryNormalizationService`

Fehlerfaelle:

- Frage reduziert sich auf leere oder nicht nutzbare Query
- nur Stopwords oder nur Rauschen nach Normalisierung

Logging:

- Original- und normalisierte Query-Laenge
- Normalisierungsmodus oder Version
- Kennzeichen, ob Tokens entfernt wurden

Tests:

- deterministische Normalisierung fuer identische Eingaben
- Stopword-only- und Kurzquery-Faelle
- keine versteckte semantische Expansion ohne explizite Entscheidung

### 3. Retrieval

Input:

- `workspace_id`
- normalisierte Retrieval-Query
- Retrieval-Limits wie `top_k`

Output:

- geordnete Trefferliste aus Chunks mit mindestens:
  - `chunk_id`
  - `document_id`
  - `document_version_id`
  - `text_preview` oder Chunk-Text
  - `source_anchor`
  - `rank`

Verantwortliche Komponente:

- `SearchService`
- spaeterer `RagRetrievalService` als orchestrierende Huelle

Fehlerfaelle:

- Suchindex nicht verfuegbar
- Retrieval-Query ungueltig
- Timeout oder technische Degradation
- keine Treffer

Logging:

- `request_id`
- Query-Hash oder normalisierte Query
- Trefferanzahl
- Retrieval-Latenz
- verwendetes `top_k`

Tests:

- Treffer nur aus dem richtigen Workspace
- Ausschluss nicht lesbarer Dokumente
- stabile Sortierung
- PostgreSQL-Integrationsnachweis fuer echte Treffer

### 4. Context Builder

Input:

- geordnete Retrieval-Trefferliste
- Kontextbudget wie `max_chunks`, `max_chars` oder `max_tokens`

Output:

- deterministisch sortierter Kontextblock
- Liste der verwendeten Quellen mit `chunk_id`
- abgeschnittene oder ausgeschlossene Treffer fuer Audit/Debug

Verantwortliche Komponente:

- `ContextBuilderService`

Fehlerfaelle:

- kein verwendbarer Kontext trotz Treffern
- Kontextbudget wird ueberschritten
- Treffer ohne `chunk_id` oder ohne Text

Logging:

- Anzahl gefundener und verwendeter Chunks
- Kontextgroesse in Zeichen oder Tokens
- Gruende fuer Ausschluss einzelner Treffer

Tests:

- Kontext wird bei gleicher Trefferliste identisch gebaut
- Kontextgroesse bleibt unter hartem Limit
- Chunks ohne `chunk_id` werden verworfen und loesen kontrollierten Fehler aus

### 5. Prompt Builder

Input:

- Benutzerfrage
- deterministisch gebauter Kontext
- System- und Prompt-Templates

Output:

- fertiger Prompt fuer den LLM-Call
- Prompt-Metadaten wie Template-Version, Kontextgroesse, Quellenliste

Verantwortliche Komponente:

- `PromptBuilderService`

Fehlerfaelle:

- Template fehlt oder ist inkonsistent
- Kontext kann nicht serialisiert werden
- Prompt verletzt Token- oder Formatbudget

Logging:

- Template-Version
- Prompt-Groesse
- Anzahl verwendeter Quellen
- keine Vollausgabe sensitiver Kontexte in Standardlogs

Tests:

- Prompt ist fuer gleiche Inputs byte-stabil oder strukturell stabil
- Reihenfolge der Quellen bleibt deterministisch
- Prompt enthaelt Quelleninstruktion verpflichtend

### 6. LLM Call

Input:

- deterministisch gebauter Prompt
- Modellkonfiguration

Output:

- Rohantwort des Modells
- Modell-Metadaten wie `model_name`, `latency_ms`, optional `usage`

Verantwortliche Komponente:

- `LlmGateway` oder `ChatCompletionService`

Fehlerfaelle:

- Provider nicht verfuegbar
- Timeout
- Ratenlimit
- leere oder nicht parsebare Modellantwort

Logging:

- Modellname
- Provider
- Latenz
- Fehlerklasse und Retry-Status

Tests:

- Gateway-Mocking fuer Timeout, 429, 5xx
- keine stillen Retries ohne Obergrenze
- Fehler werden in API-seitig kontrollierte Zustande ueberfuehrt

### 7. Citation Mapper

Input:

- Rohantwort des Modells
- Liste der im Kontext verwendeten Quellen

Output:

- Antwort mit explizit gemappten Quellen
- Quellenliste mit mindestens:
  - `chunk_id`
  - `document_id`
  - `document_version_id`
  - `source_anchor`

Verantwortliche Komponente:

- `CitationMappingService`

Fehlerfaelle:

- Modellantwort enthaelt keine zuordenbaren Quellen
- Modell verweist auf nicht im Kontext vorhandene Chunks
- Quellenliste ist leer

Logging:

- Anzahl erkannter Zitate
- Anzahl ungueltiger oder verworfener Zitate
- Modus der Quellenzuordnung

Tests:

- keine Antwort wird als erfolgreich markiert, wenn keine gueltigen Quellen gemappt werden koennen
- jeder Quote- oder Citation-Eintrag muss `chunk_id` enthalten
- nur Quellen aus dem tatsaechlich verwendeten Kontext sind erlaubt

### 8. Response Persistenz

Input:

- finale Antwort mit Quellen
- Request- und Modell-Metadaten

Output:

- persistierter Chat-/RAG-Response-Datensatz
- stabile Response-ID

Verantwortliche Komponente:

- `RagResponsePersistenceService`

Fehlerfaelle:

- Persistenzfehler nach erfolgreichem LLM-Call
- teilweise Persistenz ohne Quellen
- Transaktionskonflikte

Logging:

- Response-ID
- Session-ID
- Persistenzdauer
- Transaktionsstatus

Tests:

- Antwort und Quellen werden atomar gespeichert
- keine Persistenz erfolgreich ohne Quellenliste
- Rollback bei DB-Fehlern

### 9. API Response

Input:

- persistierte oder final validierte Antwort mit Quellen

Output:

- JSON-Response fuer den Client mit:
  - Antworttext
  - Quellenliste
  - mindestens `chunk_id` pro Quelle
  - technische Metadaten, falls vorgesehen

Verantwortliche Komponente:

- `RagResponseRouter`

Fehlerfaelle:

- Antwort ohne Quellen
- unvollstaendige Citation-Metadaten
- interner Fehler in spaeter Pipeline-Stufe

Logging:

- HTTP-Status
- Response-ID
- Anzahl Quellen
- Gesamtlatenz des Workflows

Tests:

- keine `200`-Antwort ohne Quellen
- jede Quelle in der API-Response enthaelt `chunk_id`
- Fehlerformat bleibt konsistent zum restlichen API-Standard

## 2. Komponentenliste

| Komponente | Verantwortung | Muss deterministisch sein | Kritische Ausgabe |
|---|---|---:|---|
| `ChatQuestionRouter` / `RagQueryController` | Request annehmen und validieren | ja | validierter Frage-Request |
| `QueryNormalizationService` | Frage in Retrieval-Query ueberfuehren | ja | `retrieval_query` |
| `SearchService` / `RagRetrievalService` | Chunk-Treffer holen und sortieren | ja | geordnete Trefferliste |
| `ContextBuilderService` | Treffer auf Kontextbudget reduzieren | ja | Kontext plus Quellenliste |
| `PromptBuilderService` | Prompt aus Frage und Kontext bauen | ja | finaler Prompt |
| `LlmGateway` / `ChatCompletionService` | Modellaufruf kapseln | nein im Inhalt, ja im I/O-Vertrag | Rohantwort + Modellmetadaten |
| `CitationMappingService` | Quellen aus Antwort und Kontext mappen | ja | Antwort mit gueltigen Quellen |
| `RagResponsePersistenceService` | Antwort und Quellen speichern | ja im Persistenzvertrag | persistierter Response-Datensatz |
| `RagResponseRouter` | finale API-Antwort ausliefern | ja | JSON-Response |

## 3. Fehlerverhalten

Leitlinien:

- Kein erfolgreicher Response ohne Quellen.
- Keine Quelle ohne `chunk_id`.
- Kein ungebremster Kontextaufbau ohne hartes Groessenlimit.
- Keine nicht-deterministische Prompt-Komposition fuer denselben Eingabestand.

Empfohlene Fehlerklassen:

| Fehlerklasse | Typischer Schritt | Erwartetes Verhalten |
|---|---|---|
| `INVALID_QUESTION` | User Question / Query Normalisierung | `422`, wenn Frage leer oder nicht nutzbar ist |
| `RETRIEVAL_UNAVAILABLE` | Retrieval | `503`, wenn Suchdienst oder Index nicht verfuegbar ist |
| `NO_CONTEXT_AVAILABLE` | Context Builder | kontrollierter Fehler oder fachlich erklaerter No-Answer-Zustand |
| `PROMPT_BUILD_FAILED` | Prompt Builder | `500` oder kontrollierter interner Fehler |
| `LLM_UNAVAILABLE` | LLM Call | `503` oder provider-spezifisch gemappter Fehler |
| `MISSING_CITATIONS` | Citation Mapper | kein `200`; Antwort verwerfen oder als Fehler markieren |
| `PERSISTENCE_FAILED` | Response Persistenz | kein erfolgreicher Abschluss ohne klare Persistenzstrategie |

### Entscheidungsregeln fuer die API

- Wenn Retrieval keine Treffer liefert, darf spaeter ein kontrollierter No-Answer-Response existieren, aber keine frei halluzinierte Antwort.
- Wenn der LLM-Call zwar Text liefert, aber keine gueltigen Quellen zuordenbar sind, ist der Request als Fehler zu behandeln.
- Wenn Persistenz verpflichtender Teil des Flows ist, darf kein `200` zurueckgegeben werden, wenn Antwort und Quellen nicht konsistent gespeichert wurden.

### Logging-Grundsätze

- Jeder Request bekommt eine eindeutige `request_id`.
- Jeder Pipeline-Schritt loggt Start, Ende, Dauer und Ergebnisstatus.
- Query-, Kontext- und Prompt-Inhalte werden nur kontrolliert und gekuerzt geloggt.
- Quellen-Logging muss `chunk_id` enthalten, aber keine unnoetig langen Volltexte.

### Minimale Testpyramide

- Unit-Tests je Pipeline-Schritt fuer deterministische Transformationen.
- Integrations-Tests fuer Retrieval -> Context -> Prompt.
- Gateway-/Provider-Tests mit Mocking fuer LLM-Ausfaelle.
- End-to-End-Tests fuer den kompletten Happy Path mit Quellenpflicht.
- Negative Tests fuer fehlende Quellen, leeren Kontext, Timeout und Persistenzfehler.

## 4. Harte M3c-Vorbedingungen

Bevor dieser RAG-Fluss produktiv umgesetzt wird, sollten mindestens folgende Bedingungen gelten:

- M3b Retrieval ist hart abgeschlossen. Quelle: `reports/current/masterplan_status.json`.
- Search API und Ranking-Baseline sind gegen PostgreSQL verifiziert.
- Evaluation-Dataset fuer Retrieval ist vorhanden.
- Chat/RAG-API-Contract mit Quellenpflicht ist definiert.
- Citation-Mapping und Quellenpflicht sind als API-Vertrag definiert.
- Persistenzmodell fuer Antworten und Quellen ist vor Implementierung geklaert.
