"""
Citation Longevity Audit Service.

Detects six categories of long-term citation degradation:

  1. orphaned_anchor   — chunk_id IS NULL while source_status='active'
                         (rechunking destroyed the chunk reference)
  2. anchor_unverifiable — chunk_id IS NULL (any status), anchor can't be confirmed
  3. status_drift      — stored source_status != live document.lifecycle_status
                         (lifecycle sync was missed)
  4. preview_stale     — chunk exists but quote_preview no longer matches chunk content
                         (content changed after rechunking)
  5. deleted_not_marked — document deleted but citation still shows active
  6. restored_not_marked — document restored/active but citation still shows archived/deleted

Workspace scoping: all queries join chat_citations → chat_messages → chat_sessions.workspace_id.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


# First N chars of quote_preview used for staleness fingerprint
_STALE_PREFIX_LEN = 30


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
              AND position(
                left(cc.quote_preview, :prefix_len) IN c.content
              ) = 0
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
            total=total,
        )

        return {
            "checked_at": now,
            "workspace_id": workspace_id,
            "total_citations": total,
            "orphaned_anchor_count": orphaned_anchor,
            "anchor_unverifiable_count": anchor_unverifiable,
            "status_drift_count": status_drift,
            "preview_stale_count": preview_stale,
            "deleted_not_marked_count": deleted_not_marked,
            "restored_not_marked_count": restored_not_marked,
            "severity": severity,
            "alerts": alerts,
            "risk_summary": risk_summary,
            "hardening_recommendations": _hardening_recommendations(
                orphaned_anchor=orphaned_anchor,
                status_drift=status_drift,
                preview_stale=preview_stale,
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
        total: int,
    ) -> tuple[list[str], list[str], str]:
        alerts: list[str] = []
        risk_summary: list[str] = []

        if deleted_not_marked > 0:
            alerts.append(
                f"{deleted_not_marked} citation(s) point to deleted documents but are still "
                f"marked active — historical answers may expose deleted content"
            )
            risk_summary.append("CRITICAL: citations reference deleted documents without correct status")

        if orphaned_anchor > 0:
            alerts.append(
                f"{orphaned_anchor} active citation(s) have lost their chunk reference "
                f"(chunk_id NULL) — rechunking destroyed the original anchor"
            )
            risk_summary.append("active citations with NULL chunk_id cannot be navigated to source")

        if status_drift > 0:
            alerts.append(
                f"{status_drift} citation(s) have stored source_status that diverges from "
                f"live document lifecycle_status — lifecycle sync may have been missed"
            )
            risk_summary.append("stored source_status does not reflect current document state")

        if preview_stale > 0:
            alerts.append(
                f"{preview_stale} citation(s) have a quote_preview that no longer matches "
                f"current chunk content — content changed after rechunking"
            )
            risk_summary.append("quote_preview snapshots are stale after rechunking")

        if restored_not_marked > 0:
            alerts.append(
                f"{restored_not_marked} citation(s) for restored/active documents still show "
                f"archived/deleted/missing status — restore sync may have been missed"
            )
            risk_summary.append("restored document citations not re-activated in stored status")

        if anchor_unverifiable > 0 and orphaned_anchor == 0:
            risk_summary.append(
                f"{anchor_unverifiable} citation(s) have unverifiable anchors "
                f"(chunk_id NULL, non-active status — expected after archive/delete)"
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
    status_drift: int,
    preview_stale: int,
) -> list[str]:
    recs: list[str] = []
    if orphaned_anchor > 0:
        recs.append(
            "Store content_hash at citation time so orphaned anchors can be remapped "
            "to rechunked content during a repair pass."
        )
        recs.append(
            "When rechunking sets chunk_id to NULL on an active citation, "
            "automatically transition source_status to 'missing' to prevent false active signals."
        )
    if status_drift > 0:
        recs.append(
            "Add a periodic reconciliation job that cross-checks citation.source_status "
            "against document.lifecycle_status and repairs drift silently."
        )
    if preview_stale > 0:
        recs.append(
            "Re-generate quote_preview from current chunk content after every rechunking pass "
            "where the chunk_id is preserved but content changes."
        )
    if not recs:
        recs.append("No hardening actions required — citation snapshots are stable.")
    return recs
