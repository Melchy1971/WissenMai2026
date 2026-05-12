"""
Retrieval Benchmark Runner — seeds corpus, runs golden queries, computes metrics.

Metrics:
  Precision@K        = TP / retrieved (macro-averaged over non-empty-expected queries)
  Recall@K           = TP / expected (macro-averaged over all queries)
  Citation Completeness = total expected chunks found / total expected chunks
  Missing Context Rate  = queries with ≥1 missing expected chunk / non-empty queries
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.repositories.search import SearchRepository
from tests.retrieval_benchmark.corpus import (
    ARCHIVED_DOCUMENT,
    BENCHMARK_CORPUS,
    GOLDEN_QUERIES,
    BenchmarkDocument,
    GoldenQuery,
)


BENCH_NAMESPACE = "retrieval-benchmark-v1"
BENCH_WORKSPACE_ID = "b0000000-1000-0000-0000-000000000001"
BENCH_USER_ID = "b0000000-2000-0000-0000-000000000001"
BENCH_MEMBERSHIP_ID = "bench-membership-regression-v1"


def _stable_id(prefix: str, label: str) -> str:
    h = hashlib.sha1(f"{BENCH_NAMESPACE}:{label}".encode()).hexdigest()
    return f"{prefix}-{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:24]}"


def doc_id(label: str) -> str:
    return _stable_id("b3000000", label)


def version_id(label: str) -> str:
    return _stable_id("b5000000", label)


def chunk_id(label: str) -> str:
    return _stable_id("b4000000", label)


def content_hash(label: str) -> str:
    h = hashlib.sha1(f"{BENCH_NAMESPACE}:hash:{label}".encode()).hexdigest()
    return f"bench-hash-{h[:20]}"


@dataclass
class QueryResult:
    query: GoldenQuery
    retrieved_chunk_ids: list[str]
    retrieved_labels: list[str]
    precision_at_k: float
    recall_at_k: float
    missing_expected: list[str]
    rank_of_first_expected: int | None


@dataclass
class BenchmarkResult:
    run_at: str
    database_url_host: str
    precision_at_k: float
    recall_at_k: float
    citation_completeness: float
    missing_context_rate: float
    total_queries: int
    passed_queries: int
    query_results: list[QueryResult]


class RetrievalBenchmarkRunner:
    def __init__(self, database_url: str) -> None:
        self._db_url = database_url
        if database_url.startswith("postgresql+psycopg://"):
            self._psycopg_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
            self._sa_url = database_url
        elif database_url.startswith("postgresql://"):
            self._psycopg_url = database_url
            self._sa_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        else:
            self._psycopg_url = database_url
            self._sa_url = database_url

    def seed(self) -> None:
        with psycopg.connect(self._psycopg_url) as conn:
            with conn.cursor() as cur:
                self._ensure_workspace(cur)
                for doc in BENCHMARK_CORPUS:
                    self._upsert_document(cur, doc, lifecycle_status="active")
                self._upsert_document(cur, ARCHIVED_DOCUMENT, lifecycle_status="archived")
            conn.commit()

    def cleanup(self) -> None:
        with psycopg.connect(self._psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "delete from document_chunks where document_id in "
                    "(select id from documents where workspace_id = %s::uuid)",
                    (BENCH_WORKSPACE_ID,),
                )
                cur.execute(
                    "update documents set current_version_id = null where workspace_id = %s::uuid",
                    (BENCH_WORKSPACE_ID,),
                )
                cur.execute(
                    "delete from document_versions where document_id in "
                    "(select id from documents where workspace_id = %s::uuid)",
                    (BENCH_WORKSPACE_ID,),
                )
                cur.execute(
                    "delete from documents where workspace_id = %s::uuid",
                    (BENCH_WORKSPACE_ID,),
                )
                cur.execute(
                    "delete from workspace_memberships where id = %s",
                    (BENCH_MEMBERSHIP_ID,),
                )
                cur.execute(
                    "delete from users where id = %s::uuid",
                    (BENCH_USER_ID,),
                )
                cur.execute(
                    "delete from workspaces where id = %s::uuid",
                    (BENCH_WORKSPACE_ID,),
                )
            conn.commit()

    def run(self) -> BenchmarkResult:
        self.seed()
        results = self._evaluate()
        return self._aggregate(results)

    def _ensure_workspace(self, cur) -> None:
        cur.execute(
            "insert into workspaces (id, name, is_default, created_at) "
            "values (%s::uuid, 'Retrieval Benchmark Workspace', false, now()) "
            "on conflict (id) do nothing",
            (BENCH_WORKSPACE_ID,),
        )
        cur.execute(
            "insert into users (id, display_name, login, password_hash, is_active, is_default, created_at) "
            "values (%s::uuid, 'Benchmark User', 'benchmark-user', 'unused', true, false, now()) "
            "on conflict (id) do nothing",
            (BENCH_USER_ID,),
        )
        cur.execute(
            "insert into workspace_memberships (id, workspace_id, user_id, role, created_at, updated_at) "
            "values (%s, %s::uuid, %s::uuid, 'owner', now(), now()) "
            "on conflict (id) do nothing",
            (BENCH_MEMBERSHIP_ID, BENCH_WORKSPACE_ID, BENCH_USER_ID),
        )

    def _upsert_document(self, cur, doc: BenchmarkDocument, lifecycle_status: str) -> None:
        d_id = doc_id(doc.label)
        v_id = version_id(doc.label)
        c_id = chunk_id(doc.label)
        c_hash = content_hash(doc.label)
        is_active = lifecycle_status == "active"
        archived_at = None if is_active else datetime.now(UTC)

        cur.execute(
            """
            insert into documents
                (id, workspace_id, owner_user_id, current_version_id, title, source_type,
                 mime_type, content_hash, import_status, lifecycle_status,
                 archived_at, deleted_at, created_at, updated_at)
            values (%s, %s::uuid, %s::uuid, null, %s, 'upload', 'text/plain',
                    %s, 'chunked', %s, %s, null, now(), now())
            on conflict (id) do update set
                lifecycle_status = excluded.lifecycle_status,
                archived_at = excluded.archived_at,
                updated_at = now()
            """,
            (d_id, BENCH_WORKSPACE_ID, BENCH_USER_ID, doc.title,
             c_hash, lifecycle_status, archived_at),
        )
        cur.execute(
            """
            insert into document_versions
                (id, document_id, version_number, normalized_markdown, markdown_hash,
                 parser_version, ocr_used, ki_provider, ki_model, metadata, created_at)
            values (%s, %s, 1, %s, %s, 'benchmark-v1', false, null, null, '{}', now())
            on conflict (id) do nothing
            """,
            (v_id, d_id, doc.content, f"md-{c_hash[:20]}"),
        )
        # search_vector is GENERATED ALWAYS AS — must not be in INSERT column list
        cur.execute(
            """
            insert into document_chunks
                (id, document_id, document_version_id, chunk_index, heading_path,
                 anchor, content, is_searchable, content_hash, token_estimate,
                 metadata, created_at)
            values (%s, %s, %s, 0, '[]', %s, %s, %s, %s, %s,
                    '{"source_anchor": {"type": "text", "page": null, "paragraph": 1,
                      "char_start": 0, "char_end": 200}}',
                    now())
            on conflict (id) do update set
                is_searchable = excluded.is_searchable,
                content = excluded.content
            """,
            (c_id, d_id, v_id, f"bench-{c_id[:8]}", doc.content,
             is_active, f"chunk-{c_hash[:20]}", len(doc.content)),
        )
        cur.execute(
            "update documents set current_version_id = %s where id = %s",
            (v_id, d_id),
        )

    def _evaluate(self) -> list[QueryResult]:
        label_to_chunk = {doc.label: chunk_id(doc.label) for doc in BENCHMARK_CORPUS}
        label_to_chunk[ARCHIVED_DOCUMENT.label] = chunk_id(ARCHIVED_DOCUMENT.label)

        engine = create_engine(self._sa_url, pool_pre_ping=True)
        results: list[QueryResult] = []
        try:
            with Session(engine) as session:
                repo = SearchRepository(session)
                for query in GOLDEN_QUERIES:
                    results.append(self._run_query(repo, query, label_to_chunk))
        finally:
            engine.dispose()
        return results

    def _run_query(
        self,
        repo: SearchRepository,
        query: GoldenQuery,
        label_to_chunk: dict[str, str],
    ) -> QueryResult:
        expected_chunk_ids = {chunk_id(label) for label in query.expected_labels}

        records = repo.search_chunks(
            workspace_id=BENCH_WORKSPACE_ID,
            query=query.query,
            limit=query.k,
            offset=0,
        )
        retrieved_ids = [r.chunk_id for r in records]
        retrieved_labels = [
            lbl for lbl, cid in label_to_chunk.items() if cid in retrieved_ids
        ]

        tp = len(set(retrieved_ids) & expected_chunk_ids)

        if query.expect_empty:
            precision = 1.0 if not retrieved_ids else 0.0
            recall = 1.0 if not retrieved_ids else 0.0
        else:
            precision = tp / max(len(retrieved_ids), 1)
            recall = tp / max(len(expected_chunk_ids), 1)

        missing = [
            lbl for lbl in query.expected_labels
            if chunk_id(lbl) not in retrieved_ids
        ]

        rank_of_first: int | None = None
        for i, cid in enumerate(retrieved_ids, 1):
            if cid in expected_chunk_ids:
                rank_of_first = i
                break

        return QueryResult(
            query=query,
            retrieved_chunk_ids=retrieved_ids,
            retrieved_labels=retrieved_labels,
            precision_at_k=round(precision, 4),
            recall_at_k=round(recall, 4),
            missing_expected=missing,
            rank_of_first_expected=rank_of_first,
        )

    def _aggregate(self, results: list[QueryResult]) -> BenchmarkResult:
        non_empty = [r for r in results if not r.query.expect_empty]

        precision_avg = (
            sum(r.precision_at_k for r in non_empty) / len(non_empty)
            if non_empty else 0.0
        )
        recall_avg = (
            sum(r.recall_at_k for r in results) / len(results)
            if results else 0.0
        )

        total_expected = sum(len(r.query.expected_labels) for r in results)
        total_found = sum(
            len(r.query.expected_labels) - len(r.missing_expected)
            for r in results
        )
        citation_completeness = total_found / max(total_expected, 1)

        queries_with_missing = sum(
            1 for r in non_empty if r.missing_expected
        )
        missing_context_rate = queries_with_missing / max(len(non_empty), 1)

        passed = sum(
            1 for r in results
            if r.precision_at_k >= 0.80 and r.recall_at_k >= 0.70
        )

        host = self._db_url.split("@")[-1].split("/")[0] if "@" in self._db_url else "local"

        return BenchmarkResult(
            run_at=datetime.now(UTC).isoformat(),
            database_url_host=host,
            precision_at_k=round(precision_avg, 4),
            recall_at_k=round(recall_avg, 4),
            citation_completeness=round(citation_completeness, 4),
            missing_context_rate=round(missing_context_rate, 4),
            total_queries=len(results),
            passed_queries=passed,
            query_results=results,
        )
