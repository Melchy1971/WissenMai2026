"""
Citation Longevity Audit — Truth Tests.

Simulates long-term lifecycle cycles and verifies that the audit service
detects each degradation category correctly.

Cycles tested:
  1. Baseline clean state → ok severity
  2. archive() → citation synced to archived, 0 drift (lifecycle service works)
  3. delete() → citation synced to deleted, 0 drift
  4. archive() → restore() → citation synced back to active, 0 drift
  5. Status drift: manually stale source_status detected
  6. Deleted document but citation still active → deleted_not_marked detected
  7. Restored document but citation still shows archived → restored_not_marked detected
  8. Rechunk simulation: chunk_id SET NULL, source_status='active' → orphaned_anchor detected
  9. Preview staleness: chunk exists but content changed → preview_stale detected
 10. Workspace isolation: other-workspace citations don't bleed in
 11. API endpoint contract
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.citation_longevity_service import CitationLongevityAuditService
from app.services.documents.lifecycle_service import DocumentLifecycleService
from tests.postgres_truth.support import TruthIds


pytestmark = [pytest.mark.postgres_truth, pytest.mark.citation_longevity]


_ANCHOR = json.dumps({"type": "text", "page": None, "paragraph": None, "char_start": 0, "char_end": 100})
_CONTENT = "Longevity test content. This is a stable reference sentence used for citation anchoring."
_PREVIEW = "Longevity test content. This is a stable reference sentence used for citation anchoring."


def _seed_document(
    session: Session,
    *,
    truth_ids: TruthIds,
    label: str,
    workspace_id: str,
    user_id: str,
    lifecycle_status: str = "active",
    content: str = _CONTENT,
) -> tuple[str, str, str]:
    doc_id = truth_ids.document_id(label)
    version_id = truth_ids.version_id(label)
    chunk_id = truth_ids.chunk_id(label)
    content_hash = truth_ids.content_hash(label)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    session.execute(
        text(
            """
            INSERT INTO documents (
                id, workspace_id, owner_user_id, current_version_id, title,
                source_type, mime_type, content_hash, import_status,
                lifecycle_status, archived_at, deleted_at, created_at, updated_at
            ) VALUES (
                CAST(:id AS uuid), CAST(:ws AS uuid), CAST(:user AS uuid), null, :title,
                'upload', 'text/plain', :hash, 'pending',
                'active', null, null, :now, :now
            )
            """
        ),
        {"id": doc_id, "ws": workspace_id, "user": user_id, "title": f"Doc {label}",
         "hash": content_hash, "status": lifecycle_status, "now": now},
    )
    session.execute(
        text(
            """
            INSERT INTO document_versions (
                id, document_id, version_number, normalized_markdown, markdown_hash,
                parser_version, ocr_used, ki_provider, ki_model, metadata, created_at
            ) VALUES (
                :id, :doc_id, 1, :content, :hash,
                '1.0', false, null, null, '{}', :now
            )
            """
        ),
        {"id": version_id, "doc_id": doc_id, "content": content,
         "hash": content_hash + "-md", "now": now},
    )
    session.execute(
        text(
            """
            INSERT INTO document_chunks (
                id, document_id, document_version_id, chunk_index,
                heading_path, anchor, content, content_hash, token_estimate,
                metadata, is_searchable, created_at
            ) VALUES (
                :id, :doc_id, :version_id, 0,
                '[]', 'dv:longevity:c0000', :content, :hash, 10,
                jsonb_build_object('source_anchor', cast(:anchor as jsonb)), :searchable, :now
            )
            """
        ),
        {"id": chunk_id, "doc_id": doc_id, "version_id": version_id,
         "content": content, "hash": content_hash + "-chunk",
         "searchable": lifecycle_status == "active", "now": now, "anchor": _ANCHOR},
    )
    session.execute(
        text(
            """
            UPDATE documents
            SET current_version_id = :vid,
                import_status = 'chunked',
                lifecycle_status = CAST(:status AS varchar),
                archived_at = CASE WHEN CAST(:status AS varchar) = 'archived' THEN :now ELSE null END,
                deleted_at = CASE WHEN CAST(:status AS varchar) = 'deleted' THEN :now ELSE null END,
                updated_at = :now
            WHERE id = :did
            """
        ),
        {"vid": version_id, "did": doc_id, "status": lifecycle_status, "now": now},
    )
    return doc_id, version_id, chunk_id


def _seed_citation(
    session: Session,
    *,
    truth_ids: TruthIds,
    label: str,
    workspace_id: str,
    user_id: str,
    doc_id: str,
    chunk_id: str | None,
    quote_preview: str = _PREVIEW,
    source_status: str = "active",
) -> tuple[str, str, str]:
    session_id = truth_ids.chat_session_id(label)
    message_id = truth_ids.chat_message_id(label)
    citation_id = truth_ids.citation_id(label)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    session.execute(
        text(
            """
            INSERT INTO chat_sessions (id, workspace_id, owner_user_id, title, created_at, updated_at)
            VALUES (:id, CAST(:ws AS uuid), CAST(:user AS uuid), :title, :now, :now)
            """
        ),
        {"id": session_id, "ws": workspace_id, "user": user_id,
         "title": f"Session {label}", "now": now},
    )
    session.execute(
        text(
            """
            INSERT INTO chat_messages (
                id, session_id, message_index, role, content, basis_type, metadata, created_at
            ) VALUES (
                :id, :session_id, 0, 'assistant', :content, 'knowledge_base', '{}', :now
            )
            """
        ),
        {"id": message_id, "session_id": session_id,
         "content": "Answer referencing the document.", "now": now},
    )
    chunk_val = f"'{chunk_id}'" if chunk_id else "null"
    session.execute(
        text(
            f"""
            INSERT INTO chat_citations (
                id, message_id, chunk_id, document_id,
                document_title, quote_preview, source_anchor, source_status
            ) VALUES (
                :id, :msg_id, {chunk_val}, :doc_id,
                :title, :preview, cast(:anchor as jsonb), :status
            )
            """
        ),
        {"id": citation_id, "msg_id": message_id, "doc_id": doc_id,
         "title": f"Doc {label}", "preview": quote_preview,
         "anchor": _ANCHOR, "status": source_status},
    )
    return session_id, message_id, citation_id


# ── 1. Baseline: clean state → ok ────────────────────────────────────────────

def test_longevity_clean_state_ok(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = CitationLongevityAuditService.from_session(truth_session)
    report = svc.get_longevity_report(workspace_id=truth_seed["workspace_id"])

    assert report["severity"] == "ok"
    assert report["audit_name"] == "citation_longevity_audit"
    assert report["time_horizon"] == "simulated_long_term_cycles"
    assert "source_anchor_validity" in report["audit_scope"]
    assert "archive_restore_status_sync" in report["simulated_cycles"]
    assert report["total_citations"] == 0
    assert report["orphaned_anchor_count"] == 0
    assert report["status_drift_count"] == 0
    assert report["deleted_not_marked_count"] == 0
    assert report["restore_reference_risk_count"] == 0
    assert report["rechunk_reference_risk_count"] == 0
    assert report["persistence_risks"] == [
        "no persistence risk detected in simulated long-term citation cycles"
    ]


# ── 2. Lifecycle cycle: archive syncs citation status ────────────────────────

def test_longevity_archive_syncs_citation_status(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    doc_id, _, chunk_id = _seed_document(
        truth_session, truth_ids=truth_ids, label="archive-sync",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
    )
    _seed_citation(
        truth_session, truth_ids=truth_ids, label="archive-sync",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        doc_id=doc_id, chunk_id=chunk_id, source_status="active",
    )
    truth_session.commit()

    # Simulated long-term cycle: document is archived
    lifecycle = DocumentLifecycleService.from_session(truth_session)
    lifecycle.archive(doc_id, workspace_id=truth_seed["workspace_id"])

    svc = CitationLongevityAuditService.from_session(truth_session)
    report = svc.get_longevity_report(workspace_id=truth_seed["workspace_id"])

    assert report["status_drift_count"] == 0, "lifecycle.archive() must sync citation status"
    assert report["deleted_not_marked_count"] == 0
    assert report["total_citations"] == 1


# ── 3. Lifecycle cycle: delete syncs citation status ─────────────────────────

def test_longevity_delete_syncs_citation_status(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    doc_id, _, chunk_id = _seed_document(
        truth_session, truth_ids=truth_ids, label="delete-sync",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
    )
    _seed_citation(
        truth_session, truth_ids=truth_ids, label="delete-sync",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        doc_id=doc_id, chunk_id=chunk_id, source_status="active",
    )
    truth_session.commit()

    lifecycle = DocumentLifecycleService.from_session(truth_session)
    lifecycle.delete(doc_id, workspace_id=truth_seed["workspace_id"])

    svc = CitationLongevityAuditService.from_session(truth_session)
    report = svc.get_longevity_report(workspace_id=truth_seed["workspace_id"])

    assert report["deleted_not_marked_count"] == 0, "lifecycle.delete() must sync citation status"
    assert report["status_drift_count"] == 0


# ── 4. Lifecycle cycle: archive → restore syncs back to active ───────────────

def test_longevity_restore_syncs_citation_back_to_active(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    doc_id, _, chunk_id = _seed_document(
        truth_session, truth_ids=truth_ids, label="restore-sync",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
    )
    _seed_citation(
        truth_session, truth_ids=truth_ids, label="restore-sync",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        doc_id=doc_id, chunk_id=chunk_id, source_status="active",
    )
    truth_session.commit()

    lifecycle = DocumentLifecycleService.from_session(truth_session)
    lifecycle.archive(doc_id, workspace_id=truth_seed["workspace_id"])
    lifecycle.restore(doc_id, workspace_id=truth_seed["workspace_id"])

    svc = CitationLongevityAuditService.from_session(truth_session)
    report = svc.get_longevity_report(workspace_id=truth_seed["workspace_id"])

    assert report["restored_not_marked_count"] == 0, "lifecycle.restore() must sync citation back to active"
    assert report["status_drift_count"] == 0


# ── 5. Detects status drift (lifecycle sync missed) ───────────────────────────

def test_longevity_detects_status_drift(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    doc_id, _, chunk_id = _seed_document(
        truth_session, truth_ids=truth_ids, label="drift",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        lifecycle_status="archived",  # document is already archived
    )
    # Citation was left at 'active' — the sync was missed
    _seed_citation(
        truth_session, truth_ids=truth_ids, label="drift",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        doc_id=doc_id, chunk_id=chunk_id, source_status="active",
    )
    truth_session.commit()

    svc = CitationLongevityAuditService.from_session(truth_session)
    report = svc.get_longevity_report(workspace_id=truth_seed["workspace_id"])

    assert report["status_drift_count"] == 1
    assert report["severity"] in {"warning", "critical"}
    assert any("diverges" in a or "drift" in a.lower() or "lifecycle sync" in a.lower() for a in report["alerts"])


# ── 6. Detects deleted_not_marked ─────────────────────────────────────────────

def test_longevity_detects_deleted_not_marked(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    doc_id, _, chunk_id = _seed_document(
        truth_session, truth_ids=truth_ids, label="deleted-notmark",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        lifecycle_status="deleted",
    )
    _seed_citation(
        truth_session, truth_ids=truth_ids, label="deleted-notmark",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        doc_id=doc_id, chunk_id=chunk_id, source_status="active",
    )
    truth_session.commit()

    svc = CitationLongevityAuditService.from_session(truth_session)
    report = svc.get_longevity_report(workspace_id=truth_seed["workspace_id"])

    assert report["deleted_not_marked_count"] == 1
    assert report["severity"] == "critical"
    assert any("deleted" in a.lower() for a in report["alerts"])


# ── 7. Detects restored_not_marked ───────────────────────────────────────────

def test_longevity_detects_restored_not_marked(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    doc_id, _, chunk_id = _seed_document(
        truth_session, truth_ids=truth_ids, label="restored-notmark",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        lifecycle_status="active",
    )
    # Citation stuck in 'archived' even though document is active
    _seed_citation(
        truth_session, truth_ids=truth_ids, label="restored-notmark",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        doc_id=doc_id, chunk_id=chunk_id, source_status="archived",
    )
    truth_session.commit()

    svc = CitationLongevityAuditService.from_session(truth_session)
    report = svc.get_longevity_report(workspace_id=truth_seed["workspace_id"])

    assert report["restored_not_marked_count"] == 1
    assert report["severity"] in {"warning", "critical"}
    assert any("restored" in a.lower() or "re-activated" in a.lower() or "active" in a.lower() for a in report["alerts"])


# ── 8. Detects orphaned anchor after rechunking ───────────────────────────────

def test_longevity_detects_orphaned_anchor_after_rechunk(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    doc_id, _, chunk_id = _seed_document(
        truth_session, truth_ids=truth_ids, label="rechunk-orphan",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
    )
    _seed_citation(
        truth_session, truth_ids=truth_ids, label="rechunk-orphan",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        doc_id=doc_id, chunk_id=None,  # chunk_id already NULL = rechunk destroyed it
        source_status="active",        # source_status not updated = orphaned anchor
    )
    truth_session.commit()

    svc = CitationLongevityAuditService.from_session(truth_session)
    report = svc.get_longevity_report(workspace_id=truth_seed["workspace_id"])

    assert report["orphaned_anchor_count"] == 1
    assert report["anchor_unverifiable_count"] >= 1
    assert report["rechunk_reference_risk_count"] == 1
    assert report["restore_reference_risk_count"] >= 1
    assert report["severity"] in {"warning", "critical"}
    assert any("chunk_id" in a or "NULL" in a or "rechunking" in a.lower() for a in report["alerts"])
    assert any("rechunking can detach" in risk for risk in report["persistence_risks"])
    assert any("content_hash" in rec for rec in report["hardening_recommendations"])


# ── 9. Detects preview staleness after rechunking ────────────────────────────

def test_longevity_detects_preview_staleness(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    new_content = "Completely different content after rechunking. No overlap with original preview."
    doc_id, _, chunk_id = _seed_document(
        truth_session, truth_ids=truth_ids, label="stale-preview",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        content=new_content,
    )
    # Citation has the OLD preview that no longer matches the current chunk content
    _seed_citation(
        truth_session, truth_ids=truth_ids, label="stale-preview",
        workspace_id=truth_seed["workspace_id"], user_id=truth_seed["user_id"],
        doc_id=doc_id, chunk_id=chunk_id,
        quote_preview="Original content from before rechunking that no longer exists anywhere.",
        source_status="active",
    )
    truth_session.commit()

    svc = CitationLongevityAuditService.from_session(truth_session)
    report = svc.get_longevity_report(workspace_id=truth_seed["workspace_id"])

    assert report["preview_stale_count"] == 1
    assert report["rechunk_reference_risk_count"] == 1
    assert report["severity"] in {"warning", "critical"}
    assert any("quote_preview" in a or "stale" in a.lower() or "rechunking" in a.lower() for a in report["alerts"])
    assert any("quote preview" in risk for risk in report["persistence_risks"])
    assert any("Do not overwrite historical quote_preview" in rec for rec in report["hardening_recommendations"])


# ── 10. Workspace isolation ───────────────────────────────────────────────────

def test_longevity_workspace_isolation(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    # Seed a deleted-not-marked citation in OTHER workspace
    doc_id, _, chunk_id = _seed_document(
        truth_session, truth_ids=truth_ids, label="ws-isolation",
        workspace_id=truth_seed["other_workspace_id"],
        user_id=truth_seed["other_user_id"],
        lifecycle_status="deleted",
    )
    _seed_citation(
        truth_session, truth_ids=truth_ids, label="ws-isolation",
        workspace_id=truth_seed["other_workspace_id"],
        user_id=truth_seed["other_user_id"],
        doc_id=doc_id, chunk_id=chunk_id, source_status="active",
    )
    truth_session.commit()

    # Our workspace should see nothing
    svc = CitationLongevityAuditService.from_session(truth_session)
    report = svc.get_longevity_report(workspace_id=truth_seed["workspace_id"])

    assert report["total_citations"] == 0
    assert report["deleted_not_marked_count"] == 0
    assert report["severity"] == "ok"


# ── 11. API endpoint contract ─────────────────────────────────────────────────

def test_longevity_api_endpoint_contract(
    truth_client,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    response = truth_client.get("/api/v1/admin/citations/longevity")

    assert response.status_code == 200, f"unexpected: {response.text}"
    data = response.json()

    assert data["workspace_id"] == truth_seed["workspace_id"]
    assert data["severity"] in {"ok", "warning", "critical"}
    assert isinstance(data["total_citations"], int)
    assert data["audit_name"] == "citation_longevity_audit"
    assert data["time_horizon"] == "simulated_long_term_cycles"
    assert isinstance(data["audit_scope"], list)
    assert isinstance(data["simulated_cycles"], list)
    assert isinstance(data["orphaned_anchor_count"], int)
    assert isinstance(data["status_drift_count"], int)
    assert isinstance(data["preview_stale_count"], int)
    assert isinstance(data["deleted_not_marked_count"], int)
    assert isinstance(data["restored_not_marked_count"], int)
    assert isinstance(data["restore_reference_risk_count"], int)
    assert isinstance(data["rechunk_reference_risk_count"], int)
    assert isinstance(data["alerts"], list)
    assert isinstance(data["risk_summary"], list)
    assert isinstance(data["persistence_risks"], list)
    assert isinstance(data["hardening_recommendations"], list)
    assert len(data["hardening_recommendations"]) >= 1
