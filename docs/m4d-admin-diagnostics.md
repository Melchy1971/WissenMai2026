# M4d - Admin- und Diagnoseansicht

Stand: 2026-05-07

## M4d Minimal Scope - Read-only Systemdiagnose

M4d wird bis zum Abschluss von M4a, M4b und M4c nur als **read-only Systemdiagnose** definiert. M4d darf parallel vorbereitet werden, darf aber keine Reparatur-, Reindex-, Cleanup-, Backup-, User- oder Workspace-Aktionen produktiv freischalten.

Dieser Abschnitt ist der aktuell gueltige M4d-Vertrag. Weiter unten beschriebene Admin- oder Maintenance-Zielbilder sind nur spaetere Ausbaustufen und gelten nicht als freigegeben.

### Minimaler In-Scope

- Systemstatus lesen
- DB-Verbindung pruefen
- Migration Head pruefen
- Dokumentanzahl lesen
- Chunkanzahl lesen
- Import-Job-Status lesen
- Search-Index-Status lesen
- letzte redigierte Fehler anzeigen
- Health Summary read-only anzeigen

### Stabiler read-only API-Vertrag

#### `GET /api/v1/admin/diagnostics`

Status:

- Minimalvertrag fuer M4d read-only.
- Darf parallel zu M4a/M4b/M4c vorbereitet werden.
- Liefert ausschliesslich aggregierte, redigierte Betriebsdaten.
- Darf keine Mutationen, Reparaturen oder Job-Enqueues ausloesen.
- Der Response-Vertrag ist stabil. Neue Felder duerfen spaeter nur kompatibel ergaenzt werden; bestehende Felder, Typen und Bedeutungen duerfen ohne neue API-Version nicht geaendert werden.

Auth:

- authentifizierte Session erforderlich
- aktiver Workspace-Kontext erforderlich
- Rolle `owner` oder `admin` im aktiven Workspace erforderlich

Constraints:

- keine Dokumenttexte
- keine Chunktexte
- keine Chat-Inhalte
- keine Prompts oder LLM-Antworten
- keine Secrets, Tokens, Header-Werte, Connection-Strings oder lokalen Dateipfade
- keine frei vom Client steuerbaren Workspace-Wechsel innerhalb des Diagnose-Endpunkts
- read-only: keine Writes, keine Locks, keine Job-Erzeugung, keine Reparatur- oder Admin-Aktion

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
    "head_revision": "20260505_0016",
    "current_revision": "20260505_0016",
    "is_current": true
  },
  "counts": {
    "documents": 128,
    "versions": 132,
    "chunks": 6421,
    "chat_sessions": 14,
    "chat_messages": 93
  },
  "imports": {
    "running_jobs": 0,
    "failed_jobs_last_24h": 2,
    "last_error_code": "PARSER_FAILED"
  },
  "search": {
    "index_available": true,
    "indexed_chunks": 6421,
    "stale_index_entries": 0
  },
  "auth": {
    "auth_enabled": true,
    "workspace_isolation_enabled": true
  }
}
```

#### Response Schema

Top-Level:

| Feld | Typ | Nullable | Bedeutung |
|---|---|---:|---|
| `system` | object | nein | API-/Runtime-Zustand ohne Secrets |
| `database` | object | nein | DB-Erreichbarkeit und Alembic-Revisionszustand |
| `counts` | object | nein | aggregierte Zaehler im aktiven Workspace |
| `imports` | object | nein | aggregierter Import-Job-Zustand |
| `search` | object | nein | read-only Search-Index-Zustand |
| `auth` | object | nein | aktivierte Sicherheitsgrenzen |

`system`:

| Feld | Typ | Nullable | Bedeutung |
|---|---|---:|---|
| `status` | `"ok"` \| `"degraded"` \| `"error"` | nein | Gesamtstatus der Diagnose |
| `version` | string | nein | API-/Build-Version, z. B. FastAPI-App-Version |
| `environment` | `"local"` \| `"test"` \| `"production"` | nein | redigierter Laufzeitkontext |

`database`:

| Feld | Typ | Nullable | Bedeutung |
|---|---|---:|---|
| `reachable` | boolean | nein | `true`, wenn ein einfacher DB-Read erfolgreich ist |
| `head_revision` | string \| null | ja | Alembic-Head, falls bestimmbar |
| `current_revision` | string \| null | ja | aktuell angewandte DB-Revision, falls bestimmbar |
| `is_current` | boolean | nein | `true`, wenn `current_revision == head_revision` |

`counts`:

| Feld | Typ | Nullable | Bedeutung |
|---|---|---:|---|
| `documents` | integer | nein | Dokumente im aktiven Workspace |
| `versions` | integer | nein | Dokumentversionen im aktiven Workspace |
| `chunks` | integer | nein | Chunks im aktiven Workspace |
| `chat_sessions` | integer | nein | Chat-Sessions im aktiven Workspace |
| `chat_messages` | integer | nein | Chat-Nachrichten im aktiven Workspace |

`imports`:

| Feld | Typ | Nullable | Bedeutung |
|---|---|---:|---|
| `running_jobs` | integer | nein | laufende `document_import` Jobs im aktiven Workspace |
| `failed_jobs_last_24h` | integer | nein | fehlgeschlagene `document_import` Jobs der letzten 24 Stunden |
| `last_error_code` | string \| null | ja | letzter redigierter Import-Fehlercode, keine Fehlermeldung mit Dateinamen |

`search`:

| Feld | Typ | Nullable | Bedeutung |
|---|---|---:|---|
| `index_available` | boolean | nein | Search-Index/FTS-Pruefung verfuegbar |
| `indexed_chunks` | integer | nein | suchbare/indexierte Chunks im aktiven Workspace |
| `stale_index_entries` | integer | nein | stale oder inkonsistente Indexeintraege, soweit read-only bestimmbar |

`auth`:

| Feld | Typ | Nullable | Bedeutung |
|---|---|---:|---|
| `auth_enabled` | boolean | nein | Auth-Middleware/Session-Kontext aktiv |
| `workspace_isolation_enabled` | boolean | nein | Workspace-Kontext wird serverseitig erzwungen |

#### Fehlervertrag

| Status | Code | Bedeutung |
|---:|---|---|
| `401` | `UNAUTHORIZED` | keine gueltige Session oder Authentifizierung fehlt |
| `403` | `FORBIDDEN` | Benutzer ist kein Admin/Owner im aktiven Workspace |
| `500` | `DIAGNOSTICS_FAILED` | Diagnose konnte nicht stabil aufgebaut werden |

Error Envelope:

```json
{
  "error": {
    "code": "DIAGNOSTICS_FAILED",
    "message": "Diagnostics failed",
    "details": {
      "failed_check": "database"
    }
  }
}
```

Fehlerdetails muessen redigiert bleiben. `details` darf keine Secrets, Connection-Strings, Dateipfade, Dokumenttitel, Dokumenttexte, Chunktexte, Prompts oder Chat-Inhalte enthalten.

#### Bereits vorhandene verwertbare Daten im Code

| Diagnosepunkt | Ist-Quelle | Status |
|---|---|---|
| Systemstatus | `GET /health`, `GET /api/v1/health` | vorhanden |
| DB-Verbindung | `GET /health/db`, `app.core.database.check_database_connection()` | vorhanden |
| Migration Head | Alembic unter `backend/migrations`, Tests in `backend/tests/integration/test_migrations.py` | pruefbar, noch kein Admin-API-Aggregat |
| Dokumentanzahl | `documents` Modell/Repository | vorhanden, Aggregat fehlt |
| Chunkanzahl | `document_chunks` Modell/Repository | vorhanden, Aggregat fehlt |
| Import-Job-Status | `background_jobs` Modell, `GET /api/v1/jobs/{job_id}` | vorhanden fuer Einzeljob, Aggregat fehlt |
| Search-Index-Status | `GET /api/v1/admin/search-index/inconsistencies` | vorhanden, read-only |
| Letzte Fehler | `background_jobs.error_code/error_message`, Observability-Logging | teilweise vorhanden, redigiertes Aggregat fehlt |
| Health Summary | Health-Endpunkte plus obige Quellen | Zielaggregat fehlt |

### Nicht-Scope fuer M4d read-only

- Reindex ausloesen
- Cleanup ausloesen
- Backup ausloesen
- Restore ausloesen
- User verwalten
- Workspace erstellen, wechseln, bearbeiten oder loeschen
- Dokumente reparieren, wiederherstellen oder mutieren
- freie SQL-/Admin-Kommandos
- Anzeige von Dokumenttexten, Chunktexten, Prompts, Chatantworten, Secrets, Tokens, Connection-Strings oder lokalen Dateipfaden

### Freigabeabhaengigkeiten

- M4d read-only darf parallel zu M4a, M4b und M4c vorbereitet und getestet werden.
- M4d write/admin actions bleiben bis zum erfolgreichen M4a/M4b/M4c-Gate deaktiviert oder `not_implemented`.
- Erst nach M4a-Gate duerfen Admin-Aktionen auf den finalen Auth-/Workspace-Kontext bauen.
- Erst nach M4b-Gate duerfen Import- und Job-Aktionen produktiv erweitert werden.
- Erst nach M4c-Gate duerfen Lifecycle-nahe Reparatur-, Reindex- oder Restore-Aktionen produktiv freigegeben werden. Quelle: `reports/current/masterplan_status.json`.
- Jede spaetere mutierende Admin-Aktion braucht einen eigenen API-Vertrag, Auth-Test, Audit-/Observability-Regel und Rollback-/Failure-Mode-Dokumentation.

### Aktuelle Code-Markierung

- `POST /api/v1/admin/search-index/rebuild` ist serverseitig als `501 ADMIN_ACTION_NOT_IMPLEMENTED` markiert.
- Die Admin-Diagnostics-UI rendert keine Reindex-, Cleanup-, Backup- oder sonstigen mutierenden Admin-Aktionsbuttons.
- `GET /api/v1/admin/search-index/inconsistencies` bleibt als read-only Diagnosequelle verfuegbar.

## Realer Status am 2026-05-07

- Real implementiert sind aktuell der read-only Inconsistency-Report, Health-Endpunkte und Observability-Slices.
- Die vorher produktiv erreichbare Search-Index-Rebuild-Aktion ist fuer M4d read-only deaktiviert und antwortet mit `501 ADMIN_ACTION_NOT_IMPLEMENTED`.
- Die Frontend-Seite `/admin/diagnostics` existiert und bildet den read-only Diagnostics-Aggregatvertrag ab; mutierende Aktionsbuttons werden nicht gerendert.
- Nicht real implementiert ist ein aggregierter Backend-Endpunkt `GET /api/v1/admin/diagnostics` mit den unten beschriebenen Statuskarten.
- Dieses Dokument beschreibt daher den Minimalvertrag plus vorhandene Teilquellen; ein breiteres Zielbild ist noch nicht freigegeben.

## Ziel

M4d macht den operativen Systemzustand fuer Administratoren sichtbar, ohne fachliche Inhalte oder sensible Daten offenzulegen. Die Diagnoseansicht ist eine Betriebsoberflaeche fuer Verfuegbarkeit, Datenqualitaet, Importstabilitaet, Search-Bereitschaft und Chat-/RAG-Stabilitaet.

Die Ansicht ist explizit kein allgemeines Reporting-Dashboard und keine Entwicklerkonsole.

## Scope

In Scope:

- Backend-Diagnose-Endpunkt fuer aggregierte Systemkennzahlen
- Admin-Seite unter `/admin/diagnostics`
- Statuskarten fuer Kernkomponenten
- Fehlerliste mit redigierten technischen Details
- kopierbare technische Details fuer Support und Betrieb

Nicht in Scope:

- Dokumentinhalte oder Chunk-Texte
- Roh-Stacktraces in der UI
- Benutzerbezogene personenbezogene Details
- freie SQL- oder Admin-Operations
- Mandantenuebergreifende Detail-Exporte

## Sicherheits- und Datenschutzregeln

Admin-Zugriff:

- Zugriff nur fuer authentifizierte Benutzer mit Admin-Berechtigung.
- Enforcement serverseitig ueber M4a-Auth- und Membership-Kontext.
- Frontend darf Admin-Zugriff nicht nur ueber Routing oder UI-Verstecken modellieren.

Datensparsamkeit:

- Keine Dokumenttitel, keine Dokumenttexte, keine Chunk-Texte.
- Keine Prompt-Inhalte, keine Chat-Nachrichten, keine Dateinamen einzelner fehlgeschlagener Uploads.
- Keine rohen Connection-Strings, Secrets, Tokens oder Dateisystempfade.

Zulaessig sind nur aggregierte Kennzahlen, redigierte Fehlercodes und redigierte technische Hinweise.

## Backend Diagnostics API

Status:

- Zielvertrag, derzeit nicht real implementiert.

### Endpoint

- `GET /api/v1/admin/diagnostics`

Zweck:

- Liefert eine redigierte Systemdiagnose fuer die Admin-Oberflaeche.

### Auth und Autorisierung

Anforderungen:

- authentifizierte Session erforderlich
- aktiver Workspace-Kontext serverseitig aufgeloest
- Membership-Rolle `admin` oder `owner` erforderlich

Fehler:

| Status | Code | Bedeutung |
|---:|---|---|
| `401` | `AUTH_REQUIRED` | keine gueltige Session |
| `403` | `ADMIN_REQUIRED` | Benutzer ist kein Admin/Owner |
| `503` | `SERVICE_UNAVAILABLE` | Diagnose kann wegen Infrastrukturfehler nicht vollstaendig aufgebaut werden |

### Response `200`

```json
{
  "generated_at": "2026-05-05T14:00:00Z",
  "workspace_scope": "workspace-1",
  "overall_status": "degraded",
  "cards": {
    "database": {
      "status": "ok",
      "label": "DB erreichbar",
      "details": {
        "reachable": true,
        "latency_ms": 18
      }
    },
    "migrations": {
      "status": "ok",
      "label": "Migration Head aktuell",
      "details": {
        "current_revision": "20260505_0013",
        "head_revision": "20260505_0013",
        "at_head": true
      }
    },
    "documents": {
      "status": "ok",
      "label": "Dokumente und Chunks",
      "details": {
        "document_count": 128,
        "chunk_count": 6421,
        "archived_document_count": 12,
        "deleted_document_count": 3
      }
    },
    "imports": {
      "status": "warning",
      "label": "Import-Stabilitaet",
      "details": {
        "parser_error_rate_24h": 0.083,
        "successful_imports_24h": 44,
        "failed_imports_24h": 4,
        "last_imports": [
          {
            "import_id": "imp-1",
            "finished_at": "2026-05-05T13:42:00Z",
            "status": "failed",
            "error_code": "PARSER_FAILED"
          },
          {
            "import_id": "imp-2",
            "finished_at": "2026-05-05T13:40:00Z",
            "status": "chunked",
            "error_code": null
          }
        ]
      }
    },
    "search": {
      "status": "ok",
      "label": "Search Index",
      "details": {
        "backend": "postgresql_fts",
        "index_ready": true,
        "missing_search_vectors": 0,
        "stale_current_documents": 0
      }
    },
    "chat_rag": {
      "status": "warning",
      "label": "Chat/RAG",
      "details": {
        "chat_error_rate_24h": 0.041,
        "retrieval_error_rate_24h": 0.018,
        "llm_unavailable_rate_24h": 0.006
      }
    }
  },
  "errors": [
    {
      "id": "diag-1",
      "severity": "warning",
      "source": "imports",
      "code": "PARSER_FAILED",
      "message": "Parser-Fehlerquote der letzten 24h liegt ueber dem Grenzwert.",
      "technical_details": {
        "window_hours": 24,
        "failed_imports": 4,
        "successful_imports": 44,
        "threshold": 0.05
      }
    }
  ]
}
```

### Response-Felder

Top-Level:

| Feld | Typ | Nullable | Hinweis |
|---|---|---:|---|
| `generated_at` | datetime string | nein | serverseitiger Erstellungszeitpunkt |
| `workspace_scope` | string | nein | aktiver Workspace-Kontext, nicht frei vom Client gesetzt |
| `overall_status` | `ok` \| `warning` \| `degraded` \| `error` | nein | aggregierter Gesamtzustand |
| `cards` | object | nein | gruppierte Statuskarten |
| `errors` | array | nein | redigierte Fehlerliste |

Statuskarte:

| Feld | Typ | Nullable | Hinweis |
|---|---|---:|---|
| `status` | `ok` \| `warning` \| `degraded` \| `error` | nein | Ampelzustand |
| `label` | string | nein | UI-Label |
| `details` | object | nein | redigierte Kennzahlen |

Fehlerliste:

| Feld | Typ | Nullable | Hinweis |
|---|---|---:|---|
| `id` | string | nein | stabile Diagnose-ID |
| `severity` | `info` \| `warning` \| `error` | nein | Sortierung und UI-Farbe |
| `source` | string | nein | `database`, `migrations`, `imports`, `search`, `chat_rag` |
| `code` | string | nein | technischer Fehlercode |
| `message` | string | nein | redigierte menschenlesbare Meldung |
| `technical_details` | object | nein | kopierbare, aber redigierte Betriebshinweise |

## Definition der Kennzahlen

DB erreichbar:

- einfacher Lese- oder Ping-Check gegen die aktive Datenbank
- optional `latency_ms`
- keine DSN-Ausgabe

Migration Head aktuell:

- Vergleich zwischen aktueller Alembic-Revision und Head-Revision
- nur Revisionskennungen ausgeben, keine Dateipfade

Dokumentanzahl:

- Anzahl `active` plus `archived` Dokumente im aktiven Workspace
- getrennte Zaehlung fuer `archived` und `deleted` erlaubt

Chunkanzahl:

- Anzahl persistierter Chunks im aktiven Workspace
- keine Detailverteilung nach Dokument in M4d erforderlich

Parser-Fehlerquote:

- Anteil fehlgeschlagener Importe im letzten 24h-Fenster
- Grundlage: Import-Status und importbezogene Fehlercodes
- keine Dateinamen einzelner Fehlerfaelle anzeigen

Search Index Status:

- Backend-Typ, z. B. `postgresql_fts`
- Index bereit oder nicht bereit
- Anzahl Dokumente mit fehlender Search-Indexierbarkeit fuer aktuelle Versionen

Letzte Imports:

- nur redigierte Metadaten
- `import_id`, `finished_at`, `status`, `error_code`
- keine Dateinamen, keine Dokumenttitel, keine Inhalte

Chat/RAG Fehlerquote:

- Fehleranteile fuer Chat-Persistenz, Retrieval und LLM-Verfuegbarkeit im letzten 24h-Fenster
- keine Prompts, keine Antworten, keine Zitateinhalte

## UI-Spezifikation

### Route

- `/admin/diagnostics`

### Page-Zweck

- Admins sehen die Betriebsbereitschaft des Systems auf einen Blick.
- Die Seite dient als Startpunkt fuer Diagnose und Support, nicht fuer fachliche Datenanalyse.

### Layout

Bereiche:

- Kopfbereich mit Seitentitel `Systemdiagnose`
- Statuskarten-Raster
- Fehlerliste
- Bereich `Technische Details` mit kopierbarem JSON oder Key-Value-Block

### Statuskarten

Pflichtkarten:

- `DB erreichbar`
- `Migration Head aktuell`
- `Dokumente und Chunks`
- `Import-Stabilitaet`
- `Search Index`
- `Chat/RAG`

Verhalten:

- Jede Karte zeigt genau einen Status und 2 bis 5 Kernkennzahlen.
- Status-Farblogik: gruen, gelb, orange, rot fuer `ok`, `warning`, `degraded`, `error`.
- Keine expandierten Rohdaten in der Karte selbst.

### Fehlerliste

Inhalt pro Zeile:

- Severity-Badge
- Quelle
- Fehlercode
- kurze menschenlesbare Meldung
- Aktion `Technische Details kopieren`

Sortierung:

- zuerst `error`, dann `warning`, dann `info`
- innerhalb derselben Severity nach Aktualitaet

Leerer Zustand:

- Hinweis `Keine aktuellen Diagnosefehler`

### Technische Details

Zweck:

- Support-faehige Informationen kopierbar machen, ohne sensible Daten freizugeben.

Darstellung:

- kompakter Monospace-Block oder JSON-Viewer
- Button `Kopieren`
- nur redigierte Werte aus `technical_details`

Explizit verboten:

- Dokumenttext
- Chunk-Preview
- Prompt- oder Antworttexte
- Stacktraces mit lokalen Pfaden
- Secrets oder Header-Werte

### Loading, Error und Access States

Loading:

- Skeletons fuer Karten und Fehlerliste

403 State:

- klare Meldung `Kein Admin-Zugriff`
- kein Fallback auf technische Rohantwort im UI

503 State:

- degradierter Diagnosehinweis `Diagnosedaten konnten nicht vollstaendig geladen werden`
- wenn vorhanden, partielle Karten weiter anzeigen

## Frontend-ViewModels

### `DiagnosticsOverviewVM`

Felder:

- `generatedAt`
- `workspaceScope`
- `overallStatus`
- `cards`
- `errors`
- `hasBlockingError`

### `DiagnosticsCardVM`

Felder:

- `id`
- `title`
- `status`
- `primaryMetric`
- `secondaryMetrics`
- `copyPayload`

### `DiagnosticsErrorItemVM`

Felder:

- `id`
- `severity`
- `source`
- `code`
- `message`
- `technicalDetails`
- `copyText`

## Teststrategie

### Backend-Tests

Contract-Tests:

- `GET /api/v1/admin/diagnostics` liefert stabile Top-Level-Felder
- Kartenstruktur bleibt stabil, auch wenn einzelne Teilchecks `warning` oder `error` sind
- Response enthaelt keine Dokumenttitel, keine Dateinamen, keine Dokumenttexte

Auth-Tests:

- `401 AUTH_REQUIRED` ohne Session
- `403 ADMIN_REQUIRED` fuer Nicht-Admin
- `200` fuer Admin

Metric-Tests:

- DB-Check mappt erreichbar versus nicht erreichbar korrekt
- Migration-Check erkennt `at_head` korrekt
- archivierte und geloeschte Dokumente verfremden die Sichtbarkeit nicht, aber die Zaehlung bleibt konsistent
- Search-Index-Status erkennt fehlende oder stale Indexierung
- Parser-Fehlerquote und Chat/RAG-Fehlerquote werden fuer ein definiertes Zeitfenster korrekt berechnet

Redaction-Tests:

- keine Dokumenttexte im Payload
- keine Prompt-/Antworttexte im Payload
- keine Secrets oder Connection-Strings im Payload

### Frontend-Tests

Routing:

- `/admin/diagnostics` ist nur fuer Admin-Nutzer erreichbar
- Nicht-Admin sieht den `403`-State

Rendering:

- alle Pflichtkarten werden gerendert
- Fehlerliste zeigt Severity, Code und Meldung
- leere Fehlerliste zeigt Empty State

Copy-Interaktion:

- `Technische Details kopieren` kopiert nur redigierte Details
- kopierter Inhalt enthaelt keine Dokumentinhalte

Resilienz:

- partielle Backend-Fehler fuehren nicht zum Komplettabsturz der Seite
- `503` und Netzwerkfehler haben klaren Fallback-State

## Akzeptanzkriterien

- Admin sieht auf einer Seite die Betriebsbereitschaft von DB, Migration, Import, Search und Chat/RAG.
- Nicht-Admin kann die Diagnoseansicht weder direkt noch indirekt nutzen.
- Die UI zeigt keine sensiblen Inhalte und keine Dokumenttexte.
- Technische Details sind kopierbar, aber redigiert.
- Backend- und Frontend-Tests decken Auth, Vertragsstabilitaet, Redaction und Fehlerfaelle ab.
