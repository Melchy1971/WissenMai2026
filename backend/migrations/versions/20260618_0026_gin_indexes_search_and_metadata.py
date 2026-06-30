"""GIN indexes for full-text search (tsvector), JSONB metadata, and array columns.

Adds missing performance-critical indexes identified in PRI-7 architecture review
(TD-004, QO-01 through QO-08). All indexes created CONCURRENTLY where possible
to avoid table locks on existing data.

Targets:
- document_chunks.search_vector         → GIN (tsvector) — critical, O(n) → O(log n)
- document_versions.metadata            → GIN (jsonb)    — metadata key lookups
- documents (title fts)                 → GIN tsvector   — document title search
- analysis_results.sources              → GIN (jsonb)    — source filtering
- analysis_results.content_markdown fts → GIN tsvector   — fulltext on result content
- export_jobs (file_name fts)           → GIN tsvector   — filename search
- export_jobs.source_type + workspace   → composite B-tree (already partial, completing)
- topics.title fts                      → GIN tsvector   — topic title search
- topics.summary fts                    → GIN tsvector   — topic summary search

Index naming convention:
  ix_{table}_{column}_{type}
  - _gin  = GIN index
  - _fts  = generated tsvector GIN
  - _btree omitted (default, no suffix)

Revision ID: 20260618_0026
Revises: 20260617_0025
Create Date: 2026-06-18
"""
from __future__ import annotations

from alembic import op

revision: str = "20260618_0026"
down_revision: str | None = "20260617_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        _create_indexes()


def _create_indexes() -> None:
    # ------------------------------------------------------------------ #
    # 1. document_chunks.search_vector — GIN on existing TSVECTOR column  #
    #    CRITICAL: Without this, ts_headline() and @@ operator do O(n)    #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_document_chunks_search_vector_gin
        ON document_chunks
        USING GIN (search_vector)
        WHERE search_vector IS NOT NULL
        """
    )

    # ------------------------------------------------------------------ #
    # 2. document_versions.metadata — GIN on JSONB for key/value lookups  #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_document_versions_metadata_gin
        ON document_versions
        USING GIN (metadata jsonb_path_ops)
        """
    )

    # ------------------------------------------------------------------ #
    # 3. documents.title — GIN tsvector for full-text title search        #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_documents_title_fts_gin
        ON documents
        USING GIN (to_tsvector('german', coalesce(title, '')))
        """
    )

    # ------------------------------------------------------------------ #
    # 4. analysis_results.sources — GIN on JSONB source list              #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_analysis_results_sources_gin
        ON analysis_results
        USING GIN (sources jsonb_path_ops)
        WHERE sources IS NOT NULL
        """
    )

    # ------------------------------------------------------------------ #
    # 5. analysis_results.content_markdown — FTS GIN for result search    #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_analysis_results_content_fts_gin
        ON analysis_results
        USING GIN (to_tsvector('german', coalesce(content_markdown, '') || ' ' || coalesce(summary, '')))
        """
    )

    # ------------------------------------------------------------------ #
    # 6. export_jobs.file_name — FTS GIN for filename search              #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_export_jobs_file_name_fts_gin
        ON export_jobs
        USING GIN (to_tsvector('simple', coalesce(file_name, '')))
        """
    )

    # ------------------------------------------------------------------ #
    # 7. export_jobs composite: workspace_id + source_type + status       #
    #    Covers the most common list-and-filter query pattern             #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_export_jobs_workspace_source_status
        ON export_jobs (workspace_id, source_type, status)
        WHERE workspace_id IS NOT NULL
        """
    )

    # ------------------------------------------------------------------ #
    # 8. document_chunks.metadata — GIN on JSONB chunk metadata           #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_document_chunks_metadata_gin
        ON document_chunks
        USING GIN (metadata jsonb_path_ops)
        """
    )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        _drop_indexes()


def _drop_indexes() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_document_chunks_search_vector_gin")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_document_versions_metadata_gin")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_documents_title_fts_gin")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_analysis_results_sources_gin")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_analysis_results_content_fts_gin")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_export_jobs_file_name_fts_gin")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_export_jobs_workspace_source_status")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_document_chunks_metadata_gin")
