# Datenmodell V1

Dieses Dokument beschreibt den aktuellen Datenmodellstand nach Paket 5 und den dokumentierten M4-Stand. Code und Migrationen sind die Ground Truth. Originaldateien werden nicht gespeichert; kanonische Textquelle ist `document_versions.normalized_markdown`.

## Tabellenuebersicht

- `workspaces`: Arbeitsbereich-Stammdaten; derzeit ohne nachweisbar implementierte Membership-Isolation.
- `users`: vorbereitete User-Stammdaten; derzeit ohne nachweisbar implementierte Login-, Passwort- oder Sessiondaten.
- `documents`: Dokument-Metadaten, Workspace-/Owner-Zuordnung, aktueller Versionszeiger, Deduplizierungs-Hash und Importstatus.
- `document_versions`: versionierter kanonischer Markdown-Inhalt und Parser-/OCR-/KI-Metadaten.
- `document_chunks`: aus einer Dokumentversion abgeleitete Textabschnitte mit Quellenanker.
- `categories`: workspace-faehige Kategorien.
- `tags`: workspace-faehige Tags mit normalisiertem Namen.
- `document_tags`: additive Tag-Zuordnung pro Dokument, Tag und Quelle.
- `chat_sessions`: Chat-Sitzungen mit Workspace-/Owner-Zuordnung.
- `chat_messages`: Chat-Nachrichten mit unveraenderlichem Inhalt und Metadaten.
- `chat_citations`: zitierte Quellen pro Assistant-Nachricht.
- `analysis_groups`: vorbereitete Analysegruppen.
- `analysis_group_documents`: Dokumentauswahl fuer Analysegruppen.
- `analysis_results`: vorbereitete Ergebnisse fuer Merge, Compare und Refine.
- `analysis_result_sources`: optionale Quellenbezuege fuer Analyseergebnisse.

## M4a Konsistenzstand im Datenmodell

Nachweisbar vorhanden:

- `workspaces`
- `users`
- `workspace_memberships`
- `auth_sessions`
- `documents.workspace_id`
- `documents.owner_user_id`
- `chat_sessions.workspace_id`
- `chat_sessions.owner_user_id`

Weiterhin nicht Ziel dieses Dokuments:

- Aussage ueber den vollstaendigen Frontend-Produktfluss
- Aussage ueber alle Betriebs- und Freigabegates ausserhalb des Datenmodells

Folgerung:

- Workspace- und Session-Bezug sind datenmodellseitig vorhanden.
- Das Datenmodell traegt den aktuellen technischen M4a-Kern fuer Memberships und serverseitig aufgeloeste Benutzeridentitaet.
- Formale Freigabeaussagen fuer M4a kommen nicht allein aus diesem Schema, sondern aus den aktuellen Gate- und Truth-Dokumenten.

## Wichtigste Beziehungen

- `documents.workspace_id` verweist auf `workspaces.id`.
- `documents.owner_user_id` verweist auf `users.id`.
- `document_versions.document_id` verweist auf `documents.id`.
- `documents.current_version_id` kann auf eine Version in `document_versions.id` zeigen.
- `document_chunks.document_id` und `document_chunks.document_version_id` binden Chunks an Dokument und Version.
- `categories.workspace_id` und `tags.workspace_id` machen Kategorien und Tags workspace-faehig.
- `document_tags` verbindet Dokumente und Tags additiv ueber `source`.
- Chat- und Analyse-Tabellen verweisen auf Workspaces, vorbereitete User und bei Quellen auf Dokumente, Versionen oder Chunks.

## `documents`

Wichtige Felder:

| Feld | Bedeutung |
|---|---|
| `id` | stabile Dokument-ID |
| `workspace_id` | Workspace-Grenze |
| `owner_user_id` | vorbereitete Owner-Zuordnung |
| `current_version_id` | aktuelle Dokumentversion, in der API als `latest_version_id` ausgegeben |
| `title` | Anzeigename |
| `source_type` | aktuell Importquelle, z.B. `upload` |
| `mime_type` | erkannter MIME-Type |
| `content_hash` | Hash des Quellinhalts fuer Deduplizierung |
| `import_status` | expliziter Importzustand |
| `lifecycle_status` | Dokument-Lifecycle: `active`, `archived`, `deleted` |
| `archived_at` | Zeitpunkt der Archivierung |
| `deleted_at` | Zeitpunkt des Soft-Delete |
| `created_at` | Erstellzeitpunkt |
| `updated_at` | Aktualisierungszeitpunkt |

Constraints:

- Primaerschluessel auf `id`.
- Unique Constraint `uq_documents_workspace_content_hash` auf `(workspace_id, content_hash)`.
- Check Constraint `ck_documents_import_status_allowed` auf erlaubte Importstatuswerte.
- Check Constraint `ck_documents_lifecycle_status_allowed` auf erlaubte Lifecycle-Werte.

Erlaubte Lifecycle-Werte:

- `active`
- `archived`
- `deleted`

Soft-Delete-Modell:

- `deleted` entfernt kein Dokument physisch aus `documents`.
- Versionen und Chunks bleiben erhalten.
- Der Lifecycle wird ueber Status und Timestamps modelliert, nicht ueber `DELETE CASCADE`.
- Eine Wiederherstellung geloeschter Dokumente ist im aktuellen API-Vertrag nicht implementiert.

Erlaubte Importstatuswerte:

- `pending`
- `parsing`
- `parsed`
- `chunked`
- `failed`
- `duplicate`

## `document_versions`

Wichtige Felder:

| Feld | Bedeutung |
|---|---|
| `id` | stabile Versions-ID |
| `document_id` | zugehoeriges Dokument |
| `version_number` | fachliche Versionsnummer pro Dokument |
| `normalized_markdown` | kanonischer Text fuer Read- und spaetere Retrieval-Pfade |
| `markdown_hash` | Hash des normalisierten Markdown, in API als `content_hash` der Version ausgegeben |
| `parser_version` | Parserkennung oder Parser-Version |
| `ocr_used` | ob OCR verwendet wurde; Paket 5 fuehrt kein OCR aus |
| `ki_provider` | optionaler KI-Provider |
| `ki_model` | optionales KI-Modell |
| `metadata` | Parser- und Import-Metadaten |
| `created_at` | Erstellzeitpunkt der Version |

Versionierungsprinzip:

- `documents` enthaelt stabile Dokument-Metadaten.
- Der kanonische Inhalt liegt in `document_versions.normalized_markdown`.
- Der aktuelle Importpfad legt Version 1 an und setzt danach `documents.current_version_id`.
- Die Read-API behandelt `documents.current_version_id` als `latest_version_id`.

## `document_chunks`

Wichtige Felder:

| Feld | Bedeutung |
|---|---|
| `id` | stabile Chunk-ID |
| `document_id` | zugehoeriges Dokument |
| `document_version_id` | zugehoerige Version |
| `chunk_index` | stabile Position innerhalb der Version, in der API als `position` ausgegeben |
| `heading_path` | strukturierter Ueberschriftenpfad |
| `anchor` | interner Quellenanker, z.B. `dv:<document_version_id>:c0000` |
| `content` | Chunk-Volltext, nicht Teil der Read-Detail-API |
| `content_hash` | Hash des Chunk-Inhalts |
| `token_estimate` | optionale Tokenschaetzung |
| `metadata` | strukturierte Chunk-Metadaten inklusive `source_anchor` |
| `created_at` | Erstellzeitpunkt |

Chunk- und Quellenankerprinzip:

- Chunks entstehen aus `document_versions.normalized_markdown`.
- Chunks werden fuer die API ueber `chunk_index ASC` sortiert.
- `GET /documents/{document_id}/chunks` liefert nur `text_preview`, keinen Volltext.
- `metadata.source_anchor` ist das normalisierte Quellenanker-Schema fuer API-Responses.

Normalisiertes `source_anchor`-Schema:

```json
{
  "type": "text",
  "page": null,
  "paragraph": null,
  "char_start": 0,
  "char_end": 200
}
```

Erlaubte `type`-Werte:

- `text`
- `pdf_page`
- `docx_paragraph`
- `legacy_unknown`

Legacy-Verhalten:

- Alte freie oder uneinheitliche `metadata.source_anchor`-Daten werden bei der Migration nicht geloescht.
- Wenn Legacy-Daten nicht dem normalisierten Schema entsprechen, werden sie nach `metadata.legacy_source_anchor` kopiert.
- Die API gibt keine freien Legacy-Metadaten-Blobs als `source_anchor` aus.

## Import- und Deduplizierungsprinzip

Der Importpfad unterstuetzt aktuell:

- `.txt`
- `.md`
- `.docx`
- `.doc`
- `.pdf`

Deduplizierung erfolgt ueber `documents(workspace_id, content_hash)`.

Verhalten:

- Vor dem Insert wird auf vorhandene Dokumente mit gleichem `(workspace_id, content_hash)` geprueft.
- Die Datenbank sichert denselben Key zusaetzlich per Unique Constraint ab.
- Bei Insert-Konflikt wird der Konflikt abgefangen und das bestehende Dokument deterministisch zurueckgegeben.
- Duplicate-Responses setzen `duplicate_status = duplicate_existing` und `import_status = duplicate`.

## Bekannte Einschraenkungen fuer Auth und Workspace-Isolation

- `owner_user_id` ist vorhanden, wird aber nicht ueber einen nachweisbaren Login-/Session-Flow aufgeloest.
- `workspace_id` ist fachlich zentral, wird aber in mehreren API-Vertraegen weiterhin explizit vom Client transportiert.
- Ohne `workspace_memberships` gibt es keine referenzielle Mitgliedschaftsabbildung fuer echte Workspace-Zugriffspruefung.

## Tag-Prinzip

Kategorien und Tags sind getrennt modelliert. Tags sind pro Workspace ueber `normalized_name` eindeutig. `document_tags.source` ist kontrolliert auf `manual`, `ki` und `import`.

Die Zuordnung ist additiv: Der Primaerschluessel `(document_id, tag_id, source)` erlaubt, dass ein manuelles Tag und ein KI-Tag fuer dasselbe Dokument parallel existieren. Manuelle Tags ueberschreiben KI-Tags nicht automatisch.

## Chat- und Analyse-Stand

`chat_sessions`, `chat_messages` und `chat_citations` bilden jetzt die Persistenzgrundlage fuer Chat/RAG-Verlaeufe. M3c nutzt diese Tabellen aktiv ueber die Chat-HTTP-API und den `RagChatService`. `basis_type` unterscheidet weiter `knowledge_base`, `general`, `mixed` und `unknown`. Message-Inhalte werden append-only erzeugt; ein Bearbeitungspfad ist im aktuellen Stand nicht vorgesehen.

Chat-spezifische Regeln:

- `chat_sessions` enthaelt `workspace_id`, `owner_user_id`, `title`, `created_at`, `updated_at`.
- `chat_messages` enthaelt `session_id`, `message_index`, `role`, `content`, `basis_type`, `metadata`, `created_at`.
- `chat_citations` enthaelt `message_id`, `chunk_id`, `document_id`, `source_anchor`.
- `chat_citations` enthaelt zusaetzliche Snapshot-Felder wie `document_title`, `quote_preview` und `source_status`.
- `chat_citations.source_status` ist auf `active | archived | deleted | missing` begrenzt.
- Citations referenzieren `documents` und `document_chunks` referenziell konsistent.
- Fuer zitierte Dokumente und Chunks ist Loeschen bewusst restriktiv modelliert, damit historische Chat-Quellen nicht still brechen.
- Historische Citations bleiben auch dann lesbar, wenn das referenzierte Dokument spaeter `deleted` ist.
- Lifecycle-Aenderungen aktualisieren den Citation-Snapshot `source_status`, entfernen aber keine historische Citation.
- `POST /api/v1/chat/sessions/{session_id}/messages` speichert zuerst die User-Message und danach bei ausreichendem Kontext die Assistant-Message.
- Assistant-Messages mit `basis_type = knowledge_base` muessen im erfolgreichen RAG-Pfad Citations mit `chunk_id` besitzen.
- Insufficient-Context-, Retrieval- und LLM-Fehler speichern keine freie Assistant-Antwort.
- `chat_messages.metadata` kann technische RAG-Metadaten wie Prompt-Version und Retrieval-Scores enthalten; die API gibt diese Rohmetadaten nicht ungefiltert aus.

Analysefunktionen werden ueber `analysis_groups`, `analysis_group_documents`, `analysis_results` und `analysis_result_sources` vorbereitet. Ergebnisarten sind `merge`, `compare` und `refine`. Analyseergebnisse koennen vor einem spaeteren Commit gespeichert werden; `commit_ref` ist optional.

## Migrationen

Relevante Migrationen fuer das Dokumentmodell:

- `20260430_0001_initial_document_schema.py`: Basis fuer Workspaces, Users, Documents und Versions.
- `20260430_0002_document_chunks.py`: Chunk-Tabelle mit Inhalt, Hash, Position und Metadaten.
- `20260430_0003_categories_tags.py`: Kategorien, Tags und Dokument-Tag-Zuordnung.
- `20260430_0004_chat_analysis.py`: vorbereitete Chat- und Analyse-Tabellen.
- `20260504_0005_document_content_hash_unique.py`: Unique Constraint fuer `(workspace_id, content_hash)`.
- `20260504_0006_document_import_status.py`: `documents.import_status`, Backfill und Check Constraint.
- `20260504_0007_normalize_chunk_source_anchor.py`: Normalisierung von `metadata.source_anchor`.
- `20260504_0008_read_api_performance_indexes.py`: Read-Indizes fuer Dokumentliste und Chunk-Read-Pfade.
- `20260504_0009_document_version_recency_index.py`: Recency-Index fuer Versionslisten pro Dokument.
- `20260504_0010_repair_legacy_document_states.py`: Reparatur und Auditierung inkonsistenter Legacy-Dokumente, Versionen und Chunks.
- `20260504_0011_chunk_search_vector.py`: PostgreSQL-FTS-Spalte und `GIN`-Index fuer Retrieval.
- `20260504_0012_chat_message_metadata_and_citations.py`: Ausrichtung von `chat_messages.metadata` und neue Tabelle `chat_citations`.
- `20260505_0013_document_lifecycle.py`: Lifecycle-Felder, Constraint und Listenindex fuer `active|archived|deleted`.
- `20260506_0012_chunk_searchability.py`: `document_chunks.is_searchable` und lifecycle-abhaengige Search-Indexierbarkeit.
- `20260506_0013_historical_chat_citation_snapshots.py`: Snapshot-Felder fuer historische Citations und `source_status`.
- `20260508_0014_chat_citation_missing_status.py`: Vereinheitlicht `chat_citations.source_status` auf `active|archived|deleted|missing` und migriert `unknown -> missing`.

## M4c Lifecycle-Auswirkungen auf Retrieval und Chat

- Search beruecksichtigt nur Dokumente mit `lifecycle_status = active`.
- Archivierte Dokumente bleiben datenmodellseitig vollstaendig erhalten, fallen aber aus neuem Retrieval heraus.
- Geloeschte Dokumente bleiben zur Wahrung historischer Referenzen vorhanden, sind aber fachlich unsichtbar.
- `document_chunks.is_searchable` bildet die Search-Sichtbarkeit explizit ab.
- `chat_citations` speichert Snapshot-Felder wie `document_title`, `quote_preview` und `source_status`, damit historische Antworten lesbar bleiben.

Bekannte Einschraenkungen:

- Das Datenmodell enthaelt keinen separaten Purge-Status oder Hard-Delete-Prozess.
- Das Datenmodell belegt historische Citation-Stabilitaet, aber nicht allein den End-to-End-Nachweis, dass neue Chat-Antworten nach Lifecycle-Aenderungen keine alten Dokumente mehr verwenden.
- `deleted` ist terminal; eine Rueckkehr in `active` oder `archived` ist nicht modelliert.
- Historische Citations werden absichtlich nicht an den aktuellen Read- oder Search-Sichtbarkeitsstatus angepasst, sondern nur ueber `source_status` markiert.

## Performance- und Reparaturergaenzungen aus Paket 5

### Read-Performance

Das Datenmodell wird seit Paket 5 nicht nur fachlich, sondern auch fuer die Read-API-Zugriffspfade abgesichert:

- `documents(workspace_id, created_at DESC)` fuer Workspace-Listen in absteigender Chronologie.
- `document_versions(document_id, created_at DESC)` fuer Versionslisten pro Dokument.
- `document_chunks(document_id, document_version_id, chunk_index)` fuer Chunk-Reads, Chunk-Counts und stabile Reihenfolge.

Diese Indizes stuetzen die aktuelle Repository-Implementierung direkt.

Der aktuelle Repository-Code behandelt ID- und Workspace-Filter kompatibel fuer SQLite-Testumgebungen und PostgreSQL-UUID-Spalten. Damit ist das Read-Modell nicht nur dokumentiert, sondern auf beiden verifizierten Backends praktisch nutzbar.

### Legacy-Reparatur und Audit-Trail

Migration `20260504_0010` fuehrt zusaetzlich ein:

- Audit-Tabelle `migration_document_repairs` fuer protokollierte Reparaturen.
- Backfill oder Neuverkettung von `documents.current_version_id`, wenn Legacy-Daten inkonsistent sind.
- Ableitung von `documents.import_status` anhand real vorhandener Versionen und Chunks.
- kanonische Normalisierung von `document_chunks.metadata.source_anchor`.
- Erhalt alter Metadaten in `metadata.legacy_source_anchor`, wenn sie nicht dem Normschema entsprechen.

Neue harte Datenregeln:

- Lesbare Dokumente duerfen nicht ohne `current_version_id` bestehen.
- `document_chunks.metadata.source_anchor` muss das normalisierte Schluesselschema enthalten.

## M3b Retrieval

Fuer M3b ist PostgreSQL Full Text Search auf Chunk-Ebene jetzt als erster Retrieval-Pfad angelegt.

Bevorzugte technische Richtung:

- `document_chunks` bleibt die Retrieval-Einheit.
- Volltextsuche wird ueber PostgreSQL FTS auf `document_chunks.content` aufgebaut.
- Embeddings und Vektorindizes bleiben explizit spaetere Erweiterungen.

Erwartete technische Ergaenzungen:

- generierte STORED-Spalte `search_vector` auf `document_chunks` fuer PostgreSQL.
- `GIN`-Index auf `document_chunks.search_vector`.
- keine Aenderung am kanonischen Inhaltsprinzip: `document_versions.normalized_markdown` bleibt Ursprung, `document_chunks` bleibt Such- und Retrieval-Schnitt.

Aktueller Implementierungsstand:

- Migration `20260504_0011_chunk_search_vector.py` fuehrt die PostgreSQL-Suchspalte und den GIN-Index ein.
- Unter SQLite bleibt nur Schema-Paritaet fuer lokale Tests, ohne produktionsgleichen FTS-Stack.
- Der Query-Pfad fuer Retrieval laeuft read-only ueber `documents`, `document_versions` und `document_chunks` mit Join-Validierung.

Bewusste Nicht-Ziele in M3b:

- keine Embedding-Tabellen
- keine Vektorindizes
- keine semantische Suche als Pflichtbestandteil
- Chat-Persistenz ist fuer Sessions, Messages und Citations vorhanden; der vollstaendige M3c-RAG-Antwortpfad ist oberhalb des Retrieval-Modells im Service-Layer implementiert.

## M3c Chat/RAG

M3c fuegt keine neue Datenbanktabelle hinzu, sondern nutzt die vorhandenen Chat-Tabellen aus Migration `20260504_0012_chat_message_metadata_and_citations.py`.

Service-Regeln:

- Chat-Sessions werden ueber `chat_sessions` verwaltet.
- User-Fragen werden als `chat_messages.role = user` persistiert.
- Assistant-Antworten aus dem RAG-Pfad werden als `chat_messages.role = assistant` und `basis_type = knowledge_base` persistiert.
- Citations werden in `chat_citations` gespeichert und enthalten mindestens `chunk_id`, `document_id` und normalisiertes `source_anchor`.
- Die API response fuer `POST /messages` enthaelt die Assistant-Message; die User-Message ist persistiert, aber nicht Teil dieser Response.
- Fehlende oder unzureichende Quellen verhindern eine Assistant-Persistenz.

## V1-Grenzen

- Keine Authentifizierung.
- Keine Rollen- oder Rechtepruefung.
- Keine UI.
- Keine OCR-Ausfuehrung.
- Keine vollstaendig integrierte Analyse-Service-Logik ueber HTTP.
- Keine verpflichtende Vektorsuche.
- Keine Embedding-Pipeline.
- Keine Speicherung von Originaldateien.
- Kein implementierter `/api/v1/documents`-Alias fuer die Dokument-API; aktuell ist `/documents` implementiert.
