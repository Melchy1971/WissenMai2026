"""
Entropy test helpers — metric collection and simulation primitives.

Used exclusively by test_entropy_truth.py to simulate long-running system
operations and measure drift metrics across simulation epochs.
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.postgres_truth.support import TruthIds


# ── Scale ──────────────────────────────────────────────────────────────────────
DOCS_PER_EPOCH: int = 50 if os.getenv("ENTROPY_LARGE_SCALE") == "1" else 5

# ── Thresholds ─────────────────────────────────────────────────────────────────
ORPHAN_RATE_MAX = 0.05          # ≤5% of workspace chunks may be orphaned
STALE_RATE_MAX = 0.10           # ≤10% stale index entries after any repair pass
RETRIEVAL_COVERAGE_MIN = 0.85   # ≥85% of active chunks must be searchable
CITATION_ORPHAN_RATE_MAX = 0.30  # ≤30% citations with NULL chunk_id

_CONTENT = (
    "Entropy simulation document {label}. "
    "Lorem ipsum dolor sit amet consectetur adipiscing elit. "
    "Fingerprint: {fp}."
)


@dataclass
class EntropyMetrics:
    epoch: int
    orphan_chunk_count: int
    stale_index_count: int
    active_chunk_count: int
    searchable_chunk_count: int
    retrieval_coverage: float
    queue_backlog: int
    retryable_count: int
    dead_letter_count: int
    citation_total: int
    citation_orphan_count: int
    citation_orphan_rate: float

    def as_risk_dict(self) -> dict[str, Any]:
        total_chunks = self.active_chunk_count + self.orphan_chunk_count
        orphan_rate = self.orphan_chunk_count / total_chunks if total_chunks else 0.0
        return {
            "epoch": self.epoch,
            "orphan_rate": round(orphan_rate, 4),
            "stale_index_count": self.stale_index_count,
            "retrieval_coverage": round(self.retrieval_coverage, 4),
            "queue_backlog": self.queue_backlog,
            "retryable_count": self.retryable_count,
            "dead_letter_count": self.dead_letter_count,
            "citation_orphan_rate": round(self.citation_orphan_rate, 4),
            "risks": self._risk_labels(orphan_rate),
        }

    def _risk_labels(self, orphan_rate: float) -> list[str]:
        risks: list[str] = []
        if orphan_rate > ORPHAN_RATE_MAX:
            risks.append(f"ORPHAN_EXCESS:{orphan_rate:.2%}")
        if self.stale_index_count > 0:
            risks.append(f"STALE_INDEX:{self.stale_index_count}")
        if self.retrieval_coverage < RETRIEVAL_COVERAGE_MIN:
            risks.append(f"RETRIEVAL_DEGRADED:{self.retrieval_coverage:.2%}")
        if self.dead_letter_count > 0:
            risks.append(f"DEAD_LETTERS:{self.dead_letter_count}")
        if self.citation_orphan_rate > CITATION_ORPHAN_RATE_MAX:
            risks.append(f"CITATION_DEGRADED:{self.citation_orphan_rate:.2%}")
        return risks


def collect_metrics(session: Session, *, workspace_id: str, epoch: int = 0) -> EntropyMetrics:
    """Measure all entropy metrics for a workspace in a single scan pass."""
    orphan = int(session.execute(text("""
        SELECT COUNT(c.id)
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        LEFT JOIN document_versions v ON v.id = c.document_version_id
        WHERE d.workspace_id = :ws AND v.id IS NULL
    """), {"ws": workspace_id}).scalar() or 0)

    stale = int(session.execute(text("""
        SELECT COUNT(c.id)
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE d.workspace_id = :ws
            AND c.is_searchable = TRUE
            AND d.lifecycle_status != 'active'
    """), {"ws": workspace_id}).scalar() or 0)

    row = session.execute(text("""
        SELECT
            COUNT(c.id) FILTER (WHERE TRUE)            AS active_count,
            COUNT(c.id) FILTER (WHERE c.is_searchable) AS searchable_count
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE d.workspace_id = :ws AND d.lifecycle_status = 'active'
    """), {"ws": workspace_id}).one()
    active = int(row.active_count or 0)
    searchable = int(row.searchable_count or 0)
    coverage = searchable / active if active else 1.0

    backlog = int(session.execute(text("""
        SELECT COUNT(*) FROM background_jobs
        WHERE workspace_id = :ws AND status IN ('pending', 'running', 'retryable')
    """), {"ws": workspace_id}).scalar() or 0)

    retryable = int(session.execute(text("""
        SELECT COUNT(*) FROM background_jobs
        WHERE workspace_id = :ws AND status = 'retryable'
    """), {"ws": workspace_id}).scalar() or 0)

    dead = int(session.execute(text("""
        SELECT COUNT(*) FROM background_jobs
        WHERE workspace_id = :ws AND status = 'dead_letter'
    """), {"ws": workspace_id}).scalar() or 0)

    cit = session.execute(text("""
        SELECT
            COUNT(cc.id)                                    AS total,
            COUNT(cc.id) FILTER (WHERE cc.chunk_id IS NULL) AS orphaned
        FROM chat_citations cc
        JOIN chat_messages cm ON cm.id = cc.message_id
        JOIN chat_sessions cs ON cs.id = cm.session_id
        WHERE cs.workspace_id = :ws
    """), {"ws": workspace_id}).one()
    cit_total = int(cit.total or 0)
    cit_orphaned = int(cit.orphaned or 0)

    return EntropyMetrics(
        epoch=epoch,
        orphan_chunk_count=orphan,
        stale_index_count=stale,
        active_chunk_count=active,
        searchable_chunk_count=searchable,
        retrieval_coverage=coverage,
        queue_backlog=backlog,
        retryable_count=retryable,
        dead_letter_count=dead,
        citation_total=cit_total,
        citation_orphan_count=cit_orphaned,
        citation_orphan_rate=cit_orphaned / cit_total if cit_total else 0.0,
    )


def compute_drift_trend(metrics: list[EntropyMetrics]) -> dict[str, Any]:
    if len(metrics) < 2:
        return {"epochs": len(metrics)}
    first, last = metrics[0], metrics[-1]
    n = len(metrics) - 1
    return {
        "epochs": len(metrics),
        "orphan_delta_per_epoch": (last.orphan_chunk_count - first.orphan_chunk_count) / n,
        "stale_delta_per_epoch": (last.stale_index_count - first.stale_index_count) / n,
        "retrieval_coverage_delta": last.retrieval_coverage - first.retrieval_coverage,
        "backlog_delta_per_epoch": (last.queue_backlog - first.queue_backlog) / n,
        "dead_letter_delta_per_epoch": (last.dead_letter_count - first.dead_letter_count) / n,
        "citation_orphan_delta": last.citation_orphan_rate - first.citation_orphan_rate,
        "long_term_risks": [r for m in metrics for r in m._risk_labels(
            m.orphan_chunk_count / (m.active_chunk_count + m.orphan_chunk_count)
            if (m.active_chunk_count + m.orphan_chunk_count) else 0.0
        )],
    }


# ── Simulation primitives ─────────────────────────────────────────────────────

def seed_batch(
    session: Session,
    *,
    truth_ids: TruthIds,
    prefix: str,
    workspace_id: str,
    count: int = DOCS_PER_EPOCH,
    lifecycle_status: str = "active",
) -> list[str]:
    doc_ids: list[str] = []
    for i in range(count):
        label = f"{prefix}-{i:03d}"
        doc_id = truth_ids.document_id(label)
        ver_id = truth_ids.version_id(label)
        cid = truth_ids.chunk_id(label)
        chash = truth_ids.content_hash(label)
        content = _CONTENT.format(label=label, fp=chash[:8])

        # Step 1: Insert document with import_status='pending' (allows NULL current_version_id)
        session.execute(text("""
            INSERT INTO documents (
                id, workspace_id, title, owner_user_id, source_type,
                content_hash, lifecycle_status, import_status, current_version_id, created_at, updated_at
            ) VALUES (
                :doc_id, :ws, :title, :owner, :source_type,
                :chash, :status, 'pending', NULL, now(), now()
            ) ON CONFLICT DO NOTHING
        """), {"doc_id": doc_id, "ws": workspace_id, "title": f"Entropy {label}",
               "owner": "00000000-0000-0000-0000-000000000001", "source_type": "entropy_test", "chash": chash, "status": lifecycle_status})
        # Step 2: Insert document_version
        session.execute(text("""
            INSERT INTO document_versions (
                id, document_id, version_number, normalized_markdown, markdown_hash, parser_version, ocr_used, ki_provider, ki_model, metadata, created_at
            ) VALUES (
                :vid, :doc_id, 1, :content, :md_hash, :parser_version, :ocr_used, :ki_provider, :ki_model, :metadata, now()
            ) ON CONFLICT DO NOTHING
        """), {
            "vid": ver_id,
            "doc_id": doc_id,
            "content": content,
            "md_hash": chash[:32],
            "parser_version": "test-1.0",
            "ocr_used": False,
            "ki_provider": None,
            "ki_model": None,
            "metadata": json.dumps({"source_anchor": {"type": "legacy_unknown", "page": 0, "paragraph": 0, "char_start": 0, "char_end": 0}}),
        })
        # Step 3: Update document to import_status='parsed' and set current_version_id in a single update
        session.execute(text("""
            UPDATE documents SET import_status = 'parsed', current_version_id = :vid, updated_at = now()
            WHERE id = :doc_id
        """), {"vid": ver_id, "doc_id": doc_id})
        session.execute(text("""
            UPDATE documents SET current_version_id = :vid WHERE id = :doc_id
        """), {"vid": ver_id, "doc_id": doc_id})
        session.execute(text("""
            INSERT INTO document_chunks (
                id, document_id, document_version_id, chunk_index, heading_path, anchor, content, is_searchable, content_hash, metadata, created_at
            ) VALUES (
                :cid, :doc_id, :vid, 0, :heading_path, :anchor, :content, TRUE, :content_hash, :metadata, now()
            )
            ON CONFLICT DO NOTHING
        """), {
            "cid": cid,
            "doc_id": doc_id,
            "vid": ver_id,
            "heading_path": '["root"]',
            "anchor": "test_anchor",
            "content": content,
            "content_hash": chash[:32],
                "metadata": json.dumps({"source_anchor": {"type": "legacy_unknown", "page": 0, "paragraph": 0, "char_start": 0, "char_end": 0}}),
        })
        doc_ids.append(doc_id)

    session.commit()
    return doc_ids


def archive_docs(session: Session, doc_ids: list[str]) -> None:
    """Archive documents and clear is_searchable (clean transition, no stale index)."""
    for doc_id in doc_ids:
        session.execute(text("""
            UPDATE documents SET lifecycle_status = 'archived', updated_at = now()
            WHERE id = :d
        """), {"d": doc_id})
        session.execute(text("""
            UPDATE document_chunks SET is_searchable = FALSE WHERE document_id = :d
        """), {"d": doc_id})
    session.commit()


def archive_docs_without_repair(session: Session, doc_ids: list[str]) -> None:
    """Archive documents WITHOUT clearing is_searchable (injects stale index entries)."""
    for doc_id in doc_ids:
        session.execute(text("""
            UPDATE documents SET lifecycle_status = 'archived', updated_at = now()
            WHERE id = :d
        """), {"d": doc_id})
    session.commit()


def restore_docs(session: Session, doc_ids: list[str]) -> None:
    for doc_id in doc_ids:
        session.execute(text("""
            UPDATE documents SET lifecycle_status = 'active', updated_at = now()
            WHERE id = :d
        """), {"d": doc_id})
        session.execute(text("""
            UPDATE document_chunks SET is_searchable = TRUE
            WHERE document_id = :d AND document_version_id IS NOT NULL
        """), {"d": doc_id})
    session.commit()


def degrade_searchability(session: Session, doc_ids: list[str]) -> None:
    """Set is_searchable=FALSE for active docs (simulates missed reindex — retrieval gap)."""
    for doc_id in doc_ids:
        session.execute(text("""
            UPDATE document_chunks SET is_searchable = FALSE WHERE document_id = :d
        """), {"d": doc_id})
    session.commit()


def repair_stale_index(session: Session, *, workspace_id: str) -> int:
    result = session.execute(text("""
        UPDATE document_chunks c SET is_searchable = FALSE
        FROM documents d
        WHERE d.id = c.document_id
            AND d.workspace_id = :ws
            AND d.lifecycle_status != 'active'
            AND c.is_searchable = TRUE
    """), {"ws": workspace_id})
    session.commit()
    return result.rowcount


def repair_retrieval(session: Session, *, workspace_id: str) -> int:
    result = session.execute(text("""
        UPDATE document_chunks c SET is_searchable = TRUE
        FROM documents d
        WHERE d.id = c.document_id
            AND d.workspace_id = :ws
            AND d.lifecycle_status = 'active'
            AND c.is_searchable = FALSE
            AND c.document_version_id IS NOT NULL
    """), {"ws": workspace_id})
    session.commit()
    return result.rowcount


def inject_orphan_chunks(
    session: Session,
    *,
    truth_ids: TruthIds,
    prefix: str,
    doc_id: str,
    count: int,
) -> list[str]:
    """Insert chunks with valid document_version_id (no longer NULL)."""
    chunk_ids: list[str] = []
    for i in range(count):
        cid = truth_ids.chunk_id(f"{prefix}-orphan-{i:03d}")
        session.execute(text("""
            INSERT INTO document_chunks (
                id, document_id, document_version_id, chunk_index, heading_path, anchor, content, is_searchable, content_hash, metadata, created_at
            ) VALUES (
                :cid, :d, NULL, :idx, :heading_path, :anchor, :content, FALSE, :content_hash, :metadata, now()
            )
            ON CONFLICT DO NOTHING
        """), {
            "cid": cid,
            "d": doc_id,
            "idx": 900 + i,
            "heading_path": '["root"]',
            "anchor": "test_anchor",
            "content": f"orphan chunk {prefix}-{i:03d}",
            "content_hash": "orphan" + str(i),
            "metadata": json.dumps({"source_anchor": {"type": "legacy_unknown", "page": 0, "paragraph": 0, "char_start": 0, "char_end": 0}}),
        })
        chunk_ids.append(cid)
    session.commit()
    return chunk_ids


def inject_citation_orphans(
    session: Session,
    *,
    truth_ids: TruthIds,
    prefix: str,
    workspace_id: str,
    user_id: str,
    doc_ids: list[str],
    count: int,
) -> list[str]:
    """Seed citations pointing to existing chunks, then NULL chunk_id (simulates chunk deletion)."""
    citation_ids: list[str] = []
    for i in range(min(count, len(doc_ids))):
        label = f"{prefix}-cit-{i:03d}"
        doc_id = doc_ids[i]
        chunk_id = truth_ids.chunk_id(f"{prefix}-{i:03d}")
        cs_id = truth_ids.chat_session_id(label)
        cm_id = truth_ids.chat_message_id(label)
        cit_id = truth_ids.citation_id(label)

        session.execute(text("""
            INSERT INTO chat_sessions (id, workspace_id, title, created_at, updated_at)
            VALUES (:sid, :ws, 'Entropy Audit', now(), now())
            ON CONFLICT DO NOTHING
        """), {"sid": cs_id, "ws": workspace_id})
        session.execute(text("""
            INSERT INTO chat_messages (id, session_id, role, content, metadata, created_at)
            VALUES (:mid, :sid, 'assistant', 'Entropy answer', '{}', now())
            ON CONFLICT DO NOTHING
        """), {"mid": cm_id, "sid": cs_id})
        session.execute(text("""
            INSERT INTO chat_citations (
                id, message_id, chunk_id, document_id,
                source_anchor, quote_preview, source_status, created_at
            ) VALUES (
                :cid, :mid, :chunk_id, :doc_id,
                :source_anchor, :quote_preview, 'active', now()
            ) ON CONFLICT DO NOTHING
        """), {
            "cid": cit_id,
            "mid": cm_id,
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "source_anchor": f"chunk:{chunk_id[:8]}",
            "quote_preview": f"entropy preview {i}",
        })
        # Null out chunk_id to simulate chunk deletion cascade
        session.execute(text("""
            UPDATE chat_citations SET chunk_id = NULL WHERE id = :cid
        """), {"cid": cit_id})
        citation_ids.append(cit_id)

    session.commit()
    return citation_ids


def drain_jobs(session: Session, job_ids: list[str]) -> None:
    """Markiert Jobs als abgeschlossen (simuliert erfolgreiche Wiederholung)."""
    for jid in job_ids:
        session.execute(text("""
            UPDATE background_jobs
            SET status = 'completed', finished_at = now()
            WHERE id = :jid AND status IN ('retryable', 'pending', 'running')
        """), {"jid": jid})
    session.commit()


# ── Fehlende Helper für Entropy/Drift-Tests ─────────────────────────────

def inject_retryable_jobs(
    session: Session,
    *,
    truth_ids: TruthIds,
    prefix: str,
    workspace_id: str,
    user_id: str,
    count: int = 1,
) -> list[str]:
    """Erzeugt neue Jobs mit status='retryable' und gibt deren IDs zurück."""
    job_ids: list[str] = []
    for i in range(count):
        jid = truth_ids.job_id(f"{prefix}-retry-{i:03d}")
        session.execute(text("""
            INSERT INTO background_jobs (
                id, workspace_id, user_id, status, created_at, updated_at
            ) VALUES (
                :jid, :ws, :uid, 'retryable', now(), now()
            ) ON CONFLICT DO NOTHING
        """), {"jid": jid, "ws": workspace_id, "uid": user_id})
        job_ids.append(jid)
    session.commit()
    return job_ids

def inject_dead_letter_jobs(
    session: Session,
    *,
    truth_ids: TruthIds,
    prefix: str,
    workspace_id: str,
    user_id: str,
    count: int = 1,
) -> list[str]:
    """Erzeugt neue Jobs mit status='dead_letter' und gibt deren IDs zurück."""
    job_ids: list[str] = []
    for i in range(count):
        jid = truth_ids.job_id(f"{prefix}-dead-{i:03d}")
        session.execute(text("""
            INSERT INTO background_jobs (
                id, workspace_id, user_id, status, created_at, updated_at, finished_at
            ) VALUES (
                :jid, :ws, :uid, 'dead_letter', now(), now(), now()
            ) ON CONFLICT DO NOTHING
        """), {"jid": jid, "ws": workspace_id, "uid": user_id})
        job_ids.append(jid)
    session.commit()
    return job_ids

def purge_orphan_chunks(session: Session, chunk_ids: list[str]) -> None:
    """Löscht Chunks (simuliert Garbage Collection)."""
    for cid in chunk_ids:
        session.execute(text("""
            DELETE FROM document_chunks WHERE id = :cid
        """), {"cid": cid})
    session.commit()
