# API fuer M3a GUI, M3b Retrieval-UI, M3c Chat/RAG und M4-Produktisierung

Stand: 2026-05-18

## Zweck

Dieses Dokument beschreibt die API-Abhaengigkeit der aktuellen GUI auf hoher Ebene und den Vertrag fuer M3b Search sowie M3c Chat/RAG. Verbindlicher Detailvertrag fuer die Dokument-Read-Pfade bleibt `docs/api/v1-document-api-contract.md`. Der Retrieval-Vertrag fuer M3b ist zusaetzlich in `docs/retrieval.md` beschrieben.

M3a-Nachweisgrenze: Die GUI kann vorhandene API-Faehigkeiten konsumieren, aber M3a ist nicht stabilisiert. `reports/frontend_truth_report.json` vom 2026-05-18 ist rot (`80 collected`, `58 passed`, `22 failed`). `reports/m3a_gate_result.json` steht auf `FAIL`, Score `57.1`. Ohne gruenen Gate-Report duerfen API-/GUI-Vertragsaussagen nicht als M3a-Freigabe gelesen werden.

## M4a Konsistenzstand

Der dokumentierte Zielzustand fuer M4a ist ein durchgaengig serverseitig aufgeloester Auth- und Workspace-Kontext fuer alle geschuetzten Pfade. Der technische Backend-Kern ist vorhanden, aber aktuelle Freigabeaussagen duerfen nur aus den Gate-Reports abgeleitet werden. Der aktuelle M3a-Gate-Report ist rot; der aktuelle PostgreSQL Truth Report ist ebenfalls nicht gruen.

Fuer Admin-Diagnostics ist der Legacy-Header `x-admin-token` nicht Teil des aktiven Vertrags. Diagnostics autorisiert ausschliesslich ueber AuthContext, aktiven Workspace und Workspace-Membership/Rolle.

Nachweisbar implementiert:

- `UNAUTHORIZED`, `FORBIDDEN` und `DIAGNOSTICS_FAILED` fuer den read-only Diagnostics-Endpunkt
- `AUTH_REQUIRED` und `ADMIN_REQUIRED` fuer sonstige Admin-Pfade ueber serverseitigen Auth-/Membership-Kontext
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- serverseitige Membership-Pruefung ueber Auth-Middleware fuer geschuetzte Fachendpunkte
- `WORKSPACE_REQUIRED` fuer mehrere fachliche Endpunkte mit explizitem Workspace-Parameter
- Uploads verwenden Workspace und Benutzer aus dem serverseitigen Auth-Kontext statt clientseitig frei uebergebener `workspace_id`

Nicht nachweisbar implementiert:

- `POST /auth/logout`
- Cookie-Session-Produktflow oder JWT-basierte Benutzeridentitaet als finaler Produktstandard
- vollstaendiger Frontend-Login-/Logout-/Route-Guard-Flow

## Aktuell implementierte Endpunkte

M3a Dokument-GUI:

- `GET /documents`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/versions`
- `GET /documents/{document_id}/chunks`

Diese vier Read-Pfade bilden den urspruenglichen M3a-Kern. Die folgenden Schreib-, Such-, Chat-, Lifecycle- und Diagnostics-Pfade sind spaetere GUI-Slices; sie belegen vorhandene Funktionalitaet, aber keinen gruenen M3a-Abschluss:

- `POST /documents/import`
- `PATCH /documents/{document_id}/archive`
- `PATCH /documents/{document_id}/restore`
- `DELETE /documents/{document_id}`

M3b Retrieval:

- `GET /api/v1/search/chunks`

M3c Chat:

- `POST /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions/{session_id}`
- `POST /api/v1/chat/sessions/{session_id}/messages`

M4d Admin/Diagnostics:

- `GET /api/v1/admin/diagnostics`
- `GET /api/v1/admin/search-index/inconsistencies`
- `POST /api/v1/admin/search-index/rebuild` ist fuer M4d read-only blockiert und liefert `501 ADMIN_ACTION_NOT_IMPLEMENTED`

M4e Backup/Restore:

- CLI-first, optionale Admin-API spaeter

## M3b Search Contract

### `GET /api/v1/search/chunks`

Sucht in Chunks ueber PostgreSQL Full Text Search.

Query Parameter:

| Name | Typ | Required | Default | Limit / Regel |
|---|---|---:|---:|---|
| `q` | string | ja | - | `min_length=1`, wird im Service getrimmt |
| `limit` | integer | nein | `20` | `1..100` |
| `offset` | integer | nein | `0` | `>= 0` |

Request-Beispiel:

```text
GET /api/v1/search/chunks?q=rankingterm%20orderterm&limit=20&offset=0
```

Der Workspace wird serverseitig aus dem AuthContext abgeleitet.

Response `200`:

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

Response Schema `SearchChunkResult`:

| Feld | Typ | Nullable | Hinweis |
|---|---|---:|---|
| `document_id` | string | nein | Dokument-ID |
| `document_title` | string | nein | Dokumenttitel |
| `document_created_at` | datetime string | nein | fuer Sortier-Tie-Breaker relevant |
| `document_version_id` | string | nein | aktuelle Version des Dokuments |
| `version_number` | integer | nein | Versionsnummer |
| `chunk_id` | string | nein | stabile Chunk-ID |
| `position` | integer | nein | entspricht `chunk_index` |
| `text_preview` | string | nein | serverseitig auf 200 Zeichen projiziert |
| `source_anchor` | `DocumentChunkSourceAnchor` | nein | normalisiertes Quellenanker-Schema |
| `rank` | float | nein | PostgreSQL `ts_rank` |
| `filters` | object | nein | aktuell immer `{}`, kein Query-Filtervertrag |

Schema `DocumentChunkSourceAnchor`:

| Feld | Typ | Nullable |
|---|---|---:|
| `type` | `"text"`, `"pdf_page"`, `"docx_paragraph"` oder `"legacy_unknown"` | nein |
| `page` | integer | ja |
| `paragraph` | integer | ja |
| `char_start` | integer | ja |
| `char_end` | integer | ja |

## Search-Verhalten

PostgreSQL-Abhaengigkeit:

- Search funktioniert nur mit PostgreSQL.
- Der Repository-Code verlangt PostgreSQL, weil `search_vector`, `plainto_tsquery`, `ts_rank` und GIN-Index genutzt werden.
- SQLite ist fuer diesen Endpoint kein unterstuetztes Search-Backend.
- Bei SQLite oder anderem Nicht-PostgreSQL-Dialect liefert der Endpoint `503 SERVICE_UNAVAILABLE`.

Index-/FTS-Verhalten:

- `document_chunks.search_vector` ist eine PostgreSQL `tsvector` Generated Column.
- Der GIN-Index `ix_document_chunks_search_vector` wird fuer Full Text Search vorbereitet.
- Query-Ausdruck: `plainto_tsquery('simple', q)`.
- Ranking: `ts_rank(document_chunks.search_vector, ts_query)`.

Filterverhalten:

- Es werden nur Chunks aus dem aktiven Workspace des AuthContext geliefert.
- Es werden nur Chunks der aktuellen Dokumentversion geliefert.
- Dokumente mit `import_status in ('parsed', 'chunked')` sind suchbar.
- Es werden nur Dokumente mit `lifecycle_status = 'active'` beruecksichtigt.
- Nur Chunks mit suchbarer Lifecycle-Sicht (`document_chunks.is_searchable = true`) sollen in neuen Search-Treffern auftauchen.
- `pending`, `failed`, `duplicate` und andere Statuswerte werden nicht als Suchtreffer geliefert.

Nachweisgrenze:

- Diese Lifecycle-Filterung ist lokal im Service-, API- und Reindex-Slice belegt.
- Der letzte echte PostgreSQL-Integrationslauf fuer Search/Reindex ist jedoch an `ConnectionTimeout` gegen die konfigurierte Ziel-Datenbank gescheitert.

Sortierlogik:

1. `rank DESC`
2. `document.created_at DESC`
3. `chunk_index ASC`
4. `chunk_id ASC`

Diese Reihenfolge ist Teil des stabilen M3b-Vertrags.

## Fehlercodes

Alle Fehler folgen dem Standardformat:

```json
{
  "error": {
    "code": "INVALID_QUERY",
    "message": "Invalid search query",
    "details": {}
  }
}
```

| HTTP Status | Code | Ursache |
|---:|---|---|
| `422` | `INVALID_QUERY` | `q` fehlt oder ist leer |
| `422` | `INVALID_PAGINATION` | `limit` oder `offset` ist ausserhalb der Grenzen |
| `401` | `AUTH_REQUIRED` | Authentifizierung fehlt |
| `403` | `WORKSPACE_ACCESS_FORBIDDEN` | kein Zugriff auf den aktiven Workspace |
| `503` | `SERVICE_UNAVAILABLE` | Search-Backend ist nicht verfuegbar oder nicht PostgreSQL |
| `500` | `INTERNAL_ERROR` | unerwarteter interner Fehler oder fehlende DB-Konfiguration ausserhalb des Search-Backend-Checks |

## M4a Auth- und Workspace-bezogene Fehlercodes

| HTTP Status | Code | Aktueller Einsatz |
|---:|---|---|
| `401` | `AUTH_REQUIRED` | geschuetzter Endpoint ohne gueltige Authentifizierung |
| `401` | `AUTH_INVALID_CREDENTIALS` | Login mit ungueltigen Zugangsdaten |
| `403` | `WORKSPACE_ACCESS_FORBIDDEN` | authentifiziert, aber kein Zugriff auf den angefragten Workspace |
| `403` | `ADMIN_REQUIRED` | authentifiziert, aber ohne Admin-/Owner-Rolle |
| `422` | `WORKSPACE_REQUIRED` | fehlender Header `x-workspace-id` |

Hinweis:

- `GET /api/v1/admin/diagnostics` verwendet vertragsgemaess `UNAUTHORIZED` und `FORBIDDEN`.
- Andere geschuetzte Endpunkte verwenden weiterhin die aelteren Codes wie `AUTH_REQUIRED`, `WORKSPACE_ACCESS_FORBIDDEN` oder `ADMIN_REQUIRED`.

## Upload Contract

### `POST /documents/import`

Importiert genau eine Datei ueber den bestehenden Dokument-Importpfad.

Sicherheitsgrenzen im aktuellen Stand:

- Der Endpoint ist auth-gebunden.
- `workspace_id` und `requested_by_user_id` kommen aus dem serverseitigen Auth-Kontext.
- Ein serverseitiger Default-Workspace-/Default-User-Fallback ist im Upload-Flow nicht aktiv.
- Upload ohne Auth liefert `401 AUTH_REQUIRED`.
- Upload in fremdem Workspace liefert `403 WORKSPACE_ACCESS_FORBIDDEN`.

Upload-Flow im aktuellen Stand:

1. `POST /documents/import` legt einen `document_import`-Job an.
2. Der Endpoint antwortet sofort mit `202 Accepted` und Jobmetadaten.
3. Das Frontend pollt `GET /api/v1/jobs/{job_id}`.
4. Der Job wechselt ueber `queued` und `running` nach `completed` oder `failed`.
5. Erst der Jobstatus transportiert das eigentliche Importergebnis oder den fachlichen Fehler.

Request:

- `multipart/form-data`
- Feld: `file`

Response `202`:

```json
{
  "id": "job-id",
  "job_type": "document_import",
  "status": "queued",
  "workspace_id": "workspace-id",
  "requested_by_user_id": "user-id",
  "filename": "file.txt",
  "created_at": "2026-05-05T12:00:00Z",
  "started_at": null,
  "finished_at": null,
  "progress_current": 0,
  "progress_total": 1,
  "progress_message": "Import ist in Warteschlange",
  "error_code": null,
  "error_message": null,
  "result": null
}
```

Statusabfrage:

- `GET /api/v1/jobs/{job_id}`

## M4c Lifecycle Contract

### Lifecycle State Machine

Nachweisbar implementierte Transitionen:

- `active -> archived`
- `archived -> active`
- `active -> deleted`
- `archived -> deleted`

Nicht implementiert:

- `deleted -> active`
- `deleted -> archived`
- Hard Delete / Purge

### Verhalten der Dokument-Endpunkte

- `GET /documents` zeigt standardmaessig nur `active`.
- `GET /documents?lifecycle_status=archived` liefert archivierte Dokumente explizit gefiltert.
- `deleted` ist im regulaeren Listenpfad nicht sichtbar.
- `GET /documents/{document_id}` liefert `active` und `archived`.
- `GET /documents/{document_id}` behandelt `deleted` wie nicht vorhanden und liefert `404 DOCUMENT_NOT_FOUND`.
- `PATCH /documents/{document_id}/archive` archiviert nur aktive Dokumente.
- `PATCH /documents/{document_id}/restore` stellt nur archivierte Dokumente wieder her.
- `DELETE /documents/{document_id}` fuehrt Soft Delete aus und laesst Versionen, Chunks und historische Citations bestehen.

### Search-, Chat- und Citation-Verhalten

- Neue Search-Treffer verwenden nur `active`e Dokumente.
- Neues Chat-Retrieval folgt demselben Search-/Retrieval-Pfad und nutzt deshalb nur aktive Dokumente.
- Historische Chat-Citations bleiben in der Chat-API sichtbar, auch wenn das referenzierte Dokument spaeter archiviert oder geloescht wurde.
- Historische Citations tragen dafuer `source_status` wie `active`, `archived`, `deleted` oder `missing`.

Nachweisgrenze:

- Historische Citation-Sichtbarkeit ist direkt ueber API-Tests belegt.
- Fuer neue Chat-Antworten gibt es keinen eigenen Lifecycle-End-to-End-Test; dieses Verhalten ist derzeit nur indirekt ueber Retrieval/Search nachgewiesen.

Fehlgeschlagener Job `200`:

```json
{
  "id": "job-id",
  "job_type": "document_import",
  "status": "failed",
  "workspace_id": "workspace-id",
  "requested_by_user_id": "user-id",
  "filename": "scan.pdf",
  "created_at": "2026-05-05T12:00:00Z",
  "started_at": "2026-05-05T12:00:01Z",
  "finished_at": "2026-05-05T12:00:02Z",
  "progress_current": 1,
  "progress_total": 1,
  "progress_message": "Import fehlgeschlagen",
  "error_code": "OCR_REQUIRED",
  "error_message": "OCR is required but no OCR engine is configured",
  "result": null
}
```

Abgeschlossener Job `200`:

```json
{
  "id": "job-id",
  "job_type": "document_import",
  "status": "completed",
  "workspace_id": "workspace-id",
  "requested_by_user_id": "user-id",
  "filename": "file.txt",
  "created_at": "2026-05-05T12:00:00Z",
  "started_at": "2026-05-05T12:00:01Z",
  "finished_at": "2026-05-05T12:00:02Z",
  "progress_current": 1,
  "progress_total": 1,
  "progress_message": "Import abgeschlossen",
  "error_code": null,
  "error_message": null,
  "result": {
    "document_id": "document-id",
    "version_id": "version-id",
    "import_status": "chunked",
    "duplicate_of_document_id": null,
    "chunk_count": 4,
    "parser_type": "txt-parser",
    "warnings": []
  }
}
```

Response-Felder:

| Feld | Typ | Nullable | Hinweis |
|---|---|---:|---|
| `document_id` | string | nein | Ziel- oder Bestandsdokument |
| `version_id` | string | ja | bei Duplicate kann die bestehende Version geliefert werden |
| `import_status` | string | nein | `pending`, `parsing`, `parsed`, `chunked`, `failed`, `duplicate` |
| `duplicate_of_document_id` | string | ja | gesetzt, wenn bestehendes Dokument wiederverwendet wurde |
| `chunk_count` | integer | nein | Zahl der gespeicherten oder wiedergefundenen Chunks |
| `parser_type` | string | nein | technischer Parser-Identifikator wie `txt-parser` |
| `warnings` | array | nein | strukturierte nicht-fatale Importhinweise |

## Importstatus und Duplicate-Verhalten

Jobstatus:

- `queued`: Upload angenommen, Verarbeitung noch nicht gestartet
- `running`: Importpipeline laeuft
- `completed`: Ergebnis in `result`
- `failed`: Fehler in `error_code` und `error_message`

Fachlicher Importstatus in `result.import_status`:

- `chunked`: neuer Import erfolgreich persistiert und gechunkt
- `duplicate`: bestehendes Dokument wurde wiederverwendet

Duplicate-Vertrag im aktuellen Stand:

- `result.import_status = duplicate`
- `result.duplicate_of_document_id = <bestehende dokument-id>`
- `result.document_id` zeigt weiterhin auf das vorhandene Zieldokument
- der Job selbst bleibt `completed`, weil Duplicate als fachlich erfolgreicher Abschluss gilt

Nachweisgrenze:

- Dieser Vertrag ist im Backend und in sequentiellen Upload-Tests belegt.
- Der vorhandene PostgreSQL-Race-Test fuer parallele Duplicate-Uploads ist aktuell nicht gruen verifiziert, weil der letzte echte PostgreSQL-Lauf infra-blockiert war.

OCR-required-Vertrag im aktuellen Stand:

- OCR-Bedarf liefert keinen `completed`-Duplicate- oder Erfolgsfall
- stattdessen liefert der Job `status = failed` und `error_code = OCR_REQUIRED`
- `result` bleibt `null`

Warning-Eintrag:

```json
{
  "code": "NORMALIZATION_FAILED",
  "message": "...",
  "details": {
    "stage": "normalize",
    "recoverable": true
  }
}
```

Fehlerformat:

```json
{
  "error": {
    "code": "PARSER_FAILED",
    "message": "Document parser failed",
    "details": {}
  }
}
```

Relevante Fehlercodes:

Direkt am Upload-Endpoint:

- `UNSUPPORTED_FILE_TYPE`
- `FILE_TOO_LARGE`
- `AUTH_REQUIRED`
- `WORKSPACE_ACCESS_FORBIDDEN`

Im Jobstatus:

- `PARSER_FAILED`
- `OCR_REQUIRED`
- `IMPORT_FAILED`

Im allgemeinen Fehlerkanon:

- `DUPLICATE_DOCUMENT` ist als Backend-Fehlerklasse vorhanden, wird im normalen Uploadvertrag aber nicht fuer erfolgreiche Duplicate-Faelle verwendet.

`FILE_TOO_LARGE`-Details im aktuellen Vertrag:

```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "Uploaded file exceeds the configured maximum size",
    "details": {
      "max_upload_size_bytes": 52428800,
      "actual_size_bytes": 52428801
    }
  }
}
```

| Status | Code | Bedeutung |
|---:|---|---|
| `415` | `UNSUPPORTED_FILE_TYPE` | Dateityp nicht unterstuetzt |
| `413` | `FILE_TOO_LARGE` | Datei ueberschreitet die konfigurierte Maximalgroesse |
| `422` | `PARSER_FAILED` | Parser oder Normalisierung fehlgeschlagen |
| `422` | `OCR_REQUIRED` | OCR waere erforderlich, ist aber nicht verfuegbar |
| `500` | `IMPORT_FAILED` | Importpfad oder Persistenz ist unerwartet fehlgeschlagen |

Vertragsregeln:

- Es duerfen keine rohen Exceptions an die API durchgereicht werden.
- Die maximale Dateigroesse ist konfigurierbar.
- Der Workspace fuer den Import wird serverseitig aus dem AuthContext abgeleitet; ein Default-Workspace-/Default-User-Fallback ist im Upload-Flow nicht aktiv.

## Upload-bezogene Fehlercodes

| HTTP Status oder Jobstatus | Code | Aktueller Einsatz |
|---|---|---|
| `413` | `FILE_TOO_LARGE` | Datei groesser als `max_upload_file_size_bytes` |
| `415` | `UNSUPPORTED_FILE_TYPE` | Dateiendung oder MIME-Typ nicht unterstuetzt |
| `200` mit Job `failed` | `PARSER_FAILED` | Parser, Normalisierung oder Chunking fehlgeschlagen |
| `200` mit Job `failed` | `OCR_REQUIRED` | PDF enthaelt zu wenig extrahierbaren Text fuer OCR-losen Import |
| `404` | `JOB_NOT_FOUND` | Statusabfrage fuer unbekannte Job-ID |
| n/a | `NETWORK_ERROR` | Frontend erreicht API nicht |

Bekannte Einschraenkungen:

- Duplicate und OCR werden vertraglich sauber transportiert, aber nicht ueber spezialisierte Backend-Endpoints oder UI-Flows getrennt.
- Es gibt keinen Byte-Fortschritt; sichtbar ist nur der Jobzustand.

## M4c Document Lifecycle Contract

Lifecycle-Status:

- `active`
- `archived`
- `deleted`

Lifecycle State Machine:

- `active --archive--> archived`
- `archived --restore--> active`
- `active --delete--> deleted`
- `archived --delete--> deleted`
- `archived --archive--> 409 DOCUMENT_ALREADY_ARCHIVED`
- `active --restore--> 409 INVALID_LIFECYCLE_TRANSITION`
- `deleted --archive--> 409 DOCUMENT_ALREADY_DELETED`
- `deleted --restore--> 409 DOCUMENT_ALREADY_DELETED`
- `deleted --delete--> 409 DOCUMENT_ALREADY_DELETED`

Lifecycle-Regeln:

- `archive` ist nur fuer `active` erlaubt.
- `restore` ist nur fuer `archived` erlaubt.
- `delete` ist immer ein Soft-Delete und loescht keine Versionen, Chunks oder historischen Citations physisch.
- `deleted` ist terminal und ohne explizite Admin-Funktion nicht restorable.
- `active` ist in Liste, Search, Retrieval und Chat verwendbar.
- `archived` ist nur in der Dokumentliste mit Filter sichtbar und wird nicht in Search oder Retrieval einbezogen.
- `deleted` ist weder sichtbar noch direkt abrufbar oder suchbar.
- Bestehende Chat-Citations bleiben historisch sichtbar.

Auswirkungen auf Liste, Suche und Chat:

- Dokumentliste zeigt ohne Filter nur `active`.
- Dokumentdetail, Versions- und Chunk-Read behandeln `deleted` wie `DOCUMENT_NOT_FOUND`.
- Retrieval/Search lassen nur `Document.lifecycle_status == active` zu.
- Neue Chat-Antworten koennen im implementierten Pfad nur Treffer aus dem Search-/Retrieval-Pfad zitieren; ein eigener Lifecycle-Integrationstest fuer Chat ist derzeit nicht vorhanden.
- bestehende Chat-Nachrichten behalten ihre bereits gespeicherten Citations, auch wenn das referenzierte Dokument spaeter archiviert oder geloescht wurde.

### Lifecycle-Felder im Dokumentvertrag

`GET /documents` und `GET /documents/{document_id}` liefern zusaetzlich:

| Feld | Typ | Nullable | Hinweis |
|---|---|---:|---|
| `lifecycle_status` | string | nein | `active`, `archived`, `deleted` |
| `archived_at` | datetime string | ja | Zeitpunkt der Archivierung |
| `deleted_at` | datetime string | ja | Zeitpunkt des Soft-Delete |

### `GET /documents`

Zusaetzliche Query-Parameter:

| Name | Typ | Required | Default | Regel |
|---|---|---:|---:|---|
| `lifecycle_status` | string | nein | - | `active`, `archived`, `deleted` |
| `include_archived` | boolean | nein | `false` | zeigt `archived` nur ohne expliziten Statusfilter zusaetzlich an |

Verhaltensregeln:

- Default ohne Filter: nur `active`
- mit `lifecycle_status=archived`: nur archivierte Dokumente
- `deleted` bleibt im Listenvertrag unsichtbar, auch wenn der Statuswert als Query gesendet wird
- `include_archived=true` erweitert die Defaultliste um archivierte Dokumente, solange kein expliziter `lifecycle_status` gesetzt ist

### `PATCH /documents/{document_id}/archive`

Archiviert genau ein aktives Dokument.

Vertrag:

- erlaubt nur `active -> archived`
- `archived -> archive` liefert `409 DOCUMENT_ALREADY_ARCHIVED`
- `deleted -> archive` liefert `409 DOCUMENT_ALREADY_DELETED`
- unbekannte Dokument-ID liefert `404 DOCUMENT_NOT_FOUND`

Response `200`:

```json
{
  "document_id": "document-id",
  "lifecycle_status": "archived",
  "archived_at": "2026-05-05T12:00:00Z",
  "deleted_at": null
}
```

### `PATCH /documents/{document_id}/restore`

Stellt genau ein archiviertes Dokument wieder auf `active`.

Vertrag:

- erlaubt nur `archived -> active`
- `active -> restore` liefert `409 INVALID_LIFECYCLE_TRANSITION`
- `deleted -> restore` liefert `409 DOCUMENT_ALREADY_DELETED`
- unbekannte Dokument-ID liefert `404 DOCUMENT_NOT_FOUND`

Response `200`:

```json
{
  "document_id": "document-id",
  "lifecycle_status": "active",
  "archived_at": null,
  "deleted_at": null
}
```

### `DELETE /documents/{document_id}`

Fuehrt immer ein Soft-Delete fuer ein `active` oder `archived` Dokument aus.

Vertrag:

- erlaubt `active -> deleted`
- erlaubt `archived -> deleted`
- `deleted -> delete` liefert `409 DOCUMENT_ALREADY_DELETED`
- unbekannte Dokument-ID liefert `404 DOCUMENT_NOT_FOUND`

Response `200`:

```json
{
  "document_id": "document-id",
  "lifecycle_status": "deleted",
  "archived_at": null,
  "deleted_at": "2026-05-05T12:00:00Z"
}
```

Soft-Delete-Regeln:

- `deleted` ist terminal
- Read-API, Liste und Search blenden `deleted` konsequent aus
- Versionen, Chunks und historische Citations bleiben physisch erhalten

Search- und Reindex-Regeln:

- Search bewertet nur Chunks aktiver Dokumente als sichtbar.
- Lifecycle-Uebergaenge synchronisieren `Chunk.is_searchable` fuer vorhandene Chunks.
- Reindex setzt aktive Dokumente wieder suchbar und archivierte oder geloeschte Dokumente wieder unsuchbar.
- Der PostgreSQL-spezifische Reindex-Pfad ist im Service-Slice abgedeckt.
- Ein echter PostgreSQL-Integrationslauf fuer Search und Reindex ist aktuell nicht erfolgreich abgeschlossen, weil die konfigurierte Test-Datenbank im letzten Lauf nicht erreichbar war.

Fehlercodes mit Lifecycle-Bezug:

| HTTP Status | Code | Einsatz |
|---:|---|---|
| `404` | `DOCUMENT_NOT_FOUND` | Dokument ist unbekannt |
| `409` | `INVALID_LIFECYCLE_TRANSITION` | unzulaessiger Transition-Versuch wie `active -> restore` |
| `409` | `DOCUMENT_ALREADY_ARCHIVED` | erneuter Archive-Versuch auf bereits archiviertem Dokument |
| `409` | `DOCUMENT_ALREADY_DELETED` | Aktion auf bereits geloeschtem Dokument oder Restore-Versuch ohne Admin-Funktion |
| `409` | `DOCUMENT_STATE_CONFLICT` | inkonsistenter Dokumentzustand im Read-Pfad |
| `422` | `INVALID_LIFECYCLE_STATUS` | ungueltiger Querywert fuer `lifecycle_status` |

Bekannte Einschraenkungen:

- Es gibt keinen API-Pfad, um soft-geloeschte Dokumente wieder sichtbar zu machen.
- Der Querywert `lifecycle_status=deleted` ist syntaktisch gueltig, bleibt aber fachlich leer, weil geloeschte Dokumente generell ausgeblendet werden.
- Historische Citations koennen auf Dokumente zeigen, die im aktuellen Read-, Search- oder Retrieval-Pfad nicht mehr sichtbar sind; das ist beabsichtigt.
- Fuer neue Chat-Antworten ist Lifecycle nur indirekt ueber den Retrieval-Ausschluss nachgewiesen.

### Lifecycle-Fehler

| Status | Code | Bedeutung |
|---:|---|---|
| `404` | `DOCUMENT_NOT_FOUND` | Dokument fehlt |
| `409` | `INVALID_LIFECYCLE_TRANSITION` | ungueltige Transition fuer den aktuellen Status |
| `409` | `DOCUMENT_ALREADY_ARCHIVED` | Dokument ist bereits archiviert |
| `409` | `DOCUMENT_ALREADY_DELETED` | Dokument ist bereits geloescht oder Restore ist ohne Admin-Funktion unzulaessig |
| `409` | `DOCUMENT_STATE_CONFLICT` | inkonsistenter Dokumentzustand ausserhalb des Lifecycle-Endpunkts |
| `422` | `INVALID_LIFECYCLE_STATUS` | ungueltiger Listenfilter |

Abdeckung durch Tests:

- positiver Pfad fuer `archive`, `restore` und `delete`
- `DOCUMENT_ALREADY_ARCHIVED` bei wiederholtem `archive`
- `INVALID_LIFECYCLE_TRANSITION` bei `restore` auf `active`
- `DOCUMENT_ALREADY_DELETED` bei `archive`, `restore` oder `delete` auf `deleted`
- historische Citation-Snapshots und `source_status` fuer geloeschte Dokumente bleiben sichtbar
- Search schliesst archivierte und geloeschte Dokumente im PostgreSQL-Integrationspfad fachlich aus, der aktuelle End-to-End-Lauf ist aber wegen DB-Erreichbarkeit fehlgeschlagen

## M3c Chat Contract

### `POST /api/v1/chat/sessions`

Erstellt eine Chat-Session.

Request:

```json
{
  "title": "Arbeitsvertrag"
}
```

Response `201` `ChatSessionSummary`:

```json
{
  "id": "session-id",
  "workspace_id": "workspace-1",
  "title": "Arbeitsvertrag",
  "created_at": "2026-05-01T12:00:00Z",
  "updated_at": "2026-05-01T12:00:00Z"
}
```

### `GET /api/v1/chat/sessions`

Listet Sessions eines Workspaces.

## M4d Read-only Admin Diagnostics

Der aktuell nachweisbare M4d-Slice ist **read-only vorbereitet**, aber M4d ist nicht vollstaendig abgeschlossen. Mutierende Admin-Aktionen bleiben blockiert, bis M4a, M4b und M4c ihre Gates erreicht haben.

Nachweisbar implementiert:

- `GET /api/v1/admin/diagnostics`
- `GET /api/v1/admin/search-index/inconsistencies`
- `POST /api/v1/admin/search-index/rebuild` als blockierter Pfad mit `501 ADMIN_ACTION_NOT_IMPLEMENTED`

Nicht freigegeben:

- Reindex ausloesen
- Cleanup ausloesen
- Backup ausloesen
- Restore ausloesen
- User verwalten
- Workspace mutieren
- Dokumente reparieren

Admin-Job-Replay:

- `POST /api/v1/admin/jobs/{job_id}/replay` ist fuer `dead_letter`- und `retryable`-Jobs verfuegbar.
- Die Response behaelt die letzte Fehlerursache in `previous_error`.
- Replay-Audits bleiben in `replay_history` sichtbar mit `previous_error_code`, `previous_error_message`, `replayed_at` und `replayed_by_user_id`.

### `GET /api/v1/admin/diagnostics`

Liefert eine redigierte read-only Systemdiagnose fuer Administratoren.

Autorisierung:

- gueltige Session/AuthContext erforderlich
- aktiver Workspace aus dem Request-Kontext erforderlich
- Admin- oder Owner-Rolle im aktiven Workspace erforderlich

Response `200`:

```json
{
  "system": {
    "status": "ok",
    "version": "0.1.0",
    "environment": "local"
  },
  "database": {
    "reachable": true,
    "migration_head": "20260505_0016",
    "current_revision": "20260505_0016",
    "is_current": true
  },
  "counts": {
    "documents": 0,
    "versions": 0,
    "chunks": 0,
    "chat_sessions": 0,
    "chat_messages": 0
  },
  "imports": {
    "running_jobs": 0,
    "failed_jobs_last_24h": 0,
    "last_error_code": null
  },
  "search": {
    "index_available": true,
    "indexed_chunks": 0,
    "stale_index_entries": 0
  },
  "auth": {
    "auth_enabled": true,
    "workspace_isolation_enabled": true
  }
}
```

Vertragsregeln:

- nur aggregierte Kennzahlen und redigierte technische Statuswerte
- keine Reparaturaktionen oder Job-Erzeugung
- keine Reindex-, Cleanup- oder Backup-Aktionen
- keine Dokumenttexte, keine Chunk-Texte, keine Dokumenttitel, keine Prompts, keine Chat-Fragen oder Chat-Antworten
- keine Secrets, Tokens, Header-Werte, Connection-Strings oder lokalen Dateipfade
- der Workspace wird serverseitig aus dem AuthContext abgeleitet

Fehler:

| Status | Code | Bedeutung |
|---:|---|---|
| `401` | `UNAUTHORIZED` | keine gueltige Session |
| `403` | `FORBIDDEN` | kein Admin- oder Owner-Zugriff oder fremder Workspace |
| `500` | `DIAGNOSTICS_FAILED` | Diagnosedaten konnten nicht redigiert aufgebaut werden |

### `POST /api/v1/admin/search-index/rebuild`

Dieser Pfad ist fuer M4d read-only nicht freigegeben.

Response:

- `501 ADMIN_ACTION_NOT_IMPLEMENTED`

Die fruehere Rebuild-Aktion bleibt erst nach erfolgreichem M4a/M4b/M4c-Gate wieder entscheidbar.

## M4e Backup and Restore Proposal

M4e ist bewusst CLI-first. Restore wird nicht als normaler Endnutzer-HTTP-Flow definiert.

Aktueller Status:

- Die folgenden CLI-Befehle und Admin-Endpunkte sind derzeit Vorschlag und nicht als reale Implementierung im Repository nachgewiesen.
- Es gibt aktuell keinen nachweisbaren produktiven Backup- oder Restore-Codepfad.

Empfohlene CLI-Befehle:

- `python -m app.cli backup create --output <path>`
- `python -m app.cli backup validate --input <path>`
- `python -m app.cli backup restore --input <path> --target <env>`
- `python -m app.cli search rebuild-index`

Optionale spaetere Admin-API:

- `POST /api/v1/admin/backups`
- `POST /api/v1/admin/backups/validate`
- `POST /api/v1/admin/search/rebuild-index`

Vertragsregeln:

- Backup umfasst Datenbank, technische Originaldatei-Kopien und Konfiguration.
- Search-Index ist rekonstruierbar und kein Pflichtbestandteil des Backup-Artefakts.
- Restore schliesst stets Integritaetspruefung und `alembic upgrade head` ein.
- Diagnostics- oder Backup-Pfade duerfen keine Dokumenttexte offenlegen.

Query Parameter:

| Name | Typ | Required | Default | Limit / Regel |
|---|---|---:|---:|---|
| `limit` | integer | nein | `20` | `1..100` |
| `offset` | integer | nein | `0` | `>= 0` |

Der Workspace wird serverseitig aus dem AuthContext abgeleitet.

Response `200`:

```json
[
  {
    "id": "session-id",
    "workspace_id": "workspace-1",
    "title": "Arbeitsvertrag",
    "created_at": "2026-05-01T12:00:00Z",
    "updated_at": "2026-05-01T12:00:00Z"
  }
]
```

### `GET /api/v1/chat/sessions/{session_id}`

Liefert Session-Metadaten mit Messages.

Response `200` `ChatSessionDetail`:

```json
{
  "id": "session-id",
  "workspace_id": "workspace-1",
  "title": "Arbeitsvertrag",
  "created_at": "2026-05-01T12:00:00Z",
  "updated_at": "2026-05-01T12:10:00Z",
  "messages": [
    {
      "id": "message-id",
      "session_id": "session-id",
      "role": "assistant",
      "content": "Antwort mit Quelle chunk-1.",
      "basis_type": "knowledge_base",
      "created_at": "2026-05-01T12:10:00Z",
      "citations": [
        {
          "chunk_id": "chunk-1",
          "document_id": "document-1",
          "document_title": "Document title",
          "source_anchor": {
            "type": "text",
            "page": null,
            "paragraph": 4,
            "char_start": 10,
            "char_end": 130
          },
          "quote_preview": "Historischer Quellen-Snapshot",
          "source_status": "active"
        }
      ],
      "confidence": null
    }
  ]
}
```

### `POST /api/v1/chat/sessions/{session_id}/messages`

Fuehrt den M3c-RAG-Flow aus. Der Endpoint speichert zuerst die User-Frage, fuehrt Retrieval und RAG-Orchestrierung aus und speichert bei ausreichendem Kontext eine Assistant-Antwort mit Citations.

Request:

```json
{
  "question": "Welche Kuendigungsfrist gilt nach der Probezeit?",
  "retrieval_limit": 8
}
```

Felder:

| Feld | Typ | Required | Default | Limit / Regel |
|---|---|---:|---:|---|
| `question` | string | ja | - | `min_length=1` |
| `retrieval_limit` | integer | nein | `8` | `1..100` |

Response `201` `ChatMessageResponse` fuer die Assistant-Antwort:

```json
{
  "id": "assistant-message-id",
  "session_id": "session-id",
  "role": "assistant",
  "content": "Die Frist betraegt vier Wochen zum Monatsende. Quelle: chunk-1",
  "basis_type": "knowledge_base",
  "created_at": "2026-05-01T12:10:00Z",
  "citations": [
    {
      "chunk_id": "chunk-1",
      "document_id": "document-1",
      "document_title": "Document title",
      "source_anchor": {
        "type": "text",
        "page": null,
        "paragraph": 4,
        "char_start": 10,
        "char_end": 130
      },
      "quote_preview": "Nach der Probezeit gilt eine Kuendigungsfrist von vier Wochen zum Monatsende.",
      "source_status": "active"
    }
  ],
  "confidence": {
    "sufficient_context": true,
    "retrieval_score_max": 0.92,
    "retrieval_score_avg": 0.92
  }
}
```

Wichtig:

- Der Response enthaelt nicht die User-Message. Die User-Frage wird serverseitig persistiert; die GUI ergaenzt sie lokal im Verlauf und kann die Session danach erneut laden.
- Eine erfolgreiche Assistant-Antwort muss mindestens eine Citation mit `chunk_id` enthalten.
- Bei unzureichendem Kontext wird keine freie Assistant-Antwort erzeugt.

## M3c Fehlercodes

Alle Chat/RAG-Fehler verwenden das gleiche Standardformat:

```json
{
  "error": {
    "code": "INSUFFICIENT_CONTEXT",
    "message": "no_retrieval_hits",
    "details": {
      "session_id": "session-id"
    }
  }
}
```

| HTTP Status | Code | Ursache |
|---:|---|---|
| `404` | `CHAT_SESSION_NOT_FOUND` | Session existiert nicht |
| `422` | `WORKSPACE_REQUIRED` | Header `x-workspace-id` fehlt oder ist leer |
| `422` | `CHAT_MESSAGE_INVALID` | `question` oder `retrieval_limit` ungueltig |
| `422` | `INSUFFICIENT_CONTEXT` | Retrieval-/Kontextlage reicht nicht fuer belegte Antwort |
| `500` | `CHAT_PERSISTENCE_FAILED` | Speichern von Session, Message oder Citation fehlgeschlagen |
| `502` | `RETRIEVAL_FAILED` | Retrieval-Service fehlgeschlagen |
| `503` | `LLM_UNAVAILABLE` | LLM Provider nicht verfuegbar oder leere Antwort |

## Nicht-Scope fuer M3b Search

- kein Chat
- keine LLM-Antwort
- keine Embeddings
- keine semantische Suche
- kein Re-Ranking
- keine Query-Filter ausser `q`, `limit`, `offset`
- keine Schreiboperationen

## Von der GUI verwendete Vertragsmerkmale

- Dokumentliste mit `title`, `mime_type`, `created_at`, `updated_at`, `latest_version_id`, `import_status`, `version_count`, `chunk_count`
- Dokumentdetail mit Stammdaten, `latest_version`, `parser_metadata`, `import_status`, `chunk_summary`
- Versionen mit `id`, `version_number`, `created_at`, `content_hash`
- Chunks mit `chunk_id`, `position`, `text_preview`, `source_anchor`
- Suchtreffer mit `document_id`, `document_title`, `document_created_at`, `document_version_id`, `version_number`, `chunk_id`, `position`, `text_preview`, `source_anchor`, `rank`, `filters`
- Chat-Sessions mit `id`, `workspace_id`, `title`, `created_at`, `updated_at`
- Chat-Assistant-Antworten mit `content`, `citations`, `confidence`
- Standardisiertes Fehlerformat `error.code`, `error.message`, `error.details`

## Offene Punkte

- Der Alias `/api/v1/documents` ist weiter nicht implementiert.
- M3b Search hat PostgreSQL-Integrationstests, wird aber ohne `TEST_DATABASE_URL` geskippt.
- M3c nutzt aktuell einen austauschbaren LLM-Provider-Vertrag; ein produktiver LLM-Provider ist M4-Scope.
- Streaming, Agenten, Tool Use, Embeddings und Dokumentmutation sind nicht Teil von M3c.
