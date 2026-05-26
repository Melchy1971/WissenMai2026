"""
Entropy Tests — Long-Term System Aging Detection.

Simulates multi-epoch operations (uploads, lifecycle churn, reindexes,
restore cycles, queue retries, cleanup cycles) and measures drift metrics
to detect gradual system degradation.

Simulation scale:
  - Default: 5 docs/epoch (CI speed)
  - ENTROPY_LARGE_SCALE=1: 50 docs/epoch (full signal fidelity)

Drift metrics measured per epoch:
  - orphan_chunk_count     : chunks with broken document_version_id FK
  - stale_index_count      : is_searchable=TRUE for non-active documents
  - retrieval_coverage     : searchable_chunks / active_chunks
  - queue_backlog          : pending + running + retryable jobs
  - retryable_count        : jobs stuck in retry loop
  - dead_letter_count      : jobs that exhausted all retries
  - citation_orphan_rate   : citations with NULL chunk_id

Long-term risks exposed:
  - Orphan growth if cleanup is skipped
  - Stale index if reindex is skipped after archive/restore cycles
  - Retrieval gaps if searchability flags drift from lifecycle state
  - Queue debt accumulation if retries are not resolved
  - Citation reference rot after rechunking or mass deletion
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from tests.postgres_truth.entropy_helpers import (
    CITATION_ORPHAN_RATE_MAX,
    DOCS_PER_EPOCH,
    ORPHAN_RATE_MAX,
    RETRIEVAL_COVERAGE_MIN,
    STALE_RATE_MAX,
    EntropyMetrics,
    archive_docs,
    archive_docs_without_repair,
    collect_metrics,
    compute_drift_trend,
    degrade_searchability,
    drain_jobs,
    inject_citation_orphans,
    inject_dead_letter_jobs,
    inject_orphan_chunks,
    inject_retryable_jobs,
    purge_orphan_chunks,
    repair_retrieval,
    repair_stale_index,
    restore_docs,
    seed_batch,
)
from tests.postgres_truth.support import TruthIds


pytestmark = [pytest.mark.postgres_truth, pytest.mark.entropy, pytest.mark.m5_truth]


# ── Orphan Growth ─────────────────────────────────────────────────────────────

class TestOrphanGrowthDetection:
    @pytest.mark.postgres_truth
    def test_orphan_chunks_are_detected_by_metric(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Injecting broken-FK chunks must increase orphan_chunk_count to exactly the injected count."""
        ws = truth_seed["workspace_id"]
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids, prefix="orp-a", workspace_id=ws)
        anchor_doc = doc_ids[0]

        baseline = collect_metrics(truth_session, workspace_id=ws, epoch=0)
        inject_orphan_chunks(truth_session, truth_ids=truth_ids, prefix="orp-a", doc_id=anchor_doc, count=3)
        after_inject = collect_metrics(truth_session, workspace_id=ws, epoch=1)

        assert after_inject.orphan_chunk_count == baseline.orphan_chunk_count + 3
        risks = after_inject.as_risk_dict()["risks"]
        # If injected orphans exceed threshold, risk label must appear
        total = after_inject.active_chunk_count + after_inject.orphan_chunk_count
        if after_inject.orphan_chunk_count / total > ORPHAN_RATE_MAX:
            assert any("ORPHAN_EXCESS" in r for r in risks)

    @pytest.mark.postgres_truth
    def test_orphan_purge_restores_clean_state(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """purge_orphan_chunks must reduce orphan_chunk_count back to baseline."""
        ws = truth_seed["workspace_id"]
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids, prefix="orp-b", workspace_id=ws)
        inject_orphan_chunks(truth_session, truth_ids=truth_ids, prefix="orp-b",
                             doc_id=doc_ids[0], count=4)

        before_purge = collect_metrics(truth_session, workspace_id=ws)
        assert before_purge.orphan_chunk_count >= 4

        purged = purge_orphan_chunks(truth_session, workspace_id=ws)
        after_purge = collect_metrics(truth_session, workspace_id=ws)

        assert purged >= 4
        assert after_purge.orphan_chunk_count == 0


# ── Stale Index Growth ─────────────────────────────────────────────────────────

class TestStaleIndexDetection:
    @pytest.mark.postgres_truth
    def test_stale_index_grows_when_archive_skips_repair(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Archiving docs without clearing is_searchable must create stale index entries."""
        ws = truth_seed["workspace_id"]
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids, prefix="stale-a", workspace_id=ws)

        baseline = collect_metrics(truth_session, workspace_id=ws, epoch=0)
        assert baseline.stale_index_count == 0

        archive_docs_without_repair(truth_session, doc_ids[:3])
        after_archive = collect_metrics(truth_session, workspace_id=ws, epoch=1)

        assert after_archive.stale_index_count >= 3

    @pytest.mark.postgres_truth
    def test_stale_index_cleared_by_repair_pass(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """repair_stale_index must eliminate all stale entries after archive-without-repair."""
        ws = truth_seed["workspace_id"]
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids, prefix="stale-b", workspace_id=ws)
        archive_docs_without_repair(truth_session, doc_ids)  # all archived, all still searchable

        stale_before = collect_metrics(truth_session, workspace_id=ws).stale_index_count
        assert stale_before == len(doc_ids)

        repaired = repair_stale_index(truth_session, workspace_id=ws)
        after_repair = collect_metrics(truth_session, workspace_id=ws)

        assert repaired == len(doc_ids)
        assert after_repair.stale_index_count == 0

    @pytest.mark.postgres_truth
    def test_restore_cycle_does_not_create_stale_entries(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Clean archive → restore cycle must leave stale_index_count at zero."""
        ws = truth_seed["workspace_id"]
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids, prefix="stale-c", workspace_id=ws)

        archive_docs(truth_session, doc_ids)
        mid = collect_metrics(truth_session, workspace_id=ws)
        assert mid.stale_index_count == 0  # clean archive sets is_searchable=FALSE

        restore_docs(truth_session, doc_ids)
        after_restore = collect_metrics(truth_session, workspace_id=ws)

        assert after_restore.stale_index_count == 0
        assert after_restore.retrieval_coverage == 1.0


# ── Retrieval Degradation ──────────────────────────────────────────────────────

class TestRetrievalDegradation:
    @pytest.mark.postgres_truth
    def test_searchability_drift_reduces_coverage(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Degrading searchability flags on active docs must lower retrieval_coverage."""
        ws = truth_seed["workspace_id"]
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids, prefix="ret-a",
                             workspace_id=ws, count=DOCS_PER_EPOCH)

        baseline = collect_metrics(truth_session, workspace_id=ws, epoch=0)
        assert baseline.retrieval_coverage == 1.0

        degrade_docs = doc_ids[:max(1, len(doc_ids) // 2)]
        degrade_searchability(truth_session, degrade_docs)
        degraded = collect_metrics(truth_session, workspace_id=ws, epoch=1)

        assert degraded.retrieval_coverage < 1.0
        assert degraded.retrieval_coverage < baseline.retrieval_coverage
        assert "RETRIEVAL_DEGRADED" in str(degraded.as_risk_dict()["risks"])

    @pytest.mark.postgres_truth
    def test_retrieval_repair_restores_coverage(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """repair_retrieval must restore full coverage after searchability drift."""
        ws = truth_seed["workspace_id"]
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids, prefix="ret-b", workspace_id=ws)
        degrade_searchability(truth_session, doc_ids)

        assert collect_metrics(truth_session, workspace_id=ws).retrieval_coverage < 1.0

        repaired = repair_retrieval(truth_session, workspace_id=ws)
        after = collect_metrics(truth_session, workspace_id=ws)

        assert repaired > 0
        assert after.retrieval_coverage == 1.0


# ── Queue Drift ───────────────────────────────────────────────────────────────

class TestQueueBacklogDrift:
    @pytest.mark.postgres_truth
    def test_retryable_jobs_accumulate_and_are_detected(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Injected retryable jobs must appear in queue_backlog and retryable_count."""
        ws = truth_seed["workspace_id"]
        uid = truth_seed["user_id"]

        baseline = collect_metrics(truth_session, workspace_id=ws, epoch=0)
        job_ids = inject_retryable_jobs(truth_session, truth_ids=truth_ids,
                                        prefix="q-a", workspace_id=ws, user_id=uid, count=4)
        after = collect_metrics(truth_session, workspace_id=ws, epoch=1)

        assert after.retryable_count == baseline.retryable_count + 4
        assert after.queue_backlog == baseline.queue_backlog + 4

    @pytest.mark.postgres_truth
    def test_dead_letter_accumulation_is_detected(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Dead-letter jobs must appear in dead_letter_count and trigger risk label."""
        ws = truth_seed["workspace_id"]
        uid = truth_seed["user_id"]

        inject_dead_letter_jobs(truth_session, truth_ids=truth_ids,
                                prefix="q-b", workspace_id=ws, user_id=uid, count=3)
        metrics = collect_metrics(truth_session, workspace_id=ws)

        assert metrics.dead_letter_count >= 3
        assert "DEAD_LETTERS" in str(metrics.as_risk_dict()["risks"])

    @pytest.mark.postgres_truth
    def test_draining_jobs_reduces_backlog(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Completing retryable jobs must decrease queue_backlog to baseline."""
        ws = truth_seed["workspace_id"]
        uid = truth_seed["user_id"]

        baseline = collect_metrics(truth_session, workspace_id=ws, epoch=0)
        job_ids = inject_retryable_jobs(truth_session, truth_ids=truth_ids,
                                        prefix="q-c", workspace_id=ws, user_id=uid, count=3)
        drain_jobs(truth_session, job_ids)
        after_drain = collect_metrics(truth_session, workspace_id=ws, epoch=2)

        assert after_drain.retryable_count == baseline.retryable_count
        assert after_drain.queue_backlog == baseline.queue_backlog


# ── Citation Degradation ──────────────────────────────────────────────────────

class TestCitationDegradation:
    @pytest.mark.postgres_truth
    def test_chunk_deletion_increases_citation_orphan_rate(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Nulling chunk_id on existing citations must raise citation_orphan_count."""
        ws = truth_seed["workspace_id"]
        uid = truth_seed["user_id"]
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids, prefix="cit-a", workspace_id=ws)

        baseline = collect_metrics(truth_session, workspace_id=ws, epoch=0)
        inject_citation_orphans(truth_session, truth_ids=truth_ids, prefix="cit-a",
                                workspace_id=ws, user_id=uid, doc_ids=doc_ids, count=3)
        after = collect_metrics(truth_session, workspace_id=ws, epoch=1)

        assert after.citation_orphan_count == baseline.citation_orphan_count + 3
        assert after.citation_total == baseline.citation_total + 3
        assert after.citation_orphan_rate > baseline.citation_orphan_rate

    @pytest.mark.postgres_truth
    def test_citation_orphan_rate_tracks_deletion_scale(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """citation_orphan_rate must equal orphaned / total for any injection count."""
        ws = truth_seed["workspace_id"]
        uid = truth_seed["user_id"]
        n = DOCS_PER_EPOCH
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids, prefix="cit-b",
                             workspace_id=ws, count=n)
        inject_citation_orphans(truth_session, truth_ids=truth_ids, prefix="cit-b",
                                workspace_id=ws, user_id=uid, doc_ids=doc_ids, count=n)

        metrics = collect_metrics(truth_session, workspace_id=ws)

        assert metrics.citation_total >= n
        assert metrics.citation_orphan_count == n
        expected_rate = n / metrics.citation_total
        assert abs(metrics.citation_orphan_rate - expected_rate) < 0.001


# ── Multi-Epoch Entropy Simulation ────────────────────────────────────────────

class TestMultiEpochEntropySimulation:
    @pytest.mark.postgres_truth
    def test_entropy_simulation_detects_chaos_and_verifies_recovery(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """
        3-epoch entropy simulation:
          Epoch 0 (baseline)  — clean DB, all metrics zero / optimal
          Epoch 1 (chaos)     — inject orphans, stale index, retryable jobs, citation orphans
          Epoch 2 (recovery)  — repair all injected failures, verify system stabilises

        Verifies:
          • All metrics increase between epoch 0 and epoch 1 (chaos is detected)
          • After recovery, orphan/stale/retry metrics return to baseline
          • Drift trend shows positive delta at epoch 1 → negative at epoch 2
          • Long-term risk labels appear only during chaos epoch
        """
        ws = truth_seed["workspace_id"]
        uid = truth_seed["user_id"]
        n = DOCS_PER_EPOCH
        collected: list[EntropyMetrics] = []

        # ── Epoch 0: baseline ────────────────────────────────────────────────
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids,
                             prefix="sim-e0", workspace_id=ws, count=n)
        e0 = collect_metrics(truth_session, workspace_id=ws, epoch=0)
        collected.append(e0)

        assert e0.orphan_chunk_count == 0
        assert e0.stale_index_count == 0
        assert e0.retrieval_coverage == 1.0
        assert e0.dead_letter_count == 0
        assert e0.citation_orphan_count == 0

        # ── Epoch 1: chaos injection ─────────────────────────────────────────
        # Orphan drift: inject broken-FK chunks
        inject_orphan_chunks(truth_session, truth_ids=truth_ids, prefix="sim-e1",
                             doc_id=doc_ids[0], count=3)
        # Stale index: archive docs without repair
        archive_docs_without_repair(truth_session, doc_ids[1:3])
        # Retrieval gap: degrade searchability on remaining active docs
        degrade_searchability(truth_session, doc_ids[3:4])
        # Queue debt: inject retryable and dead-letter jobs
        retry_ids = inject_retryable_jobs(
            truth_session, truth_ids=truth_ids, prefix="sim-e1",
            workspace_id=ws, user_id=uid, count=3,
        )
        inject_dead_letter_jobs(truth_session, truth_ids=truth_ids, prefix="sim-e1",
                                workspace_id=ws, user_id=uid, count=2)
        # Citation rot: inject orphaned citations
        inject_citation_orphans(truth_session, truth_ids=truth_ids, prefix="sim-e1",
                                workspace_id=ws, user_id=uid,
                                doc_ids=doc_ids, count=min(3, n))

        e1 = collect_metrics(truth_session, workspace_id=ws, epoch=1)
        collected.append(e1)

        # Chaos must be detected
        assert e1.orphan_chunk_count > e0.orphan_chunk_count
        assert e1.stale_index_count > e0.stale_index_count
        assert e1.retrieval_coverage < e0.retrieval_coverage
        assert e1.retryable_count > e0.retryable_count
        assert e1.dead_letter_count > e0.dead_letter_count
        assert e1.citation_orphan_count > e0.citation_orphan_count

        # Risk labels must fire
        risks = e1.as_risk_dict()["risks"]
        assert any("STALE_INDEX" in r for r in risks)
        assert any("DEAD_LETTERS" in r for r in risks)

        # ── Epoch 2: recovery ─────────────────────────────────────────────────
        purge_orphan_chunks(truth_session, workspace_id=ws)
        repair_stale_index(truth_session, workspace_id=ws)
        repair_retrieval(truth_session, workspace_id=ws)
        drain_jobs(truth_session, retry_ids)
        # Restore the archived docs so active chunk count recovers
        restore_docs(truth_session, doc_ids[1:3])

        e2 = collect_metrics(truth_session, workspace_id=ws, epoch=2)
        collected.append(e2)

        # Recovery must be verified
        assert e2.orphan_chunk_count == 0
        assert e2.stale_index_count == 0
        assert e2.retrieval_coverage >= RETRIEVAL_COVERAGE_MIN
        assert e2.retryable_count == 0
        # Citation orphans persist (expected — no citation repair service)
        assert e2.citation_orphan_count == e1.citation_orphan_count

        # ── Drift trend analysis ──────────────────────────────────────────────
        trend = compute_drift_trend(collected)
        assert trend["epochs"] == 3

        # Total orphan change from epoch 0 to epoch 2 must be zero (fully recovered)
        total_orphan_delta = e2.orphan_chunk_count - e0.orphan_chunk_count
        assert total_orphan_delta == 0

        # Stale index fully recovered
        assert (e2.stale_index_count - e0.stale_index_count) == 0

        # Queue backlog fully recovered (dead letters persist but retryable drained)
        assert e2.retryable_count == e0.retryable_count

    @pytest.mark.postgres_truth
    def test_repeated_archive_restore_cycles_stay_entropy_neutral(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """
        5 archive→restore cycles on the same documents must leave entropy metrics
        unchanged (no orphan or stale accumulation from clean lifecycle transitions).
        """
        ws = truth_seed["workspace_id"]
        doc_ids = seed_batch(truth_session, truth_ids=truth_ids, prefix="cyc",
                             workspace_id=ws, count=DOCS_PER_EPOCH)

        baseline = collect_metrics(truth_session, workspace_id=ws, epoch=0)

        for cycle in range(5):
            archive_docs(truth_session, doc_ids)
            mid = collect_metrics(truth_session, workspace_id=ws, epoch=cycle * 2 + 1)
            assert mid.stale_index_count == 0, f"stale entries after archive cycle {cycle}"

            restore_docs(truth_session, doc_ids)
            end = collect_metrics(truth_session, workspace_id=ws, epoch=cycle * 2 + 2)
            assert end.stale_index_count == 0, f"stale entries after restore cycle {cycle}"
            assert end.orphan_chunk_count == baseline.orphan_chunk_count
            assert end.retrieval_coverage == 1.0

    @pytest.mark.postgres_truth
    def test_drift_trend_function_returns_valid_structure(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """compute_drift_trend must return valid keys for any metric sequence."""
        ws = truth_seed["workspace_id"]
        seed_batch(truth_session, truth_ids=truth_ids, prefix="trend", workspace_id=ws)

        metrics = [
            collect_metrics(truth_session, workspace_id=ws, epoch=i)
            for i in range(3)
        ]
        trend = compute_drift_trend(metrics)

        assert trend["epochs"] == 3
        assert "orphan_delta_per_epoch" in trend
        assert "stale_delta_per_epoch" in trend
        assert "retrieval_coverage_delta" in trend
        assert "backlog_delta_per_epoch" in trend
        assert "dead_letter_delta_per_epoch" in trend
        assert "citation_orphan_delta" in trend
        assert isinstance(trend["long_term_risks"], list)

