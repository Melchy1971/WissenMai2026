# RAG

Stand: 2026-05-05

Dieses Dokument ist der kurze Einstiegspunkt fuer den aktuellen Stand von Chat/RAG.

Es beschreibt den abgeschlossenen Stand der M3c Chat/RAG Foundation. M3c liefert den stabilen Antwortpfad ueber Chat-API, Retrieval, Kontextbau, Prompting, Policy, Fake-LLM-Testprovider, Citation Mapping und Persistenz. M4 bleibt die naechste Ausbaustufe fuer produktive LLM-Provider, Streaming, erweiterte Chat-Funktionen und Analyseintegration.

## Implementiert

- RAG-Datenfluss ist dokumentiert.
- Chat/RAG-API-Vertrag ist dokumentiert.
- Chat-HTTP-API unter `/api/v1/chat/...` ist implementiert.
- `POST /api/v1/chat/sessions/{session_id}/messages` ist mit dem RAG-Orchestrator verdrahtet.
- `RagChatService` orchestriert Persistenz, Retrieval, Context Builder, Insufficient-Context-Policy, Prompt Builder, LLM Provider, Citation Mapper und Assistant-Persistenz.
- Context Builder ist implementiert.
- Prompt Builder ist implementiert.
- Citation Mapper ist implementiert.
- Insufficient-Context-Policy ist implementiert.
- Chat-Persistenz fuer Sessions, Messages und Citations ist implementiert.
- Fake LLM Provider fuer deterministische Tests ist implementiert.
- Chat-UI ist gegen den dokumentierten Backend-Vertrag implementiert und ueber Screen-Tests abgesichert.
- API-, Service- und Frontend-Tests fuer M3c sind vorhanden.

## Antwortpfad

Der erfolgreiche M3c-Flow:

1. User-Frage wird als Chat-Message gespeichert.
2. Retrieval sucht Chunks ueber den Search-Service.
3. Context Builder erzeugt ein deterministisches Kontextpaket.
4. Insufficient-Context-Policy bricht ab, wenn der Kontext nicht belastbar ist.
5. Prompt Builder erzeugt System- und User-Prompt.
6. LLM Provider wird nur bei ausreichendem Kontext aufgerufen.
7. Assistant-Antwort wird gespeichert.
8. Citations werden aus Chunk-Referenzen in der Antwort abgeleitet und persistiert.
9. API liefert eine `ChatMessageResponse` fuer die Assistant-Antwort inklusive Citations und Confidence.

## Quellenlogik

- Keine erfolgreiche dokumentgestuetzte Antwort ohne Quellen.
- Citations muessen mindestens `chunk_id`, `document_id`, `source_anchor` und optional `quote_preview` enthalten.
- Eine Assistant-Antwort ohne Chunk-Referenz wird als `INSUFFICIENT_CONTEXT` verworfen.
- Insufficient-Context-Faelle erzeugen keine freie Assistant-Antwort und rufen keinen LLM Provider auf.

## Lifecycle-Auswirkungen auf RAG

- Neues Retrieval fuer Chat nutzt nur aktive Dokumente.
- Archivierte Dokumente liefern keine neuen Retrieval-Treffer mehr.
- Soft-geloeschte Dokumente liefern ebenfalls keine neuen Retrieval-Treffer mehr.
- Bereits gespeicherte Chat-Citations bleiben historisch sichtbar, auch wenn das referenzierte Dokument spaeter geloescht wurde.
- Bereits gespeicherte Chat-Citations bleiben ebenfalls fuer spaeter archivierte Dokumente sichtbar und tragen dazu `source_status`.

Citation-Historie:

- `chat_citations` bleibt append-only Teil des Chatverlaufs.
- Die API filtert historische Citations fuer geloeschte Dokumente nicht nachtraeglich weg.
- Dadurch bleibt die Nachvollziehbarkeit alter Antworten erhalten, auch wenn das aktuelle Dokument nicht mehr ueber Read-API oder Search erreichbar ist.

Nachweisgrenze:

- Historische Citation-Stabilitaet ist direkt getestet.
- Dass neue Chat-Antworten keine archivierten oder geloeschten Dokumente mehr verwenden, ist derzeit nur indirekt ueber den Retrieval-/Search-Ausschluss nachgewiesen.
- Ein gruener PostgreSQL-End-to-End-Nachweis fuer diesen Ausschluss liegt im letzten Lauf nicht vor, weil die konfigurierte Testdatenbank nicht erreichbar war.

## Fehlerverhalten

Alle Fehler verwenden das API-Error-Envelope.

| Code | Bedeutung |
|---|---|
| `CHAT_SESSION_NOT_FOUND` | Session existiert nicht |
| `CHAT_MESSAGE_INVALID` | Request ist ungueltig, z.B. leere Frage |
| `CHAT_PERSISTENCE_FAILED` | Persistenzfehler beim Speichern |
| `RETRIEVAL_FAILED` | Retrieval-Service ist fehlgeschlagen |
| `INSUFFICIENT_CONTEXT` | Kontext reicht nicht fuer eine belegte Antwort |
| `LLM_UNAVAILABLE` | LLM Provider ist nicht verfuegbar oder liefert keine Antwort |

## Verifikation

- Chat-API, Schemas, RAG-Service, Fake LLM Provider und Chat-Persistenz: `74 passed` im historischen fokussierten Backend-Lauf.
- Frontend ChatPage und alle Frontend-Screen-Tests: `14 passed`.
- Frontend-Build: erfolgreich.

## Referenzen

- `docs/rag-dataflow.md`
- `docs/chat-rag-api-contract.md`
- `docs/retrieval.md`

## Abschlussstand

- Fachlicher Fortschritt: abgeschlossen fuer M3c Foundation
- Harter Abschluss: bestanden
- Score: `94/100`
- Historische Entscheidung nach M3c-Abschluss: `Go` fuer den Start von M4-Produktisierung; kein aktueller M4-Freigabestatus.

## Abgrenzung zu M4

- M3c liefert Foundation, stabilen API-Pfad, Fake-LLM-Testbarkeit und Quellenpflicht.
- M4 ersetzt den Fake-/unconfigured Provider durch einen produktiven LLM Provider und erweitert den Chat fachlich.
- Streaming, Agenten, Tool Use, Dokumentmutation, Embeddings und Analysefunktionen bleiben ausserhalb von M3c.

Bekannte Einschraenkung aus M4c:

- Historische Citations koennen auf Dokumente zeigen, die inzwischen archiviert oder geloescht wurden; das ist beabsichtigt und kein Datenfehler.
- Ein eigener Lifecycle-End-to-End-Test fuer den Chat-Antwortpfad fehlt derzeit noch.
