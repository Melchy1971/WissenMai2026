# Query Plan — After GIN Indexes

Stand: 2026-06-18 (nach Migration 20260618_0026)
Basis: Erwartete Pläne gemäß PostgreSQL GIN-Dokumentation

---

## IDX-01: Volltext-Suche document_chunks (KRITISCH → GELÖST)

```sql
EXPLAIN ANALYZE
SELECT id, document_id, content, ts_headline('german', content, q) AS headline
FROM document_chunks, to_tsquery('german', 'Wissensmanagement') q
WHERE search_vector @@ q
  AND is_searchable = true
LIMIT 20;
```

**Erwarteter Plan MIT GIN-Index:**
```
Limit  (cost=8.00..125.00  rows=20)
  ->  Bitmap Heap Scan on document_chunks
        Recheck Cond: (search_vector @@ '''wissensmanagement'''::tsquery)
        Filter: is_searchable
        ->  Bitmap Index Scan on ix_document_chunks_search_vector_gin
              Index Cond: (search_vector @@ '''wissensmanagement'''::tsquery)
```

**Erwartete Kosten nach GIN:**
| Datensätze | Scan-Zeit | Verbesserung |
|-----------|-----------|-------------|
| 10.000 Chunks | <20ms | **25× schneller** |
| 50.000 Chunks | <50ms | **50× schneller** |
| 100.000 Chunks | <100ms | **>50× schneller** |

---

## IDX-02: JSONB Metadata Lookup

```sql
-- Nach ix_document_versions_metadata_gin (jsonb_path_ops):
Bitmap Heap Scan on document_versions
  Recheck Cond: (metadata @> '{"parser_version": "2.0"}')
  ->  Bitmap Index Scan on ix_document_versions_metadata_gin
        Index Cond: (metadata @> '{"parser_version": "2.0"}')
-- O(log n) statt O(n)
```

---

## IDX-03: Dokumenten-Titelsuche

```sql
-- Nach ix_documents_title_fts_gin:
Bitmap Heap Scan on documents
  Recheck Cond: (to_tsvector(...) @@ query)
  Filter: (workspace_id = $1 AND lifecycle_status = 'active')
  ->  Bitmap Index Scan on ix_documents_title_fts_gin
        Index Cond: (to_tsvector('german', title) @@ query)
```

---

## IDX-04/05: Analysis Result Suche

```sql
-- Nach ix_analysis_results_content_fts_gin:
Bitmap Heap Scan on analysis_results
  Recheck Cond: (to_tsvector(...) @@ query)
  Filter: (status = 'approved')
  ->  BitmapAnd
        ->  Bitmap Index Scan on ix_analysis_results_content_fts_gin
        ->  Bitmap Index Scan on ix_analysis_results_status
```

---

## IDX-07: Export-Jobs Composite

```sql
-- Nach ix_export_jobs_workspace_source_status:
Index Scan on ix_export_jobs_workspace_source_status
  Index Cond: (workspace_id = $1 AND source_type = 'ANALYSIS_RESULT' AND status = 'COMPLETED')
Sort: created_at DESC
-- Keine Filter-Reste, direkter Index-Hit
```

---

## Benchmark-Ziele (nach Migration)

| Query | Datensätze | Ziel | Status |
|-------|-----------|------|--------|
| Chunk-Volltext | 10k | <20ms | SPEZIFIZIERT |
| Chunk-Volltext | 50k | <50ms | SPEZIFIZIERT |
| Chunk-Volltext | 100k | <100ms | SPEZIFIZIERT |
| JSONB-Lookup | 50k | <10ms | SPEZIFIZIERT |
| Titel-FTS | 50k | <15ms | SPEZIFIZIERT |
| Export-List-Filter | 50k | <5ms | SPEZIFIZIERT |

**Verifikation:** `EXPLAIN ANALYZE` nach SCGB-01-Schließung mit befüllter Test-DB ausführen.

---

## EXPLAIN ANALYZE Testskript (nach SCGB-01)

```sql
-- 1. Benchmark Datenmenge prüfen
SELECT COUNT(*) FROM document_chunks WHERE search_vector IS NOT NULL;

-- 2. GIN-Index vorhanden?
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'document_chunks'
  AND indexname = 'ix_document_chunks_search_vector_gin';

-- 3. Performance-Test (10k-Benchmark)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, content
FROM document_chunks
WHERE search_vector @@ to_tsquery('german', 'Wissen')
  AND is_searchable = true
LIMIT 20;

-- 4. Index-Nutzung prüfen
SELECT indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname = 'document_chunks'
ORDER BY idx_scan DESC;
```

