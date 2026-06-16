# Entwicklungsprotokoll — Topics, Unified Search, Dashboard Widgets

**Datum:** 2026-06-16
**Tasks:** 64–72
**Statusquelle:** `reports/current/topics_release_report.json`, `reports/current/topics_gold_path.json`, `reports/current/masterplan_status.json`

---

## Übersicht

Drei Feature-Cluster wurden abgeschlossen:

1. **Topics-Backend** (Tasks 64–70): Vollständiges CRUD-System für Themen
2. **Unified Search** (Task 71): Erweiterte globale Suche über alle Entitätstypen
3. **Dashboard Widgets** (Task 72): Topics-Kennzahlen-Panel mit Charts

---

## Task 64 — SQLAlchemy Model topics.py

**Datei:** `backend/app/models/topics.py`

Vier ORM-Entitäten:
- `Topic`: Kern-Entity. Felder: id, workspace_id, title, slug, summary, status, created_by, approved_at, approved_by, deleted_at, created_at, updated_at.
- `TopicDocument`: N:M-Relation Topic ↔ Document mit relation_type (primary|related|reference).
- `TopicTag`: N:M-Relation Topic ↔ Tag.
- `TopicRelation`: Topic ↔ Topic mit relation_type.

Status-Constraint: `draft|review|approved|archived`. Soft-Delete via `deleted_at`. Composite-Index auf `(workspace_id, status)` für List-Queries.

---

## Task 65 — Alembic Migration 0022_topics

Migration erzeugt: `topics`, `topic_documents`, `topic_tags`, `topic_relations`. Foreign Keys mit CASCADE und SET NULL korrekt gesetzt. Rückwärts-kompatibel.

---

## Task 66 — Pydantic Schemas

**Datei:** `backend/app/schemas/topics.py`

Typen: `TopicCreate`, `TopicUpdate`, `TopicDetail`, `TopicListResponse`, `AddTagRequest`, `AttachDocumentRequest`, `TopicMergeRequest`, `TopicMergeResponse`.

Fehlerklassen: `TopicNotFoundError`, `TopicSlugConflictError`, `TopicValidationError`.

---

## Task 67 — Repository Layer

**Datei:** `backend/app/repositories/topics.py` (406 Zeilen)

11 Operationen: list_topics (mit Pagination, Status-Filter, Tag-Filter, Order-By), get_topic_by_id, get_topic_by_slug, create_topic, update_topic, soft_delete_topic, attach_document, detach_document, add_tag, remove_tag, list_tags_for_topic.

Workspace-Isolation in jeder Query. Soft-Delete-Filter überall.

---

## Task 68 — TopicService + TopicMergeService

**Dateien:** `backend/app/services/topics/service.py` (353 Zeilen), `backend/app/services/topics/merge_service.py` (368 Zeilen)

`TopicService`: orchestriert alle CRUD-Operationen. Slug-Uniqueness-Validierung vor Persist.

`TopicMergeService`: Führt zwei Topics zusammen. Optional: Dokumente + Tags vom Source-Topic übernehmen. Source-Topic wird soft-deleted nach Merge.

---

## Task 69 — FastAPI Router api/v1/topics.py

**Datei:** `backend/app/api/v1/topics.py`

10 Endpoints unter `/api/v1/topics`:
- `GET /` — Liste mit Pagination, Filter, Sortierung
- `POST /` — Erstellen (Member)
- `GET /{id}` — Detail (Member)
- `PATCH /{id}` — Update (Member)
- `DELETE /{id}` — Soft-Delete (Admin)
- `POST /{id}/documents` — Dokument anhängen (Member)
- `DELETE /{id}/documents/{doc_id}` — Dokument lösen (Member)
- `POST /{id}/tags` — Tag hinzufügen (Member)
- `DELETE /{id}/tags/{tag_id}` — Tag entfernen (Member)
- `POST /merge` — Topics zusammenführen (Admin)

Router in `backend/app/api/v1/router.py` registriert.

---

## Task 70 — Tests

**Service-Tests:** `backend/tests/test_topic_service.py` (377 Zeilen, `pytest.mark.unit_fast`)
**Repository-Tests:** `backend/tests/test_topic_repository.py` (304 Zeilen)

Beide nutzen FakeRepository-Muster. Abgedeckt: CRUD, Slug-Validierung, Soft-Delete, Status-Transitions, Merge-Logik.

---

## Task 71 — Unified Search

### Backend

**Schemas:** `backend/app/schemas/search.py` (87 Zeilen)
- `UnifiedSearchFilters`, `UnifiedSearchHit`, `UnifiedSearchResponse`
- Cursor-Helpers: `encode_cursor(offset)` → base64(json), `decode_cursor(token)` → int

**Repository:** `backend/app/repositories/search.py` (513 Zeilen)

Drei Sub-Searches, Python-seitig gemergt:
- `_search_topics`: ILIKE auf `title` + `summary`. Score: title-base 0.90, summary-base 0.65.
- `_search_documents`: ILIKE auf `title`. Score-base 0.85. Nur `lifecycle_status=active`.
- `_search_chunks_unified`: PG → `ts_rank` + `ts_headline` (Limit 200). SQLite → ILIKE auf content (Limit 100).

Highlighting: `_highlight_ilike()` erzeugt Excerpt mit `<mark>word</mark>`. PG-Chunks: `ts_headline()` mit `StartSel=<mark>,StopSel=</mark>`.

Sortierung (`_sort_records`): `score_desc`, `created_at_desc`, `created_at_asc`, `title_asc`.

**Service:** `backend/app/services/search_service.py` (211 Zeilen)

`search_unified()`: Validierung (workspace, query, limit 1–100, sort in `_VALID_SORTS`), Cursor-Decode → Offset, Repo-Call, Cursor-Encode → Response.

**API:** `backend/app/api/v1/search.py` (131 Zeilen)

`GET /api/v1/search/unified`: Parameter `q`, `limit`, `cursor`, `sort`, `kind[]`, `status[]`. Logging mit duration_ms, total, hit_count.

**Tests:** `backend/tests/test_unified_search_service.py` (239 Zeilen, `pytest.mark.unit_fast`)

18 Tests: Cursor-Roundtrip, Validierung (4 parametrisierte Fälle), Result-Mapping, Pagination (4 Fälle), Filter-Weiterleitung (3 Tests), Sort (parametrisiert + Forward), Empty-Results.

### Frontend

**API:** `frontend/src/api/search.js` — `searchUnified()` mit URLSearchParams, multi-value `kind[]` + `status[]`.

**Hook:** `frontend/src/features/search/useUnifiedSearch.js` (146 Zeilen) — useReducer mit States `idle|loading|loading-more|success|error`. Methoden: `search()`, `loadMore()`, `setSort()`, `setKindFilter()`, `reset()`.

**Card:** `frontend/src/features/search/UnifiedSearchResultCard.jsx` (123 Zeilen) — KindBadge (farbkodiert nach kind), ScoreBar (CSS width%), Highlight via `dangerouslySetInnerHTML`.

**Page:** `frontend/src/pages/SearchPage.jsx` (313 Zeilen) — KindTabs (Alle|Topic|Dokument|Chunk), SortDropdown, Debounced-Input (300ms), SkeletonCard (pulse), "Weitere laden"-Button.

---

## Task 72 — Dashboard Widgets

### Backend

**Schemas:** `backend/app/schemas/dashboard.py` — `TopicsDayCount`, `TopicTagCount`, `TopicsWidgetData` ergänzt.

**Service:** `backend/app/services/dashboard_service.py` — `get_topics_widgets()`: 3 Queries:
1. GROUP BY status → Totals, by_status Dict, unreviewed (draft + review)
2. created_at >= now-7days → new_last_7_days, new_per_day (7 Einträge, Lücken als 0)
3. Raw SQL JOIN tags + topic_tags + topics → top_tags (Limit 10)

Cross-DB: PG und SQLite identische SQL-Syntax für Tag-Query.

**API:** `backend/app/api/v1/dashboard.py` — `GET /api/v1/dashboard/topics-widgets` ergänzt.

### Frontend

**API:** `frontend/src/api/dashboard.js` — `getDashboardTopicsWidgets()` ergänzt.

**Panel:** `frontend/src/features/dashboard/TopicsWidgetPanel.jsx` (325 Zeilen):
- `DonutChart`: SVG mit `stroke-dasharray`-Segmenten pro Status (Magenta-Farbpalette)
- `BarChart`: CSS Flexbox Bars mit STATUS_COLORS
- `TrendChart`: SVG `<polyline>` + gefüllter Area-Pfad für 7-Tage-Verlauf
- `TagCloud`: Font-Size skaliert 11–19px nach Count
- `SkeletonWidget` / `SkeletonChart`: `@keyframes skel-pulse`
- `TopicsWidgetPanel`: useReducer, Fetch on Mount, alle 6 Widgets

**DashboardPage:** `frontend/src/pages/DashboardPage.jsx` (239 Zeilen) — vollständig neu geschrieben mit `<TopicsWidgetPanel />`.

---

## Offene Punkte

### HIGH — Blocker

**TC-URL-01:** `frontend/src/api/topics.js` ruft `/topics/*` auf statt `/api/v1/topics/*`. Topics-Feature im Frontend 404. Fix: 30 Minuten.

### LOW — Debt

**Tag-Suche:** Tags werden nicht direkt in Unified Search durchsucht. Nur als Metadaten zurückgegeben.

**Unified Search Performance:** Python-seitiger Merge von bis zu 200 PG-Chunks + allen matching Topics/Docs. Bei >1000 Topics Performance-Risiko. Für V1 ausreichend.

**Dark Mode:** Nicht implementiert. Explizit deferred.

**Accessibility Topics-Panels:** aria-labels nicht auditiert.

---

## Technische Entscheidungen

| Entscheidung | Grund |
|---|---|
| Python-seitiger Merge in Unified Search | Vermeidet komplexe DB-übergreifende UNION-Queries; für V1-Datenmengen ausreichend |
| Cursor-Pagination via base64(JSON) | Opaque für Client, einfach zu implementieren, zustandslos |
| Pure SVG Charts ohne externe Bibliothek | Keine npm-Dependencies, kein Bundle-Size-Impact |
| Soft-Delete Topics | Merge-Referenzen bleiben konsistent; Audit-Trail erhalten |
| Raw SQL für Tag-Aggregation | Tags-Tabelle hat kein ORM-Model; raw `text()` sicherer als Pseudo-Models |
