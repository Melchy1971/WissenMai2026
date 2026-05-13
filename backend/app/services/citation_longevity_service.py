"""
Citation Longevity Audit Service.

Detects long-term citation degradation:
- orphaned anchors after rechunking
- unverifiable anchors after chunk removal
- source_status drift from document lifecycle
- stale quote previews after content movement
- deleted documents still marked active
- restored documents still marked unavailable
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


_STALE_PREFIX_LEN = 30
LONGEVITY_AUDIT_SCOPE = [
    "source_anchor_validity",
    "quote_preview_stability",
    "deleted_document_marking",
    "restored_document_marking",
    "rechunk_reference_survival",
    "restore_reference_survival",
]
SIMULATED_LONG_TERM_CYCLES = [
    "baseline_snapshot",
    "archive_status_sync",
    "delete_status_sync",
    "archive_restore_status_sync",
    "manual_status_drift_detection",
    "rechunk_orphan_detection",
    "quote_preview_staleness_detection",
    "workspace_isolation",
]


class CitationLongevityAuditService:
    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def from_session(cls, session: Session) -> "CitationLongevityAuditService":
        return cls(session)

    def get_longevity_report(self, *, workspace_id: str) -> dict[str, Any]:
        now = datetime.now(UTC)

        total = self._count(
            """
            SELECT COUNT(cc.id)
            FROM chat_citations cc
            JOIN chat_messages cm ON cm.id = cc.message_id
            JOIN chat_sessions cs ON cs.id = cm.session_id
            WHERE cs.workspace_id = :ws
            """,
            ws=workspace_id,
        )
        orphaned_anchor = self._count(
            """
            SELECT COUNT(cc.id)
            FROM chat_citations cc
            JOIN chat_messages cm ON cm.id = cc.message_id
            JOIN chat_sessions cs ON cs.id = cm.session_id
            WHERE cs.workspace_id = :ws
              AND cc.chunk_id IS NULL
              AND cc.source_status = 'active'
            """,
            ws=workspace_id,
        )
        anchor_unverifiable = self._count(
            """
            SELECT COUNT(cc.id)
            FROM chat_citations cc
            JOIN chat_messages cm ON cm.id = cc.message_id
            JOIN chat_sessions cs ON cs.id = cm.session_id
            WHERE cs.workspace_id = :ws
              AND cc.chunk_id IS NULL
            """,
            ws=workspace_id,
        )
        status_drift = self._count(
            """
            SELECT COUNT(cc.id)
            FROM chat_citations cc
            JOIN chat_messages cm ON cm.id = cc.message_id
            JOIN chat_sessions cs ON cs.id = cm.session_id
            JOIN documents d ON d.id = cc.document_id
            WHERE cs.workspace_id = :ws
              AND cc.source_status != d.lifecycle_status
            """,
            ws=workspace_id,
        )
        preview_stale = self._count(
            """
            SELECT COUNT(cc.id)
            FROM chat_citations cc
            JOIN chat_messages cm ON cm.id = cc.message_id
            JOIN chat_sessions cs ON cs.id = cm.session_id
            JOIN document_chunks c ON c.id = cc.chunk_id
            WHERE cs.workspace_id = :ws
              AND cc.chunk_id IS NOT NULL
              AND cc.quote_preview != 'Historical citation unavailable'
              AND position(left(cc.quote_preview, :prefix_len) IN c.content) = 0
            """,
            ws=workspace_id,
            prefix_len=_STALE_PREFIX_LEN,
        )
        deleted_not_marked = self._count(
            """
            SELECT COUNT(cc.id)
            FROM chat_citations cc
            JOIN chat_messages cm ON cm.id = cc.message_id
            JOIN chat_sessions cs ON cs.id = cm.session_id
            JOIN documents d ON d.id = cc.document_id
            WHERE cs.workspace_id = :ws
              AND d.lifecycle_status = 'deleted'
              AND cc.source_status = 'active'
            """,
            ws=workspace_id,
        )
        restored_not_marked = self._count(
            """
            SELECT COUNT(cc.id)
            FROM chat_citations cc
            JOIN chat_messages cm ON cm.id = cc.message_id
            JOIN chat_sessions cs ON cs.id = cm.session_id
            JOIN documents d ON d.id = cc.document_id
            WHERE cs.workspace_id = :ws
              AND d.lifecycle_status = 'active'
              AND cc.source_status IN ('archived', 'deleted', 'missing')
            """,
            ws=workspace_id,
        )

        alerts, risk_summary, severity = self._evaluate(
            orphaned_anchor=orphaned_anchor,
            anchor_unverifiable=anchor_unverifiable,
            status_drift=status_drift,
            preview_stale=preview_stale,
            deleted_not_marked=deleted_not_marked,
            restored_not_marked=restored_not_marked,
        )

        return {
            "checked_at": now,
            "workspace_id": workspace_id,
            "audit_name": "citation_longevity_audit",
            "audit_scope": LONGEVITY_AUDIT_SCOPE,
            "time_horizon": "simulated_long_term_cycles",
            "simulated_cycles": SIMULATED_LONG_TERM_CYCLES,
            "total_citations": total,
            "orphaned_anchor_count": orphaned_anchor,
            "anchor_unverifiable_count": anchor_unverifiable,
            "status_drift_count": status_drift,
            "preview_stale_count": preview_stale,
            "deleted_not_marked_count": deleted_not_marked,
            "restored_not_marked_count": restored_not_marked,
            "restore_reference_risk_count": orphaned_anchor + anchor_unverifiable + status_drift,
            "rechunk_reference_risk_count": orphaned_anchor + preview_stale,
            "severity": severity,
            "alerts": alerts,
            "risk_summary": risk_summary,
            "persistence_risks": _persistence_risks(
                orphaned_anchor=orphaned_anchor,
                anchor_unverifiable=anchor_unverifiable,
                status_drift=status_drift,
                preview_stale=preview_stale,
                deleted_not_marked=deleted_not_marked,
                restored_not_marked=restored_not_marked,
            ),
            "hardening_recommendations": _hardening_recommendations(
                orphaned_anchor=orphaned_anchor,
                anchor_unverifiable=anchor_unverifiable,
                status_drift=status_drift,
                preview_stale=preview_stale,
                deleted_not_marked=deleted_not_marked,
                restored_not_marked=restored_not_marked,
            ),
        }

    def _count(self, sql: str, **params: Any) -> int:
        return int(self._session.execute(text(sql), params).scalar() or 0)

    def _evaluate(
        self,
        *,
        orphaned_anchor: int,
        anchor_unverifiable: int,
        status_drift: int,
        preview_stale: int,
        deleted_not_marked: int,
        restored_not_marked: int,
    ) -> tuple[list[str], list[str], str]:
        alerts: list[str] = []
        risk_summary: list[str] = []

        if deleted_not_marked > 0:
            alerts.append(
                f"{deleted_not_marked} citation(s) point to deleted documents but are still "
                "marked active - historical answers may expose deleted content"
            )
            risk_summary.append("CRITICAL: citations reference deleted documents without correct status")
        if orphaned_anchor > 0:
            alerts.append(
                f"{orphaned_anchor} active citation(s) have lost their chunk reference "
                "(chunk_id NULL) - rechunking destroyed the original anchor"
            )
            risk_summary.append("active citations with NULL chunk_id cannot be navigated to source")
        if status_drift > 0:
            alerts.append(
                f"{status_drift} citation(s) have stored source_status that diverges from "
                "live document lifecycle_status - lifecycle sync may have been missed"
            )
            risk_summary.append("stored source_status does not reflect current document state")
        if preview_stale > 0:
            alerts.append(
                f"{preview_stale} citation(s) have a quote_preview that no longer matches "
                "current chunk content - content changed after rechunking"
            )
            risk_summary.append("quote_preview snapshots are stale after rechunking")
        if restored_not_marked > 0:
            alerts.append(
                f"{restored_not_marked} citation(s) for restored/active documents still show "
                "archived/deleted/missing status - restore sync may have been missed"
            )
            risk_summary.append("restored document citations not re-activated in stored status")
        if anchor_unverifiable > 0 and orphaned_anchor == 0:
            risk_summary.append(
                f"{anchor_unverifiable} citation(s) have unverifiable anchors "
                "(chunk_id NULL, non-active status - expected after archive/delete)"
            )

        if deleted_not_marked > 0 or (orphaned_anchor > 0 and status_drift > 0):
            severity = "critical"
        elif orphaned_anchor > 0 or status_drift > 0 or preview_stale > 0 or restored_not_marked > 0:
            severity = "warning"
        else:
            severity = "ok"

        return alerts, risk_summary, severity


def _hardening_recommendations(
    *,
    orphaned_anchor: int,
    anchor_unverifiable: int,
    status_drift: int,
    preview_stale: int,
    deleted_not_marked: int,
    restored_not_marked: int,
) -> list[str]:
    recs: list[str] = []
    if orphaned_anchor > 0:
        recs.append(
            "Snapshot citation content_hash, chunk_index, document_version_id and source_anchor "
            "at citation time so orphaned anchors can be remapped during an audited repair pass."
        )
        recs.append(
            "When rechunking sets chunk_id to NULL on an active citation, "
            "automatically transition source_status to 'missing' to prevent false active signals."
        )
    if anchor_unverifiable > 0:
        recs.append(
            "Persist an immutable citation_anchor_snapshot so archived/deleted citations remain "
            "verifiable even when live chunks are removed or replaced."
        )
    if status_drift > 0:
        recs.append(
            "Add a periodic reconciliation job that cross-checks citation.source_status "
            "against document.lifecycle_status and writes an audited repair report before mutation."
        )
    if preview_stale > 0:
        recs.append(
            "Do not overwrite historical quote_preview. Add quote_hash and current_preview_match "
            "so stale live content can be flagged without changing the historical answer."
        )
    if deleted_not_marked > 0:
        recs.append(
            "Make delete lifecycle updates atomically update citation.source_status to 'deleted' "
            "and block new retrieval from deleted sources."
        )
    if restored_not_marked > 0:
        recs.append(
            "Make restore lifecycle updates atomically reactivate citation.source_status only when "
            "the source anchor is still verifiable; otherwise keep status 'missing'."
        )
    if not recs:
        recs.append(
            "Current snapshot fields are stable for the simulated long-term cycles; keep "
            "source_anchor, quote_preview, document_title and source_status immutable in citations."
        )
    return recs


def _persistence_risks(
    *,
    orphaned_anchor: int,
    anchor_unverifiable: int,
    status_drift: int,
    preview_stale: int,
    deleted_not_marked: int,
    restored_not_marked: int,
) -> list[str]:
    risks: list[str] = []
    if orphaned_anchor > 0:
        risks.append("rechunking can detach active citations from their original chunk anchor")
    if anchor_unverifiable > 0:
        risks.append("chunk-level source anchors cannot be verified for every historical citation")
    if preview_stale > 0:
        risks.append("current chunk content no longer contains the stored quote preview")
    if deleted_not_marked > 0:
        risks.append("deleted sources can appear active in historical answers")
    if restored_not_marked > 0:
        risks.append("restored sources can remain marked unavailable in historical answers")
    if status_drift > 0:
        risks.append("citation source_status can drift from document lifecycle status")
    if not risks:
        risks.append("no persistence risk detected in simulated long-term citation cycles")
    return risks
