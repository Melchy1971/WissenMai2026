# Technical Debt Register

Stand: 2026-06-17
Quelle: `reports/current/technical_debt_register.json`

---

## Priorität 1 — Kritisch (sofort)

### TD-004 — Fehlender GIN-Index auf search_vector

**Kategorie:** Performance / Index | **Aufwand:** XS | **Risiko:** HIGH

Migration 0011 erstellt die TSVECTOR-Spalte, aber keinen GIN-Index. FTS-Queries auf Chunks laufen als Sequential Scan. Bei >5k Chunks: Antwortzeit >1s.

**Lösung:** `CREATE INDEX CONCURRENTLY ix_chunks_search_vector ON document_chunks USING GIN (search_vector);`

---

### TD-013 — Fehlende CSP-Header (GA-Blocker)

**Kategorie:** Security | **Aufwand:** S | **Risiko:** HIGH

Kein `Content-Security-Policy`-Header im Middleware-Stack. Blockiert GA-SEC-01.

**Lösung:** FastAPI-Middleware mit `default-src 'self'; script-src 'self'; object-src 'none'`.

---

## Priorität 2 — Hoch

### TD-001 — Python-seitige Pagination in Unified Search

**Kategorie:** Performance | **Aufwand:** M | **Risiko:** HIGH

`search_unified()` lädt alle passenden Datensätze aus allen drei Sub-Queries (Topics, Documents, Chunks) in RAM, sortiert und schneidet dann. Bei 10k Chunks mit typischem Query: >2s, >500MB RAM-Spitze.

**Lösung:** Sub-Queries mit DB-LIMIT, COUNT-Subquery statt `len(records)`, Cursor-basierte Pagination.

---

### TD-011 — Kein Cursor-basiertes Pagination-Interface

**Kategorie:** Skalierungsrisiko | **Aufwand:** L | **Risiko:** HIGH

Alle List-Endpoints nutzen `limit`/`offset`. Ab 50k Einträgen müssen frühe Seiten full-table-gescannt werden.

**Lösung:** Keyset-Pagination: `?cursor=<base64(created_at + id)>` als Alternative zu offset.

---

## Priorität 3 — Mittel

### TD-002 — Dashboard Activity: 5 separate Queries

**Kategorie:** N+1 | **Aufwand:** S | **Risiko:** MEDIUM

5 SELECT-Statements, Python-seitiges Merge und Sort. Keine parallele Ausführung.

**Lösung:** UNION ALL auf DB-Ebene oder dedizierte `activity_events`-Tabelle.

---

### TD-003 — AnalysisJob: Lazy-Load N+1

**Kategorie:** N+1 | **Aufwand:** S | **Risiko:** MEDIUM

AnalysisJob.result, .suggestions, .source_document_links sind lazy-loaded. Job-Listing mit 50 Jobs → 150+ Queries.

**Lösung:** `selectinload(AnalysisJob.result)` im List-Endpoint.

---

### TD-005 — Zwei Import-Pfade

**Kategorie:** Duplicate Code | **Aufwand:** M | **Risiko:** MEDIUM

`import_service.py` (Top-Level) + `services/importing/pipeline.py` + `services/documents/import_executor.py`. Keine klare Canonical-Route dokumentiert.

---

### TD-009 — Zwei parallele Drift-Dashboard-Implementierungen

**Kategorie:** Duplicate Code | **Aufwand:** M | **Risiko:** MEDIUM

`features/dashboard/DriftWidgetPanel.jsx` und `features/drift_v2/DriftDashboard.jsx` implementieren ähnliche Widgets mit unterschiedlichem State-Management.

---

### TD-010 — Kein Response-Caching

**Kategorie:** Performance | **Aufwand:** L | **Risiko:** MEDIUM

Dashboard-Summary: 8+ Queries pro Request. Keine ETag/Cache-Control-Header, kein Server-Side-Cache.

---

### TD-012 — TopicTag N+1 in Suche

**Kategorie:** N+1 | **Aufwand:** S | **Risiko:** MEDIUM

`_search_topics()` führt pro Topic ein separates `SELECT tag_id FROM topic_tags WHERE topic_id = ?` aus.

---

### TD-015 — Kein einheitliches Job-Interface

**Kategorie:** Architektur | **Aufwand:** XL | **Risiko:** MEDIUM

Drei separate Job-Systeme (Import, Analyse, Export) mit eigenen Retry-, Timeout-, Cancel-Implementierungen. Kein gemeinsames Interface.

---

## Priorität 4–5 — Niedrig

### TD-006 — backup_restore.py God Service (693 Zeilen)

**Kategorie:** God Service | **Aufwand:** M | **Risiko:** LOW

### TD-007 — diagnostics.py God Service (528 Zeilen)

**Kategorie:** God Service | **Aufwand:** M | **Risiko:** LOW

### TD-008 — DriftWidgetPanel.jsx (465 Zeilen)

**Kategorie:** Große Komponente | **Aufwand:** M | **Risiko:** LOW

### TD-014 — Kein KWIC-Highlighting (GA-FUNC-01)

**Kategorie:** Fehlende Funktion | **Aufwand:** L | **Risiko:** MEDIUM

ts_headline() bereits in `_search_chunks_pg` vorbereitet. Frontend-Side: `<mark>`-Tag-Rendering.

---

## Gesamtübersicht

| Risiko | Anzahl |
|--------|--------|
| HIGH | 4 |
| MEDIUM | 8 |
| LOW | 3 |

**Kritischer Pfad für GA:** TD-004 → TD-013 → TD-001 → TD-011 → TD-014
