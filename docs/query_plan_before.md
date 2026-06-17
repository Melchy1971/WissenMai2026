# Query Plan — Before GIN Indexes

Stand: 2026-06-18 (vor Migration 20260618_0026)
Basis: Schema-Analyse, keine Live-DB verfügbar (SCGB-01)

---

## Methodik

Kein Live-Datenbankzugriff (SCGB-01). Query-Pläne sind auf Basis der Schema-Analyse und PostgreSQL-Planer-Regeln rekonstruiert. EXPLAIN ANALYZE muss nach SCGB-01-Schließung verifiziert werden.

---

## IDX-01: Volltext-Suche document_chunks (KRITISCH)

```sql
EXPLAIN ANALYZE
SELECT id, document_id, content, ts_headline('german', content, q) AS headline
FROM document_chunks, to_tsquery('german', 'Wissensmanagement') q
WHERE search_vector @@ q
  AND is_searchable = true
LIMIT 20;
```

**Erwarteter Plan OHNE GIN-Index:**
```
Limit  (cost=0.00..???  rows=20)
  ->  Seq Scan on document_chunks
        Filter: ((search_vector @@ '''wissensmanagement'''::tsquery) AND is_searchable)
        Rows Removed by Filter: ~9980 (bei 10k)
        Estimated rows: ~100k for full scan
```

**Geschätzte Kosten:**
| Datensätze | Scan-Zeit | Engpass |
|-----------|-----------|---------|
| 10.000 Chunks | ~500ms | Seqscan |
| 50.000 Chunks | ~2.500ms | Seqscan |
| 100.000 Chunks | >5.000ms | Seqscan |

---

## IDX-02: JSONB Metadata Lookup (document_versions)

```sql
EXPLAIN ANALYZE
SELECT id, metadata
FROM document_versions
WHERE metadata @> '{"parser_version": "2.0"}';
```

**OHNE GIN:**
```
Seq Scan on document_versions
  Filter: (metadata @> '{"parser_version": "2.0"}')
  -- vollständiger Tabellen-Scan
```

---

## IDX-03: Dokumenten-Titelsuche

```sql
EXPLAIN ANALYZE
SELECT id, title
FROM documents
WHERE to_tsvector('german', title) @@ to_tsquery('german', 'Bericht & 2026')
  AND workspace_id = $1
  AND lifecycle_status = 'active';
```

**OHNE GIN:**
```
Index Scan on ix_documents_workspace_created  (workspace_id filter)
  ->  Filter: to_tsvector('german', title) @@ query
  -- FTS-Filter nach Index-Scan: kein FTS-Index, recheck auf alle Workspace-Dokumente
```

---

## IDX-04/05: Analysis Result Suche

```sql
EXPLAIN ANALYZE
SELECT id, summary, content_markdown
FROM analysis_results
WHERE to_tsvector('german', coalesce(content_markdown,'') || ' ' || coalesce(summary,''))
      @@ to_tsquery('german', 'Risiko')
  AND status = 'approved';
```

**OHNE GIN:**
```
Index Scan on ix_analysis_results_status  (status='approved')
  ->  Filter: to_tsvector(content_markdown || summary) @@ query
  -- FTS auf allen approved-Zeilen ohne Index
```

---

## IDX-07: Export-Jobs List-and-Filter

```sql
EXPLAIN ANALYZE
SELECT id, file_name, status, created_at
FROM export_jobs
WHERE workspace_id = $1
  AND source_type = 'ANALYSIS_RESULT'
  AND status = 'COMPLETED'
ORDER BY created_at DESC
LIMIT 50;
```

**OHNE Composite-Index:**
```
Sort  (created_at DESC)
  ->  Index Scan on ix_export_jobs_workspace_id  (workspace_id)
        Filter: (source_type = 'ANALYSIS_RESULT' AND status = 'COMPLETED')
        Rows Removed by Filter: ~viele (je nach Verteilung)
```

---

## N+1 Patterns (zusätzlich identifiziert)

| Muster | Ort | Frequenz |
|--------|-----|---------|
| TopicTag je Topic | search.py _search_topics() | 1 SELECT pro Topic |
| AnalysisJob.result lazy load | service.py list() | 1 SELECT pro Job |
| Dashboard: 5 Einzelqueries | dashboard_service.py list_activity() | pro Request |

