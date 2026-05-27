import os
from collections.abc import Iterator
from datetime import UTC, datetime
import logging

import psycopg
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1 import admin as admin_api
from app.api.v1 import chat as chat_api
from app.api.v1 import search as search_api
from app.core.config import settings
from app.main import app
from app.services.auth import hash_password, hash_token
from app.services.chat.citation_mapper import CitationMapper
from app.services.chat.context_builder import ContextBuilder
from app.services.chat.fake_llm_provider import FakeLlmProvider
from app.services.chat.insufficient_context_policy import InsufficientContextPolicy, InsufficientContextThresholds
from app.services.chat.persistence_service import ChatPersistenceService
from app.services.chat.prompt_builder import PromptBuilder
from app.services.chat.rag_chat_service import RagChatService
from app.services.search_index_service import SearchIndexRebuildService
from app.services.search_service import SearchService
from tests.integration.test_migrations import make_alembic_config, psycopg_url

pytestmark = pytest.mark.postgres

# ---------------------------------------------------------------------------
# Test IDs: deterministic UUIDs that never collide with migration seeds
# ---------------------------------------------------------------------------

WORKSPACE_ID    = "e1000000-0000-0000-0000-000000000001"
OTHER_WS_ID     = "e1000000-0000-0000-0000-000000000002"
USER_ID         = "00000000-0000-0000-0000-000000000001"  # seeded by migration

DOC_PYTHON_ID   = "e2000000-0000-0000-0000-000000000001"
DOC_ML_ID       = "e2000000-0000-0000-0000-000000000002"
DOC_DB_ID       = "e2000000-0000-0000-0000-000000000003"
DOC_FAILED_ID   = "e2000000-0000-0000-0000-000000000004"
DOC_PENDING_ID  = "e2000000-0000-0000-0000-000000000005"
DOC_OTHER_WS_ID = "e2000000-0000-0000-0000-000000000006"
DOC_ARCHIVED_ID = "e2000000-0000-0000-0000-000000000007"
DOC_DELETED_ID  = "e2000000-0000-0000-0000-000000000008"
DOC_RANK_STRONG_ID = "e2100000-0000-0000-0000-000000000001"
DOC_RANK_NEW_ID    = "e2100000-0000-0000-0000-000000000002"
DOC_RANK_OLD_ID    = "e2100000-0000-0000-0000-000000000003"
DOC_RANK_INDEX_ID  = "e2100000-0000-0000-0000-000000000004"
DOC_RANK_ID_LOW    = "e2100000-0000-0000-0000-000000000005"
DOC_RANK_ID_HIGH   = "e2100000-0000-0000-0000-000000000006"

VER_PYTHON_OLD_ID = "e3000000-0000-0000-0000-000000000001"
VER_PYTHON_ID     = "e3000000-0000-0000-0000-000000000002"
VER_ML_ID         = "e3000000-0000-0000-0000-000000000003"
VER_DB_ID         = "e3000000-0000-0000-0000-000000000004"
VER_FAILED_ID     = "e3000000-0000-0000-0000-000000000005"
VER_PENDING_ID    = "e3000000-0000-0000-0000-000000000006"
VER_OTHER_WS_ID   = "e3000000-0000-0000-0000-000000000007"
VER_ARCHIVED_ID   = "e3000000-0000-0000-0000-000000000008"
VER_DELETED_ID    = "e3000000-0000-0000-0000-000000000009"
VER_RANK_STRONG_ID = "e3100000-0000-0000-0000-000000000001"
VER_RANK_NEW_ID    = "e3100000-0000-0000-0000-000000000002"
VER_RANK_OLD_ID    = "e3100000-0000-0000-0000-000000000003"
VER_RANK_INDEX_ID  = "e3100000-0000-0000-0000-000000000004"
VER_RANK_ID_LOW    = "e3100000-0000-0000-0000-000000000005"
VER_RANK_ID_HIGH   = "e3100000-0000-0000-0000-000000000006"

CHUNK_PYTHON_OLD_ID = "e4000000-0000-0000-0000-000000000001"
CHUNK_PYTHON_ID     = "e4000000-0000-0000-0000-000000000002"
CHUNK_ML_ID         = "e4000000-0000-0000-0000-000000000003"
CHUNK_DB_ID         = "e4000000-0000-0000-0000-000000000004"
CHUNK_FAILED_ID     = "e4000000-0000-0000-0000-000000000005"
CHUNK_PENDING_ID    = "e4000000-0000-0000-0000-000000000006"
CHUNK_OTHER_WS_ID   = "e4000000-0000-0000-0000-000000000007"
CHUNK_ARCHIVED_ID   = "e4000000-0000-0000-0000-000000000008"
CHUNK_DELETED_ID    = "e4000000-0000-0000-0000-000000000009"
CHUNK_RANK_STRONG_ID = "e4100000-0000-0000-0000-000000000001"
CHUNK_RANK_NEW_ID    = "e4100000-0000-0000-0000-000000000002"
CHUNK_RANK_OLD_ID    = "e4100000-0000-0000-0000-000000000003"
CHUNK_RANK_INDEX_0_ID = "e4100000-0000-0000-0000-000000000004"
CHUNK_RANK_INDEX_1_ID = "e4100000-0000-0000-0000-000000000005"
CHUNK_RANK_ID_LOW     = "e4100000-0000-0000-0000-000000000006"
CHUNK_RANK_ID_HIGH    = "e4100000-0000-0000-0000-000000000007"

DOC_LIFECYCLE_ACTIVE_ID = "e2200000-0000-0000-0000-000000000001"
DOC_LIFECYCLE_ARCHIVED_ID = "e2200000-0000-0000-0000-000000000002"
DOC_LIFECYCLE_DELETED_ID = "e2200000-0000-0000-0000-000000000003"

VER_LIFECYCLE_ACTIVE_ID = "e3200000-0000-0000-0000-000000000001"
VER_LIFECYCLE_ARCHIVED_ID = "e3200000-0000-0000-0000-000000000002"
VER_LIFECYCLE_DELETED_ID = "e3200000-0000-0000-0000-000000000003"

CHUNK_LIFECYCLE_ACTIVE_ID = "e4200000-0000-0000-0000-000000000001"
CHUNK_LIFECYCLE_ARCHIVED_ID = "e4200000-0000-0000-0000-000000000002"
CHUNK_LIFECYCLE_DELETED_ID = "e4200000-0000-0000-0000-000000000003"

LIFECYCLE_SHARED_TERM = "lifecycleretrievalterm"

RANKING_QUERY = "rankingterm orderterm"
RANKING_BASE_CONTENT = "rankingterm orderterm baseline"

SESSION_TOKEN = "m3b-search-session-token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sa_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _index_exists(conn: psycopg.Connection, index_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND indexname = %s)",
            (index_name,),
        )
        row = cur.fetchone()
    return bool(row[0]) if row is not None else False


_NULL_SOURCE_ANCHOR = (
    '{"source_anchor": {"type": "text", "page": null, "paragraph": null,'
    ' "char_start": null, "char_end": null}}'
)


def _insert_test_data(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        # Additional workspaces (migration seeds the default; ours are non-default)
        cur.executemany(
            "INSERT INTO workspaces (id, name, is_default, created_at)"
            " VALUES (%s::uuid, %s, false, now()) ON CONFLICT DO NOTHING",
            [
                (WORKSPACE_ID, "M3b Test Workspace"),
                (OTHER_WS_ID,  "M3b Other Workspace"),
            ],
        )

        # Insert documents with status "pending" initially so current_version_id=NULL
        # is allowed (constraint: readable statuses require current_version_id IS NOT NULL).
        cur.executemany(
            """
            INSERT INTO documents
                (id, workspace_id, owner_user_id, current_version_id,
                 title, source_type, mime_type, content_hash, import_status,
                 created_at, updated_at)
            VALUES
                (%s::uuid, %s::uuid, %s::uuid, NULL,
                 %s, 'upload', 'text/plain', %s, 'pending',
                 now(), now())
            """,
            [
                (DOC_PYTHON_ID,   WORKSPACE_ID, USER_ID, "Python Guide",   "hash-m3b-python"),
                (DOC_ML_ID,       WORKSPACE_ID, USER_ID, "ML Basics",      "hash-m3b-ml"),
                (DOC_DB_ID,       WORKSPACE_ID, USER_ID, "DB Performance", "hash-m3b-db"),
                (DOC_FAILED_ID,   WORKSPACE_ID, USER_ID, "Failed Doc",     "hash-m3b-failed"),
                (DOC_PENDING_ID,  WORKSPACE_ID, USER_ID, "Pending Doc",    "hash-m3b-pending"),
                (DOC_OTHER_WS_ID, OTHER_WS_ID,  USER_ID, "Other WS Doc",   "hash-m3b-other-ws"),
                (DOC_ARCHIVED_ID, WORKSPACE_ID, USER_ID, "Archived Doc",   "hash-m3b-archived"),
                (DOC_DELETED_ID,  WORKSPACE_ID, USER_ID, "Deleted Doc",    "hash-m3b-deleted"),
            ],
        )
        cur.executemany(
            """
            INSERT INTO documents
                (id, workspace_id, owner_user_id, current_version_id,
                 title, source_type, mime_type, content_hash, import_status,
                 created_at, updated_at)
            VALUES
                (%s::uuid, %s::uuid, %s::uuid, NULL,
                 %s, 'upload', 'text/plain', %s, 'pending',
                 %s::timestamptz, %s::timestamptz)
            """,
            [
                (
                    DOC_RANK_STRONG_ID,
                    WORKSPACE_ID,
                    USER_ID,
                    "Ranking Strong",
                    "hash-m3b-rank-strong",
                    "2026-05-02T12:00:00Z",
                    "2026-05-02T12:00:00Z",
                ),
                (
                    DOC_RANK_NEW_ID,
                    WORKSPACE_ID,
                    USER_ID,
                    "Ranking Newer Tie",
                    "hash-m3b-rank-new",
                    "2026-05-06T12:00:00Z",
                    "2026-05-06T12:00:00Z",
                ),
                (
                    DOC_RANK_OLD_ID,
                    WORKSPACE_ID,
                    USER_ID,
                    "Ranking Older Tie",
                    "hash-m3b-rank-old",
                    "2026-05-05T12:00:00Z",
                    "2026-05-05T12:00:00Z",
                ),
                (
                    DOC_RANK_INDEX_ID,
                    WORKSPACE_ID,
                    USER_ID,
                    "Ranking Chunk Index Tie",
                    "hash-m3b-rank-index",
                    "2026-05-04T12:00:00Z",
                    "2026-05-04T12:00:00Z",
                ),
                (
                    DOC_RANK_ID_LOW,
                    WORKSPACE_ID,
                    USER_ID,
                    "Ranking Chunk ID Low",
                    "hash-m3b-rank-id-low",
                    "2026-05-03T12:00:00Z",
                    "2026-05-03T12:00:00Z",
                ),
                (
                    DOC_RANK_ID_HIGH,
                    WORKSPACE_ID,
                    USER_ID,
                    "Ranking Chunk ID High",
                    "hash-m3b-rank-id-high",
                    "2026-05-03T12:00:00Z",
                    "2026-05-03T12:00:00Z",
                ),
            ],
        )

        # Document versions
        cur.executemany(
            """
            INSERT INTO document_versions
                (id, document_id, version_number, normalized_markdown, markdown_hash,
                 parser_version, ocr_used, ki_provider, ki_model, metadata, created_at)
            VALUES
                (%s::uuid, %s::uuid, %s, %s, %s,
                 '1.0', false, NULL, NULL, '{}'::jsonb, now())
            """,
            [
                (VER_PYTHON_OLD_ID, DOC_PYTHON_ID,   1, "# Old Python Guide",  "md-hash-py-old"),
                (VER_PYTHON_ID,     DOC_PYTHON_ID,   2, "# Python Guide v2",   "md-hash-py"),
                (VER_ML_ID,         DOC_ML_ID,       1, "# ML Basics",         "md-hash-ml"),
                (VER_DB_ID,         DOC_DB_ID,       1, "# DB Performance",    "md-hash-db"),
                (VER_FAILED_ID,     DOC_FAILED_ID,   1, "# Failed",            "md-hash-failed"),
                (VER_PENDING_ID,    DOC_PENDING_ID,  1, "# Pending",           "md-hash-pending"),
                (VER_OTHER_WS_ID,   DOC_OTHER_WS_ID, 1, "# Other WS",         "md-hash-other-ws"),
                (VER_ARCHIVED_ID,   DOC_ARCHIVED_ID, 1, "# Archived",         "md-hash-archived"),
                (VER_DELETED_ID,    DOC_DELETED_ID,  1, "# Deleted",          "md-hash-deleted"),
            ],
        )
        cur.executemany(
            """
            INSERT INTO document_versions
                (id, document_id, version_number, normalized_markdown, markdown_hash,
                 parser_version, ocr_used, ki_provider, ki_model, metadata, created_at)
            VALUES
                (%s::uuid, %s::uuid, 1, %s, %s,
                 '1.0', false, NULL, NULL, '{}'::jsonb, %s::timestamptz)
            """,
            [
                (VER_RANK_STRONG_ID, DOC_RANK_STRONG_ID, "# Ranking Strong", "md-hash-rank-strong", "2026-05-02T12:01:00Z"),
                (VER_RANK_NEW_ID, DOC_RANK_NEW_ID, "# Ranking New", "md-hash-rank-new", "2026-05-06T12:01:00Z"),
                (VER_RANK_OLD_ID, DOC_RANK_OLD_ID, "# Ranking Old", "md-hash-rank-old", "2026-05-05T12:01:00Z"),
                (VER_RANK_INDEX_ID, DOC_RANK_INDEX_ID, "# Ranking Index", "md-hash-rank-index", "2026-05-04T12:01:00Z"),
                (VER_RANK_ID_LOW, DOC_RANK_ID_LOW, "# Ranking ID Low", "md-hash-rank-id-low", "2026-05-03T12:01:00Z"),
                (VER_RANK_ID_HIGH, DOC_RANK_ID_HIGH, "# Ranking ID High", "md-hash-rank-id-high", "2026-05-03T12:01:00Z"),
            ],
        )

        # Set current_version_id; VER_PYTHON_OLD_ID is intentionally not current
        cur.executemany(
            "UPDATE documents SET current_version_id = %s::uuid WHERE id = %s",
            [
                (VER_PYTHON_ID,   DOC_PYTHON_ID),
                (VER_ML_ID,       DOC_ML_ID),
                (VER_DB_ID,       DOC_DB_ID),
                (VER_FAILED_ID,   DOC_FAILED_ID),
                (VER_PENDING_ID,  DOC_PENDING_ID),
                (VER_OTHER_WS_ID, DOC_OTHER_WS_ID),
                (VER_ARCHIVED_ID, DOC_ARCHIVED_ID),
                (VER_DELETED_ID,  DOC_DELETED_ID),
                (VER_RANK_STRONG_ID, DOC_RANK_STRONG_ID),
                (VER_RANK_NEW_ID, DOC_RANK_NEW_ID),
                (VER_RANK_OLD_ID, DOC_RANK_OLD_ID),
                (VER_RANK_INDEX_ID, DOC_RANK_INDEX_ID),
                (VER_RANK_ID_LOW, DOC_RANK_ID_LOW),
                (VER_RANK_ID_HIGH, DOC_RANK_ID_HIGH),
            ],
        )

        # Set final import_status now that current_version_id is non-NULL
        cur.executemany(
            "UPDATE documents SET import_status = %s WHERE id = %s",
            [
                ("chunked", DOC_PYTHON_ID),
                ("chunked", DOC_ML_ID),
                ("chunked", DOC_DB_ID),
                ("failed",  DOC_FAILED_ID),
                ("pending", DOC_PENDING_ID),
                ("chunked", DOC_OTHER_WS_ID),
                ("chunked", DOC_ARCHIVED_ID),
                ("chunked", DOC_DELETED_ID),
                ("chunked", DOC_RANK_STRONG_ID),
                ("chunked", DOC_RANK_NEW_ID),
                ("chunked", DOC_RANK_OLD_ID),
                ("chunked", DOC_RANK_INDEX_ID),
                ("chunked", DOC_RANK_ID_LOW),
                ("chunked", DOC_RANK_ID_HIGH),
            ],
        )

        # Chunks: search_vector is GENERATED STORED (auto-populated from content).
        # metadata must contain a normalized source_anchor per migration 0010 constraint.
        # Each chunk has a unique term so tests can target it precisely.
        cur.executemany(
            """
            INSERT INTO document_chunks
                (id, document_id, document_version_id, chunk_index,
                 heading_path, anchor, content, content_hash,
                 token_estimate, metadata, created_at)
            VALUES
                (%s::uuid, %s::uuid, %s::uuid, %s,
                 '[]'::jsonb, %s, %s, md5(%s),
                 NULL, %s::jsonb, now())
            """,
            [
                # Old version of DOC_PYTHON: excluded because not current version
                (CHUNK_PYTHON_OLD_ID, DOC_PYTHON_ID,   VER_PYTHON_OLD_ID, 0,
                 "anchor-py-old", "oldversion programming language history documentation Python",
                 "oldversion programming language history documentation Python", _NULL_SOURCE_ANCHOR),
                # Current version chunks: returned for matching queries
                (CHUNK_PYTHON_ID,     DOC_PYTHON_ID,   VER_PYTHON_ID,     0,
                 "anchor-py",     "Python is a programming language used for software development",
                 "Python is a programming language used for software development", _NULL_SOURCE_ANCHOR),
                (CHUNK_ML_ID,         DOC_ML_ID,       VER_ML_ID,         0,
                 "anchor-ml",     "Machine learning algorithms use statistical methods to recognize patterns",
                 "Machine learning algorithms use statistical methods to recognize patterns", _NULL_SOURCE_ANCHOR),
                (CHUNK_DB_ID,         DOC_DB_ID,       VER_DB_ID,         0,
                 "anchor-db",     "Database query optimization improves system performance dramatically",
                 "Database query optimization improves system performance dramatically", _NULL_SOURCE_ANCHOR),
                # Failed document: excluded by import_status filter
                (CHUNK_FAILED_ID,     DOC_FAILED_ID,   VER_FAILED_ID,     0,
                 "anchor-failed", "failedcontent document processing error occurred",
                 "failedcontent document processing error occurred", _NULL_SOURCE_ANCHOR),
                # Pending document: excluded by import_status filter
                (CHUNK_PENDING_ID,    DOC_PENDING_ID,  VER_PENDING_ID,    0,
                 "anchor-pending","pendingcontent document import is pending processing",
                 "pendingcontent document import is pending processing", _NULL_SOURCE_ANCHOR),
                # Different workspace: excluded when querying WORKSPACE_ID
                (CHUNK_OTHER_WS_ID,   DOC_OTHER_WS_ID, VER_OTHER_WS_ID,   0,
                 "anchor-other",  "exclusiveterm belongs to a completely different workspace context",
                 "exclusiveterm belongs to a completely different workspace context", _NULL_SOURCE_ANCHOR),
                # Archived document: excluded by lifecycle filter
                (CHUNK_ARCHIVED_ID,   DOC_ARCHIVED_ID, VER_ARCHIVED_ID,   0,
                 "anchor-archived",  "archivedcontent archived knowledge should not be retrieved",
                 "archivedcontent archived knowledge should not be retrieved", _NULL_SOURCE_ANCHOR),
                # Deleted document: excluded by lifecycle filter
                (CHUNK_DELETED_ID,    DOC_DELETED_ID,  VER_DELETED_ID,    0,
                 "anchor-deleted",   "deletedcontent deleted knowledge should not be retrieved",
                 "deletedcontent deleted knowledge should not be retrieved", _NULL_SOURCE_ANCHOR),
                # Ranking regression data:
                # - strong chunk wins by rank because both query terms repeat.
                # - all following chunks have identical content and rank.
                # - tie-breakers are document.created_at DESC, chunk_index ASC, chunk_id ASC.
                (CHUNK_RANK_STRONG_ID, DOC_RANK_STRONG_ID, VER_RANK_STRONG_ID, 0,
                 "anchor-rank-strong",
                 f"{RANKING_BASE_CONTENT} {RANKING_BASE_CONTENT} {RANKING_BASE_CONTENT}",
                 f"{RANKING_BASE_CONTENT} {RANKING_BASE_CONTENT} {RANKING_BASE_CONTENT}",
                 _NULL_SOURCE_ANCHOR),
                (CHUNK_RANK_NEW_ID, DOC_RANK_NEW_ID, VER_RANK_NEW_ID, 0,
                 "anchor-rank-new", RANKING_BASE_CONTENT, RANKING_BASE_CONTENT, _NULL_SOURCE_ANCHOR),
                (CHUNK_RANK_OLD_ID, DOC_RANK_OLD_ID, VER_RANK_OLD_ID, 0,
                 "anchor-rank-old", RANKING_BASE_CONTENT, RANKING_BASE_CONTENT, _NULL_SOURCE_ANCHOR),
                (CHUNK_RANK_INDEX_0_ID, DOC_RANK_INDEX_ID, VER_RANK_INDEX_ID, 0,
                 "anchor-rank-index-0", RANKING_BASE_CONTENT, RANKING_BASE_CONTENT, _NULL_SOURCE_ANCHOR),
                (CHUNK_RANK_INDEX_1_ID, DOC_RANK_INDEX_ID, VER_RANK_INDEX_ID, 1,
                 "anchor-rank-index-1", RANKING_BASE_CONTENT, RANKING_BASE_CONTENT, _NULL_SOURCE_ANCHOR),
                (CHUNK_RANK_ID_LOW, DOC_RANK_ID_LOW, VER_RANK_ID_LOW, 0,
                 "anchor-rank-id-low", RANKING_BASE_CONTENT, RANKING_BASE_CONTENT, _NULL_SOURCE_ANCHOR),
                (CHUNK_RANK_ID_HIGH, DOC_RANK_ID_HIGH, VER_RANK_ID_HIGH, 0,
                 "anchor-rank-id-high", RANKING_BASE_CONTENT, RANKING_BASE_CONTENT, _NULL_SOURCE_ANCHOR),
            ],
        )

        cur.execute(
            "UPDATE documents SET lifecycle_status = 'archived', archived_at = now() WHERE id = %s",
            (DOC_ARCHIVED_ID,),
        )
        cur.execute(
            "UPDATE documents SET lifecycle_status = 'deleted', deleted_at = now() WHERE id = %s",
            (DOC_DELETED_ID,),
        )

        created = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
        cur.execute(
            "UPDATE users SET login=%s, password_hash=%s, is_active=true WHERE id=%s",
            ("m3b-user", hash_password("secret", salt="m3bsalt"), USER_ID),
        )
        cur.execute("DELETE FROM auth_sessions WHERE user_id = %s", (USER_ID,))
        cur.execute("DELETE FROM workspace_memberships WHERE user_id = %s", (USER_ID,))
        cur.executemany(
            """
            INSERT INTO workspace_memberships (id, workspace_id, user_id, role, created_at, updated_at)
            VALUES (%s, %s, %s, 'owner', %s, %s)
            """,
            [
                ("m3b-membership-1", WORKSPACE_ID, USER_ID, created, created),
                ("m3b-membership-2", OTHER_WS_ID, USER_ID, created, created),
            ],
        )
        cur.execute(
            """
            INSERT INTO auth_sessions (id, user_id, token_hash, expires_at, created_at, last_seen_at, revoked_at)
            VALUES (%s, %s, %s, %s, %s, %s, NULL)
            """,
            (
                "m3b-session-1",
                USER_ID,
                hash_token(SESSION_TOKEN),
                datetime(2036, 5, 1, 10, 0, tzinfo=UTC),
                created,
                created,
            ),
        )

    conn.commit()


def _insert_lifecycle_retrieval_data(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO documents
                (id, workspace_id, owner_user_id, current_version_id,
                 title, source_type, mime_type, content_hash, import_status,
                 lifecycle_status, archived_at, deleted_at, created_at, updated_at)
            VALUES
                (%s::uuid, %s::uuid, %s::uuid, NULL,
                 %s, 'upload', 'text/plain', %s, 'pending',
                 'active', NULL, NULL, now(), now())
            """,
            [
                (DOC_LIFECYCLE_ACTIVE_ID, WORKSPACE_ID, USER_ID, "Lifecycle Active", "hash-lifecycle-active"),
                (DOC_LIFECYCLE_ARCHIVED_ID, WORKSPACE_ID, USER_ID, "Lifecycle Archived", "hash-lifecycle-archived"),
                (DOC_LIFECYCLE_DELETED_ID, WORKSPACE_ID, USER_ID, "Lifecycle Deleted", "hash-lifecycle-deleted"),
            ],
        )

        cur.executemany(
            """
            INSERT INTO document_versions
                (id, document_id, version_number, normalized_markdown, markdown_hash,
                 parser_version, ocr_used, ki_provider, ki_model, metadata, created_at)
            VALUES
                (%s::uuid, %s::uuid, 1, %s, %s,
                 '1.0', false, NULL, NULL, '{}'::jsonb, now())
            """,
            [
                (
                    VER_LIFECYCLE_ACTIVE_ID,
                    DOC_LIFECYCLE_ACTIVE_ID,
                    f"# Active\n\n{LIFECYCLE_SHARED_TERM} active retrieval source",
                    "md-hash-lifecycle-active",
                ),
                (
                    VER_LIFECYCLE_ARCHIVED_ID,
                    DOC_LIFECYCLE_ARCHIVED_ID,
                    f"# Archived\n\n{LIFECYCLE_SHARED_TERM} archived retrieval source",
                    "md-hash-lifecycle-archived",
                ),
                (
                    VER_LIFECYCLE_DELETED_ID,
                    DOC_LIFECYCLE_DELETED_ID,
                    f"# Deleted\n\n{LIFECYCLE_SHARED_TERM} deleted retrieval source",
                    "md-hash-lifecycle-deleted",
                ),
            ],
        )

        cur.executemany(
            "UPDATE documents SET current_version_id = %s::uuid, import_status = 'chunked' WHERE id = %s",
            [
                (VER_LIFECYCLE_ACTIVE_ID, DOC_LIFECYCLE_ACTIVE_ID),
                (VER_LIFECYCLE_ARCHIVED_ID, DOC_LIFECYCLE_ARCHIVED_ID),
                (VER_LIFECYCLE_DELETED_ID, DOC_LIFECYCLE_DELETED_ID),
            ],
        )

        cur.executemany(
            """
            INSERT INTO document_chunks
                (id, document_id, document_version_id, chunk_index,
                 heading_path, anchor, content, is_searchable, content_hash,
                 token_estimate, metadata, created_at)
            VALUES
                (%s::uuid, %s::uuid, %s::uuid, 0,
                 '[]'::jsonb, %s, %s, %s, md5(%s),
                 NULL, %s::jsonb, now())
            """,
            [
                (
                    CHUNK_LIFECYCLE_ACTIVE_ID,
                    DOC_LIFECYCLE_ACTIVE_ID,
                    VER_LIFECYCLE_ACTIVE_ID,
                    "anchor-lifecycle-active",
                    (
                        f"{LIFECYCLE_SHARED_TERM} active retrieval source remains visible "
                        "for lifecycle-aware search and chat retrieval validation with enough context."
                    ),
                    True,
                    (
                        f"{LIFECYCLE_SHARED_TERM} active retrieval source remains visible "
                        "for lifecycle-aware search and chat retrieval validation with enough context."
                    ),
                    _NULL_SOURCE_ANCHOR,
                ),
                (
                    CHUNK_LIFECYCLE_ARCHIVED_ID,
                    DOC_LIFECYCLE_ARCHIVED_ID,
                    VER_LIFECYCLE_ARCHIVED_ID,
                    "anchor-lifecycle-archived",
                    f"{LIFECYCLE_SHARED_TERM} archived retrieval source must stay hidden",
                    False,
                    f"{LIFECYCLE_SHARED_TERM} archived retrieval source must stay hidden",
                    _NULL_SOURCE_ANCHOR,
                ),
                (
                    CHUNK_LIFECYCLE_DELETED_ID,
                    DOC_LIFECYCLE_DELETED_ID,
                    VER_LIFECYCLE_DELETED_ID,
                    "anchor-lifecycle-deleted",
                    f"{LIFECYCLE_SHARED_TERM} deleted retrieval source must stay hidden",
                    False,
                    f"{LIFECYCLE_SHARED_TERM} deleted retrieval source must stay hidden",
                    _NULL_SOURCE_ANCHOR,
                ),
            ],
        )

        cur.execute(
            "UPDATE documents SET lifecycle_status = 'archived', archived_at = now() WHERE id = %s",
            (DOC_LIFECYCLE_ARCHIVED_ID,),
        )
        cur.execute(
            "UPDATE documents SET lifecycle_status = 'deleted', deleted_at = now() WHERE id = %s",
            (DOC_LIFECYCLE_DELETED_ID,),
        )

    conn.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_db_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping M3b search integration test")
    return url


@pytest.fixture(scope="module")
def pg_engine(test_db_url: str):
    engine = create_engine(_sa_url(test_db_url), pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def search_test_setup(test_db_url: str) -> Iterator[None]:
    original_url = settings.database_url
    settings.database_url = test_db_url

    config = make_alembic_config()
    try:
        command.downgrade(config, "base")
        command.upgrade(config, "head")

        with psycopg.connect(psycopg_url(test_db_url)) as conn:
            _insert_test_data(conn)

        yield
    finally:
        command.downgrade(config, "base")
        settings.database_url = original_url


@pytest.fixture
def client(search_test_setup, pg_engine) -> Iterator[TestClient]:
    def override_search_service() -> Iterator[SearchService]:
        with Session(pg_engine) as session:
            yield SearchService.from_session(session)

    app.dependency_overrides[search_api.get_search_service] = override_search_service
    try:
        yield TestClient(app, headers={
            "Authorization": f"Bearer {SESSION_TOKEN}",
            "X-Workspace-Id": WORKSPACE_ID,
        })
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_search_returns_at_least_one_hit(client: TestClient) -> None:
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "programming"},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1


def test_search_result_has_required_fields(client: TestClient) -> None:
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "machine"},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1

    result = results[0]
    assert result["chunk_id"] == CHUNK_ML_ID
    assert result["document_id"] == DOC_ML_ID
    assert result["rank"] > 0.0
    assert "source_anchor" in result
    assert "type" in result["source_anchor"]


def test_search_ranking_order_is_deterministic(client: TestClient) -> None:
    # Ranking expectation:
    # 1. rank DESC: CHUNK_RANK_STRONG_ID repeats the exact query terms.
    # 2. document.created_at DESC: NEW beats OLD for equal-rank chunks.
    # 3. chunk_index ASC: index 0 beats index 1 inside the same document.
    # 4. chunk_id ASC: LOW beats HIGH when rank, created_at and chunk_index tie.
    expected_order = [
        CHUNK_RANK_STRONG_ID,
        CHUNK_RANK_NEW_ID,
        CHUNK_RANK_OLD_ID,
        CHUNK_RANK_INDEX_0_ID,
        CHUNK_RANK_INDEX_1_ID,
        CHUNK_RANK_ID_LOW,
        CHUNK_RANK_ID_HIGH,
    ]

    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": RANKING_QUERY, "limit": len(expected_order)},
    )

    assert response.status_code == 200
    results = response.json()
    assert [result["chunk_id"] for result in results] == expected_order

    ranks = {result["chunk_id"]: result["rank"] for result in results}
    assert ranks[CHUNK_RANK_STRONG_ID] > ranks[CHUNK_RANK_NEW_ID]
    for chunk_id in expected_order[1:]:
        assert ranks[chunk_id] == ranks[CHUNK_RANK_NEW_ID]


def test_search_chunks_http_contract_filters_to_current_readable_workspace_chunks(client: TestClient) -> None:
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "programming"},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1

    chunk_ids = {result["chunk_id"] for result in results}
    document_ids = {result["document_id"] for result in results}

    assert CHUNK_PYTHON_ID in chunk_ids
    assert CHUNK_PYTHON_OLD_ID not in chunk_ids
    assert CHUNK_FAILED_ID not in chunk_ids
    assert CHUNK_PENDING_ID not in chunk_ids
    assert CHUNK_OTHER_WS_ID not in chunk_ids
    assert CHUNK_ARCHIVED_ID not in chunk_ids
    assert document_ids <= {DOC_PYTHON_ID, DOC_ML_ID, DOC_DB_ID}

    for result in results:
        assert result["chunk_id"]
        assert result["document_id"] in {DOC_PYTHON_ID, DOC_ML_ID, DOC_DB_ID}
        assert result["document_version_id"]
        assert isinstance(result["source_anchor"], dict)
        assert result["source_anchor"]["type"] in {"text", "pdf_page", "docx_paragraph", "legacy_unknown"}
        assert isinstance(result["rank"], float)
        assert result["rank"] > 0.0


def test_search_hits_belong_to_queried_workspace(client: TestClient) -> None:
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "programming"},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1

    document_ids = {r["document_id"] for r in results}
    assert document_ids <= {DOC_PYTHON_ID, DOC_ML_ID, DOC_DB_ID}


def test_search_excludes_non_current_version_chunks(client: TestClient) -> None:
    # "oldversion" appears only in the old (non-current) version of DOC_PYTHON
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "oldversion"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_excludes_failed_documents(client: TestClient) -> None:
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "failedcontent"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_excludes_pending_documents(client: TestClient) -> None:
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "pendingcontent"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_excludes_archived_documents(client: TestClient) -> None:
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "archivedcontent"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_excludes_deleted_documents(client: TestClient) -> None:
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "deletedcontent"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_excludes_other_workspace_chunks(client: TestClient) -> None:
    # "exclusiveterm" only exists in OTHER_WS_ID; querying WORKSPACE_ID returns nothing
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "exclusiveterm"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_finds_chunk_in_correct_workspace(client: TestClient) -> None:
    # Querying OTHER_WS_ID for the same term must find exactly the right chunk
    response = client.get(
        "/api/v1/search/chunks",
        params={"q": "exclusiveterm"},
        headers={"X-Workspace-Id": OTHER_WS_ID},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["chunk_id"] == CHUNK_OTHER_WS_ID
    assert results[0]["document_id"] == DOC_OTHER_WS_ID


def test_search_current_python_chunk_found_not_old_version(client: TestClient) -> None:
    # "programming" matches both CHUNK_PYTHON_OLD and CHUNK_PYTHON,
    # but only the current version chunk (CHUNK_PYTHON_ID) must appear.
    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "programming"},
    )

    assert response.status_code == 200
    results = response.json()
    chunk_ids = [r["chunk_id"] for r in results]
    assert CHUNK_PYTHON_ID in chunk_ids
    assert CHUNK_PYTHON_OLD_ID not in chunk_ids


def test_search_index_rebuild_recreates_missing_index_and_search_still_returns_results(
    client: TestClient,
    pg_engine,
    test_db_url: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with psycopg.connect(psycopg_url(test_db_url)) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP INDEX IF EXISTS ix_document_chunks_search_vector")
        conn.commit()
        assert _index_exists(conn, "ix_document_chunks_search_vector") is False

    with Session(pg_engine) as session:
        with caplog.at_level(logging.INFO, logger="app.services.search_index_service"):
            result = SearchIndexRebuildService.from_session(session).rebuild_search_index(workspace_id=WORKSPACE_ID)

    assert result == {
        "workspace_id": WORKSPACE_ID,
        "reindexed_chunk_count": 13,
        "reindexed_document_count": 11,
        "index_name": "ix_document_chunks_search_vector",
        "index_action": "created",
        "status": "completed",
    }

    with psycopg.connect(psycopg_url(test_db_url)) as conn:
        assert _index_exists(conn, "ix_document_chunks_search_vector") is True

    response = client.get(
        "/api/v1/search/chunks",
        params={"workspace_id": WORKSPACE_ID, "q": "programming"},
    )

    assert response.status_code == 200
    chunk_ids = [row["chunk_id"] for row in response.json()]
    assert CHUNK_PYTHON_ID in chunk_ids
    assert CHUNK_ARCHIVED_ID not in chunk_ids
    assert CHUNK_DELETED_ID not in chunk_ids
    assert "programming language used for software development" not in caplog.text


def test_lifecycle_e2e_excludes_archived_deleted_from_search_chat_and_reindex(
    client: TestClient,
    pg_engine,
    test_db_url: str,
) -> None:
    with psycopg.connect(psycopg_url(test_db_url)) as conn:
        _insert_lifecycle_retrieval_data(conn)

    search_response = client.get(
        "/api/v1/search/chunks",
        params={"q": LIFECYCLE_SHARED_TERM},
    )

    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert [item["document_id"] for item in search_payload] == [DOC_LIFECYCLE_ACTIVE_ID]
    assert [item["chunk_id"] for item in search_payload] == [CHUNK_LIFECYCLE_ACTIVE_ID]

    provider = FakeLlmProvider()

    def override_rag_chat_service() -> Iterator[RagChatService]:
        with Session(pg_engine) as session:
            yield RagChatService(
                persistence=ChatPersistenceService.from_session(session),
                retrieval=SearchService.from_session(session),
                context_builder=ContextBuilder(max_context_chars=12000, max_context_tokens=2500, min_chunk_chars=40),
                insufficient_context_policy=InsufficientContextPolicy(
                    InsufficientContextThresholds(min_retrieval_score=0.0, min_top_chunk_chars=1)
                ),
                prompt_builder=PromptBuilder(),
                llm_provider=provider,
                citation_mapper=CitationMapper(),
                retrieval_limit=8,
            )

    app.dependency_overrides[chat_api.get_rag_chat_service] = override_rag_chat_service
    try:
        session_response = client.post(
            "/api/v1/chat/sessions",
            json={"title": "Lifecycle Retrieval Check"},
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        chat_response = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"question": LIFECYCLE_SHARED_TERM, "retrieval_limit": 8},
        )
    finally:
        app.dependency_overrides.pop(chat_api.get_rag_chat_service, None)

    assert chat_response.status_code == 201, chat_response.json()
    chat_payload = chat_response.json()
    assert [citation["document_id"] for citation in chat_payload["citations"]] == [DOC_LIFECYCLE_ACTIVE_ID]
    assert [citation["chunk_id"] for citation in chat_payload["citations"]] == [CHUNK_LIFECYCLE_ACTIVE_ID]
    assert [citation["source_status"] for citation in chat_payload["citations"]] == ["active"]
    assert len(provider.calls) == 1
    assert f"chunk_id: {CHUNK_LIFECYCLE_ACTIVE_ID}" in provider.calls[0].user_prompt
    assert CHUNK_LIFECYCLE_ARCHIVED_ID not in provider.calls[0].user_prompt
    assert CHUNK_LIFECYCLE_DELETED_ID not in provider.calls[0].user_prompt

    with psycopg.connect(psycopg_url(test_db_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE document_chunks
                SET is_searchable = true
                WHERE id IN (%s, %s)
                """,
                (CHUNK_LIFECYCLE_ARCHIVED_ID, CHUNK_LIFECYCLE_DELETED_ID),
            )
        conn.commit()

    with Session(pg_engine) as session:
        rebuild_result = SearchIndexRebuildService.from_session(session).rebuild_search_index(workspace_id=WORKSPACE_ID)

    assert rebuild_result["status"] == "completed"

    with psycopg.connect(psycopg_url(test_db_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, is_searchable
                FROM document_chunks
                WHERE id IN (%s, %s, %s)
                ORDER BY id ASC
                """,
                (
                    CHUNK_LIFECYCLE_ACTIVE_ID,
                    CHUNK_LIFECYCLE_ARCHIVED_ID,
                    CHUNK_LIFECYCLE_DELETED_ID,
                ),
            )
            rows = cur.fetchall()

    assert rows == [
        (CHUNK_LIFECYCLE_ACTIVE_ID, True),
        (CHUNK_LIFECYCLE_ARCHIVED_ID, False),
        (CHUNK_LIFECYCLE_DELETED_ID, False),
    ]

    search_after_reindex = client.get(
        "/api/v1/search/chunks",
        params={"q": LIFECYCLE_SHARED_TERM},
    )
    assert search_after_reindex.status_code == 200
    assert [item["document_id"] for item in search_after_reindex.json()] == [DOC_LIFECYCLE_ACTIVE_ID]
