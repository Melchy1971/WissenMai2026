from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class CrashConsistencyMatrix:
    background_jobs_pending: int
    background_jobs_running: int
    background_jobs_retryable: int
    background_jobs_dead_letter: int
    orphan_documents_without_version: int
    orphan_versions_without_document: int
    orphan_chunks_without_document: int
    orphan_chunks_without_version: int
    duplicate_versions_per_number: int
    duplicate_chunks_per_index: int
    stale_archived_searchable_chunks: int
    stale_deleted_searchable_chunks: int


def load_crash_consistency_matrix(database_url: str, *, workspace_id: str) -> CrashConsistencyMatrix:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                    coalesce(sum(case when status = 'pending' then 1 else 0 end), 0),
                    coalesce(sum(case when status = 'running' then 1 else 0 end), 0),
                    coalesce(sum(case when status = 'retryable' then 1 else 0 end), 0),
                    coalesce(sum(case when status = 'dead_letter' then 1 else 0 end), 0)
                from background_jobs
                where workspace_id = %s
                """,
                (workspace_id,),
            )
            background_jobs = cursor.fetchone()

            cursor.execute(
                """
                select count(*)
                from documents d
                left join document_versions v on v.id = d.current_version_id
                where d.workspace_id = %s
                  and d.current_version_id is not null
                  and v.id is null
                """,
                (workspace_id,),
            )
            orphan_documents_without_version = int(cursor.fetchone()[0])

            cursor.execute(
                """
                select count(*)
                from document_versions v
                left join documents d on d.id = v.document_id
                where d.id is null
                """
            )
            orphan_versions_without_document = int(cursor.fetchone()[0])

            cursor.execute(
                """
                select count(*)
                from document_chunks c
                left join documents d on d.id = c.document_id
                where d.id is null
                """
            )
            orphan_chunks_without_document = int(cursor.fetchone()[0])

            cursor.execute(
                """
                select count(*)
                from document_chunks c
                left join document_versions v on v.id = c.document_version_id
                where v.id is null
                """
            )
            orphan_chunks_without_version = int(cursor.fetchone()[0])

            cursor.execute(
                """
                select count(*)
                from (
                    select document_id, version_number
                    from document_versions
                    group by document_id, version_number
                    having count(*) > 1
                ) duplicates
                """
            )
            duplicate_versions_per_number = int(cursor.fetchone()[0])

            cursor.execute(
                """
                select count(*)
                from (
                    select document_version_id, chunk_index
                    from document_chunks
                    group by document_version_id, chunk_index
                    having count(*) > 1
                ) duplicates
                """
            )
            duplicate_chunks_per_index = int(cursor.fetchone()[0])

            cursor.execute(
                """
                select count(*)
                from document_chunks c
                join documents d on d.id = c.document_id
                where d.workspace_id = %s
                  and d.lifecycle_status = 'archived'
                  and c.is_searchable = true
                """,
                (workspace_id,),
            )
            stale_archived_searchable_chunks = int(cursor.fetchone()[0])

            cursor.execute(
                """
                select count(*)
                from document_chunks c
                join documents d on d.id = c.document_id
                where d.workspace_id = %s
                  and d.lifecycle_status = 'deleted'
                  and c.is_searchable = true
                """,
                (workspace_id,),
            )
            stale_deleted_searchable_chunks = int(cursor.fetchone()[0])

    return CrashConsistencyMatrix(
        background_jobs_pending=int(background_jobs[0]),
        background_jobs_running=int(background_jobs[1]),
        background_jobs_retryable=int(background_jobs[2]),
        background_jobs_dead_letter=int(background_jobs[3]),
        orphan_documents_without_version=orphan_documents_without_version,
        orphan_versions_without_document=orphan_versions_without_document,
        orphan_chunks_without_document=orphan_chunks_without_document,
        orphan_chunks_without_version=orphan_chunks_without_version,
        duplicate_versions_per_number=duplicate_versions_per_number,
        duplicate_chunks_per_index=duplicate_chunks_per_index,
        stale_archived_searchable_chunks=stale_archived_searchable_chunks,
        stale_deleted_searchable_chunks=stale_deleted_searchable_chunks,
    )
