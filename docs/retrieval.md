# Retrieval

Stand: 2026-05-07

Dieses Dokument definiert den stabilen M3b Retrieval-Vertrag fuer den implementierten Endpoint `GET /api/v1/search/chunks`.

## Implementierter Scope

- Read-only Chunk-Suche.
- PostgreSQL Full Text Search auf Chunk-Ebene.
- Suche ueber `document_chunks.search_vector`.
- Ranking ueber PostgreSQL `ts_rank`.
- stabile Sortierung mit expliziten Tie-Breakern.
- Ausschluss nicht aktueller Versionen.
- Ausschluss nicht lesbarer Importstatus.
- normalisierte `source_anchor`-Response.

## Endpoint

```text
GET /api/v1/search/chunks
```

Query Parameter:

| Name | Typ | Required | Default | Limit / Regel |
|---|---|---:|---:|---|
| `q` | string | ja | - | nicht leer |
| `limit` | integer | nein | `20` | `1..100` |
| `offset` | integer | nein | `0` | `>= 0` |

Der Workspace wird serverseitig aus dem AuthContext abgeleitet. Ein clientseitiger `workspace_id`-Queryparameter ist nicht Teil des aktuellen Vertrags.

Der Endpoint akzeptiert aktuell keine weiteren Filterparameter.

## Response Schema

Response ist ein JSON-Array von `SearchChunkResult`:

```json
[
  {
    "document_id": "document-id",
    "document_title": "Document title",
    "document_created_at": "2026-05-01T10:00:00Z",
    "document_version_id": "version-id",
    "version_number": 1,
    "chunk_id": "chunk-id",
    "position": 0,
    "text_preview": "First 200 characters of chunk content",
    "source_anchor": {
      "type": "text",
      "page": null,
      "paragraph": null,
      "char_start": 0,
      "char_end": 200
    },
    "rank": 0.123,
    "filters": {}
  }
]
```

Felder:

| Feld | Bedeutung |
|---|---|
| `document_id` | Dokument des Treffers |
| `document_title` | Titel des Dokuments |
| `document_created_at` | Erstellzeitpunkt des Dokuments |
| `document_version_id` | aktuelle Version, aus der der Treffer stammt |
| `version_number` | Versionsnummer |
| `chunk_id` | stabile Chunk-ID |
| `position` | Chunk-Position, entspricht `chunk_index` |
| `text_preview` | DB-seitig gekuerzte Vorschau, maximal 200 Zeichen |
| `source_anchor` | normalisierter Quellenanker |
| `rank` | PostgreSQL `ts_rank` als Float |
| `filters` | aktuell immer `{}` |

## PostgreSQL-Abhaengigkeit

M3b Retrieval ist PostgreSQL-only.

Verwendete PostgreSQL-Funktionen:

- `tsvector` Generated Column `document_chunks.search_vector`
- GIN-Index `ix_document_chunks_search_vector`
- `plainto_tsquery('simple', q)`
- `ts_rank(search_vector, ts_query)`

Verhalten bei SQLite oder nicht verfuegbarem Search Backend:

- SQLite fuehrt diesen Endpoint nicht fachlich aus.
- Wenn der aktive SQLAlchemy-Dialect nicht `postgresql` ist, liefert der Endpoint `503 SERVICE_UNAVAILABLE`.
- Ohne verfuegbares Search Backend gibt es keine Fallback-Suche.

## Filter- und Sichtbarkeitsregeln

Ein Chunk darf nur als Treffer erscheinen, wenn alle Bedingungen gelten:

- `documents.workspace_id = auth_context.workspace_id`
- `documents.current_version_id = document_versions.id`
- `document_chunks.document_version_id = document_versions.id`
- `document_chunks.search_vector @@ plainto_tsquery('simple', q)`
- `documents.import_status in ('parsed', 'chunked')`

Damit werden ausgeschlossen:

- Chunks alter, nicht aktueller Versionen.
- Dokumente mit `pending`.
- Dokumente mit `failed`.
- Dokumente mit `archived`.
- Dokumente mit `deleted`.
- Dokumente ausserhalb des angefragten Workspaces.

Lifecycle-Auswirkung:

- Retrieval/Search arbeitet nur auf `documents.lifecycle_status = active`.
- Archivierte Dokumente bleiben ueber die Dokumentliste erreichbar, verschwinden aber sofort aus neuen Search-Treffern.
- Soft-geloeschte Dokumente bleiben historisch im Datenmodell, sind fuer Retrieval jedoch ausgeschlossen.
- Reindex synchronisiert dazu die Chunk-Sichtbarkeit ueber `document_chunks.is_searchable`.
- Historische Chat-Citations sind kein Retrieval-Modus und werden von diesen Regeln nicht rueckwirkend bereinigt.

Reindex-Regeln im nachgewiesenen Stand:

- Archivieren und Loeschen setzen Chunks fuer das betroffene Dokument auf `is_searchable = false`.
- Restore setzt Chunks fuer das betroffene Dokument wieder auf `is_searchable = true`.
- Der Rebuild-Service synchronisiert die Searchability erneut gegen den dokumentierten Lifecycle-Zustand.
- Inkonsistenzpruefungen melden archivierte oder geloeschte Dokumente, die weiter im aktiven Index auftauchen, sowie fehlende Indexeintraege.

Nachweisgrenze:

- Der Lifecycle-Ausschluss ist in lokalen Service-/API-Tests und in den PostgreSQL-Integrationsfixtures modelliert.
- Der letzte echte PostgreSQL-Lauf gegen die konfigurierte Testdatenbank war infra-blockiert und konnte diesen Nachweis nicht gruen bestaetigen.

## Sortierlogik

Die Trefferreihenfolge ist stabil und Teil des Vertrags:

1. `rank DESC`
2. `document.created_at DESC`
3. `chunk_index ASC`
4. `chunk_id ASC`

Ranking-Erwartung:

- Staerkere PostgreSQL-FTS-Treffer kommen zuerst.
- Bei gleichem Rank kommt das neuere Dokument zuerst.
- Bei gleichem Dokumentdatum kommt der fruehere Chunk zuerst.
- Bei weiterhin gleichem Sortierschluessel entscheidet `chunk_id ASC`.

## Fehlercodes

Fehlerformat:

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Chunk search requires PostgreSQL full text search",
    "details": {}
  }
}
```

| HTTP Status | Code | Ursache |
|---:|---|---|
| `422` | `INVALID_QUERY` | `q` fehlt oder ist leer |
| `422` | `INVALID_PAGINATION` | `limit > 100`, `limit < 1` oder `offset < 0` |
| `401` | `AUTH_REQUIRED` | Authentifizierung fehlt |
| `403` | `WORKSPACE_ACCESS_FORBIDDEN` | kein Zugriff auf den aktiven Workspace |
| `503` | `SERVICE_UNAVAILABLE` | Search erfordert PostgreSQL oder Backend ist nicht verfuegbar |
| `500` | `INTERNAL_ERROR` | unerwarteter interner Fehler |

## Nicht-Scope

- kein Chat
- keine LLM-Antwort
- keine Embeddings
- keine semantische Suche
- kein Re-Ranking
- keine Antwortgenerierung
- keine Zitatauswahl ueber den gelieferten `source_anchor` hinaus
- keine Schreiboperationen

## Bekannte Einschraenkungen

- Retrieval kennt keinen historischen Modus fuer archivierte oder geloeschte Dokumente.
- Bereits gespeicherte Chat-Citations koennen weiter auf Dokumente verweisen, die aus dem aktuellen Retrieval nicht mehr erreichbar sind.
- Der aktuelle PostgreSQL-Integrationslauf fuer Retrieval/Search ist nicht gruen nachgewiesen, weil die konfigurierte Test-Datenbank im letzten Lauf per Connection-Timeout nicht erreichbar war.

## Tests

M3b Search ist ueber PostgreSQL-Integrationstests vorbereitet, die nur mit `TEST_DATABASE_URL` laufen:

- echte HTTP-Requests gegen `GET /api/v1/search/chunks`
- deterministische Fixture-Daten
- Ausschluss alter Versionen
- Ausschluss `failed`/`pending`
- Workspace-Grenze
- Required Response Fields
- Ranking-Regression fuer die Sortierlogik

Aktueller Befund:

- Der fokussierte lokale Service-/API-Slice ist gruen.
- Der letzte End-to-End-Lauf gegen die konfigurierte PostgreSQL-Ziel-Datenbank ist nicht an fachlichem Verhalten, sondern an DB-Erreichbarkeit gescheitert.
- Der lokale Reindex-/Inkonsistenz-Slice ist gruen, ersetzt aber nicht den blockierten PostgreSQL-End-to-End-Nachweis.

Ohne `TEST_DATABASE_URL` werden diese Tests geskippt. SQLite darf diese Tests nicht ausfuehren.
