# Hartes Abschluss-Gate: Paket 5

Stand: 2026-05-04

Hinweis zum Dokumentstatus:

- Dieses Dokument beschreibt das historische Abschluss-Gate fuer Paket 5.
- Es ist weiterhin als M3-Basis relevant, aber keine aktuelle Quelle fuer M4/M5-Freigabeentscheidungen.
- Fuer den aktuellen M4/M5-Stand sind `docs/m4-m5-freigabefassung.md`, `reports/current/m4_truth_report.json`, `reports/current/m4e_backup_restore_truth.json` und `masterplan.md` massgeblich.

Dieses Gate bewertet, ob Paket 5 freigegeben werden darf. Code, Tests und Migrationen sind die Ground Truth.

## Bewertungsregel

- `>= 90`: freigegeben Quelle: `reports/current/masterplan_status.json`.
- `70-89`: bedingt freigegeben, Risiken dokumentieren Quelle: `reports/current/masterplan_status.json`.
- `< 70`: nicht freigegeben

Der Gesamt-Score ist der arithmetische Mittelwert der Kategorien API, Datenbank, Tests, Dokumentation und Performance.

## Ergebnis

| Kategorie | Score | Bewertung |
|---|---:|---|
| API | 92 | stabil, mit dokumentiertem Pfad-Risiko |
| Datenbank | 95 | Constraints, Migrationen und PostgreSQL-Head praktisch verifiziert |
| Tests | 96 | Standardlauf und PostgreSQL-Integrationslauf gruen |
| Dokumentation | 95 | synchronisiert mit Paket 5 |
| Performance | 100 | Zielwerte auf PostgreSQL-Referenzdaten klar eingehalten |
| Gesamt | 96 | freigegeben | Quelle: `reports/current/masterplan_status.json`.

## Freigabeentscheidung

**Freigegeben.** Quelle: `reports/current/masterplan_status.json`.

Paket 5 ist fuer den aktuellen Entwicklungsstand als belastbare M3-Basis freigegeben. Der Abschluss ist nicht nur fachlich, sondern durch PostgreSQL-Integration und gemessene Read-Performance praktisch verifiziert. Quelle: `reports/current/masterplan_status.json`.

## Folge-Gate fuer GUI-Start

Die GUI startet nicht vor Paket 5.

Harte Regel:

- Start von `M3a - GUI Foundation` nur nach erfolgreichem Paket-5-Gate.
- Mindestschwelle fuer den GUI-Start ist ein Paket-5-Gesamtscore von `>= 90`.
- GUI darf nur gegen den dokumentierten API-Vertrag entwickeln, nicht gegen implizite Backend- oder Datenbankannahmen.

Begruendung:

- Paket 5 ist die Integrationsgrenze, die Read-API, Fehlerstandard und Datenkonsistenz stabilisiert.
- Ein frueherer GUI-Start wuerde die UI an potenziell instabile Vertrags- und Zustandslogik koppeln.

## API

Score: `92`

Geprueft:

- `GET /documents` ist implementiert mit required `workspace_id`, `limit`, `offset` und `created_at DESC`.
- `GET /documents/{document_id}` ist implementiert mit Detaildaten, `latest_version`, Parser-Metadaten, `import_status` und `chunk_summary`.
- `GET /documents/{document_id}/versions` ist implementiert.
- `GET /documents/{document_id}/chunks` ist implementiert mit `position ASC`, optionalem `limit`, `text_preview` und normalisiertem `source_anchor`.
- Paket-5-Fehler werden im Error-Envelope `{"error": {"code": "...", "message": "...", "details": {...}}}` ausgegeben.
- Response-Schemas sind als Pydantic-Modelle definiert.

Risiken:

- Implementierter Base Path ist `/documents`; `/api/v1/documents` ist dokumentiertes Ziel, aber noch kein implementierter Alias.
- Nicht alle moeglichen internen Fehlerklassen sind fachlich spezialisiert; unbekannte Fehler koennen weiterhin als generische Serverfehler auftreten.

## Datenbank

Score: `95`

Geprueft:

- Alembic Head ist `20260504_0010`.
- Migrationskette ist linear:
  - `20260430_0001`
  - `20260430_0002`
  - `20260430_0003`
  - `20260430_0004`
  - `20260504_0005`
  - `20260504_0006`
  - `20260504_0007`
  - `20260504_0008`
  - `20260504_0009`
  - `20260504_0010`
- Unique Constraint `uq_documents_workspace_content_hash` ist im Model und in der Migration vorhanden.
- `documents.import_status` ist im Model und in der Migration vorhanden.
- Check Constraint `ck_documents_import_status_allowed` ist im Model und in der Migration vorhanden.
- Source-Anchor-Normalisierung ist als Migration vorhanden.
- Read-Indizes und Legacy-Reparaturmigration sind auf PostgreSQL erfolgreich gelaufen.
- Der PostgreSQL-Migrationslauf ist verifiziert gruen.

Risiken:

- Bestehende Produktivdaten koennten vor Anwendung der Unique-Migration bereits Duplikate enthalten; dafuer braucht es vor Migration einen Datencheck.

## Tests

Score: `96`

Geprueft:

```text
42 passed, 1 skipped
6 passed
19 passed
```

Skips:

- Im Standardlauf bleibt der PostgreSQL-Pfad ohne gesetzte `TEST_DATABASE_URL` optional.
- Fuer das Abschluss-Gate wurde der PostgreSQL-Pfad aber explizit mit Test-DB ausgefuehrt.

Abdeckung:

- API-Tests fuer Dokumentliste, Dokumentdetail, Chunks und Fehlerfaelle.
- Service-Tests ohne FastAPI.
- Parser-Tests.
- Chunking-Tests.
- Import-API-Fehlerpfade.
- Strukturtests fuer Alembic.
- PostgreSQL-Migrations-Integrationstest.
- PostgreSQL-Import-Integrationstest inklusive Duplicate-Verhalten.

Risiken:

- Der Standardlauf allein deckt PostgreSQL nicht ab; das Abschluss-Gate sollte deshalb weiter einen expliziten PostgreSQL-Lauf enthalten.

## Dokumentation

Score: `95`

Geprueft:

- `docs/status.md` ist auf Paket 5 aktualisiert.
- `docs/api/v1-document-api-contract.md` beschreibt aktuelle Endpoints, Schemas und Fehlercodes.
- `docs/data-model.md` beschreibt neue Felder, Constraints und Migrationen.
- `docs/adr/0003-document-read-api-before-retrieval.md` dokumentiert die Architekturentscheidung.
- `docs/paket-5-definition-of-done.md` enthaelt messbare Muss-Kriterien.
- Stichproben auf veraltete Aussagen zu altem Fehlerformat, alten Source-Anchor-Feldern und lokal laufendem OCR ergaben keine Treffer.

Risiken:

- ADR-Nummerierung ist historisch doppelt belegt.
- Dokumentation beschreibt `/api/v1/documents` als Zielpfad, aber korrekt als noch nicht implementierten Alias.

## Performance

Score: `100`

Geprueft:

- `GET /documents` nutzt aggregierte Projektionen fuer Version- und Chunk-Zaehler.
- `GET /documents/{document_id}` berechnet `chunk_summary` per Aggregat/Subquery und laedt keine vollstaendigen Chunks.
- `GET /documents/{document_id}/chunks` nutzt Projektion und `substr(content, 1, 200)` fuer serverseitiges `text_preview`.
- Chunk-Abfrage filtert auf `document_id` und `latest_version`.
- Chunk-Abfrage sortiert nach `chunk_index ASC`.
- PostgreSQL-Benchmark auf Referenzdaten ist gemessen.
- EXPLAIN ANALYZE zeigt Nutzung von `ix_documents_workspace_created`, `ix_document_versions_document_created` und `ix_document_chunks_doc_ver_idx`.

Gemessene Mittelwerte:

- `GET /documents`: `3.1ms`
- `GET /documents/{document_id}`: `3.4ms`
- `GET /documents/{document_id}/chunks`: `2.1ms`

Restliches Risiko:

- Die Messung basiert auf dem verifizierten Referenzdatensatz `100` Dokumente, `300` Versionen und `6.000` Chunks, nicht auf spaeteren Produktionslasten.

## Verbleibende Nicht-Blocker

1. Vor Produktiveinsatz Bestandsdaten auf doppelte `(workspace_id, content_hash)` pruefen.
2. Optional vor M3 einen kompatiblen `/api/v1/documents`-Alias implementieren.
3. OCR und feinere Quellenpositionsdaten spaeter separat behandeln.

## Harte Gate-Regel fuer kuenftige Pakete

Ein Paket darf nur als `freigegeben` markiert werden, wenn alle folgenden Bedingungen erfuellt sind:

- API-Score `>= 90`.
- Datenbank-Score `>= 90`.
- Test-Score `>= 90`.
- Dokumentations-Score `>= 90`.
- Performance-Score `>= 90`, sofern Performance Teil des Pakets ist.
- Keine offenen Blocker.
- Alle skipped Tests haben eine dokumentierte, akzeptierte Begruendung.
- Dokumentation enthaelt keine Features, die nicht im Code existieren.

