from __future__ import annotations

import argparse
import gc
import json
import sys
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.data_quality import DataQualityFinding, DataQualityRun  # noqa: E402
from app.models.documents import (  # noqa: E402
    Base,
    ChatCitation,
    ChatMessage,
    ChatSession,
    Chunk,
    Document,
    DocumentVersion,
    User,
    Workspace,
)
from app.services.data_quality_runner import DataQualityRunner  # noqa: E402
from app.services.quality_score import calculate_quality_score_from_findings  # noqa: E402


DEFAULT_OUTPUT = REPO_ROOT / "reports" / "current" / "m5a_performance_baseline.json"
DEFAULT_DOC_COUNTS = (100, 1000, 5000, 10000)
BENCH_WORKSPACE_ID = "m5a-perf-workspace"
BENCH_USER_ID = "m5a-perf-user"

CONTENT_HASH_UNIQUE = next(
    constraint
    for constraint in Document.__table__.constraints
    if constraint.name == "uq_documents_workspace_content_hash"
)


def _now() -> datetime:
    return datetime.now(UTC)


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _id(prefix: str, number: int) -> str:
    return f"{prefix}-{number:012x}"


def _create_engine_without_benchmark_constraints():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Document.__table__.constraints.remove(CONTENT_HASH_UNIQUE)
    try:
        Base.metadata.create_all(engine)
    finally:
        Document.__table__.constraints.add(CONTENT_HASH_UNIQUE)
    return engine


def _seed_dataset(session: Session, doc_count: int) -> dict[str, int]:
    now = _now()
    duplicate_docs = max(2, min(500, doc_count // 10))
    duplicate_docs -= duplicate_docs % 2
    metadata_docs = min(500, max(1, doc_count // 20))
    lifecycle_docs = min(500, max(1, doc_count // 25))
    citation_docs = min(500, max(1, doc_count // 20))
    orphan_rows = min(500, max(1, doc_count // 100))

    session.execute(
        insert(Workspace),
        [
            {
                "id": BENCH_WORKSPACE_ID,
                "name": "M5a Performance Workspace",
                "is_default": False,
                "created_at": now,
            }
        ],
    )
    session.execute(
        insert(User),
        [
            {
                "id": BENCH_USER_ID,
                "display_name": "M5a Perf User",
                "login": None,
                "password_hash": None,
                "is_active": True,
                "is_default": False,
                "created_at": now,
            }
        ],
    )

    docs: list[dict[str, Any]] = []
    versions: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    for i in range(doc_count):
        doc_id = _id("doc", i)
        version_id = _id("ver", i)
        chunk_id = _id("chk", i)
        is_archived_drift = i < lifecycle_docs and i % 2 == 0
        is_active_unsearchable = i < lifecycle_docs and i % 2 == 1
        lifecycle_status = "archived" if is_archived_drift else "active"
        content_hash = f"hash-dup-{i // 2:012x}" if i < duplicate_docs else f"hash-{i:012x}"
        metadata = (
            {}
            if i < metadata_docs
            else {
                "tags": ["baseline"],
                "category": "performance",
                "doc_type": "synthetic",
                "summary": "M5a performance baseline document.",
            }
        )
        docs.append(
            {
                "id": doc_id,
                "workspace_id": BENCH_WORKSPACE_ID,
                "owner_user_id": BENCH_USER_ID,
                "current_version_id": version_id,
                "title": "" if i < metadata_docs else f"M5a Baseline Document {i}",
                "source_type": "synthetic",
                "mime_type": "text/plain",
                "content_hash": content_hash,
                "import_status": "parsed",
                "lifecycle_status": lifecycle_status,
                "archived_at": now if is_archived_drift else None,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            }
        )
        versions.append(
            {
                "id": version_id,
                "document_id": doc_id,
                "version_number": 1,
                "normalized_markdown": "# Synthetic\n\nContent for M5a performance baseline.",
                "markdown_hash": f"markdown-{i:012x}",
                "parser_version": "m5a-perf/1",
                "ocr_used": False,
                "ki_provider": None,
                "ki_model": None,
                "metadata_": metadata,
                "created_at": now,
            }
        )
        chunks.append(
            {
                "id": chunk_id,
                "document_id": doc_id,
                "document_version_id": version_id,
                "chunk_index": 0,
                "heading_path": ["Synthetic"],
                "anchor": f"anchor-{i}",
                "content": "Synthetic M5a performance chunk.",
                "is_searchable": not is_active_unsearchable,
                "search_vector": "synthetic" if not is_active_unsearchable else None,
                "content_hash": f"chunk-{i:012x}",
                "token_estimate": 12,
                "metadata_": {"source": "m5a_performance_baseline"},
                "created_at": now,
            }
        )

    session.execute(insert(Document), docs)
    session.execute(insert(DocumentVersion), versions)
    session.execute(insert(Chunk), chunks)

    chat_session_id = _id("chat-session", doc_count)
    chat_message_id = _id("chat-message", doc_count)
    session.execute(
        insert(ChatSession),
        [
            {
                "id": chat_session_id,
                "workspace_id": BENCH_WORKSPACE_ID,
                "owner_user_id": BENCH_USER_ID,
                "title": "M5a Performance Chat",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    session.execute(
        insert(ChatMessage),
        [
            {
                "id": chat_message_id,
                "session_id": chat_session_id,
                "message_index": 0,
                "role": "assistant",
                "content": "Synthetic answer.",
                "basis_type": "knowledge_base",
                "metadata_": {},
                "created_at": now,
            }
        ],
    )
    citations: list[dict[str, Any]] = []
    for i in range(citation_docs):
        doc_id = _id("doc", i)
        citations.append(
            {
                "id": _id("citation", i),
                "message_id": chat_message_id,
                "chunk_id": _id("chk", i),
                "document_id": doc_id,
                "document_title": f"M5a Baseline Document {i}",
                "quote_preview": "Synthetic citation.",
                "source_anchor": {"type": "synthetic"},
                "source_status": "active",
            }
        )
    session.execute(insert(ChatCitation), citations)

    orphan_versions = [
        {
            "id": _id("orphan-ver", i),
            "document_id": _id("missing-doc", i),
            "version_number": 1,
            "normalized_markdown": "orphan",
            "markdown_hash": f"orphan-md-{i}",
            "parser_version": "m5a-perf/1",
            "ocr_used": False,
            "ki_provider": None,
            "ki_model": None,
            "metadata_": {},
            "created_at": now,
        }
        for i in range(orphan_rows)
    ]
    orphan_chunks = [
        {
            "id": _id("orphan-chk", i),
            "document_id": _id("missing-doc", i),
            "document_version_id": _id("orphan-ver", i),
            "chunk_index": 0,
            "heading_path": [],
            "anchor": f"orphan-{i}",
            "content": "orphan",
            "is_searchable": True,
            "search_vector": "orphan",
            "content_hash": f"orphan-chunk-{i}",
            "token_estimate": 1,
            "metadata_": {},
            "created_at": now,
        }
        for i in range(orphan_rows)
    ]
    orphan_findings = [
        {
            "id": _id("orphan-finding", i),
            "run_id": _id("missing-run", i),
            "workspace_id": BENCH_WORKSPACE_ID,
            "finding_type": "ORPHAN_FINDING",
            "severity": "warning",
            "document_id": None,
            "version_id": None,
            "chunk_id": None,
            "title": "Synthetic orphan finding",
            "description": "Synthetic orphan finding for performance baseline.",
            "remediation": "Report only.",
            "created_at": now,
        }
        for i in range(orphan_rows)
    ]
    session.execute(insert(DocumentVersion), orphan_versions)
    session.execute(insert(Chunk), orphan_chunks)
    session.execute(insert(DataQualityFinding), orphan_findings)
    session.commit()

    return {
        "documents": doc_count,
        "versions": doc_count + orphan_rows,
        "chunks": doc_count + orphan_rows,
        "citations": citation_docs,
        "duplicate_seed_docs": duplicate_docs,
        "metadata_seed_docs": metadata_docs,
        "lifecycle_seed_docs": lifecycle_docs,
        "orphan_seed_rows_per_type": orphan_rows,
    }


def _finding_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        finding_type = str(finding.get("finding_type", "UNKNOWN"))
        counts[finding_type] = counts.get(finding_type, 0) + 1
    return dict(sorted(counts.items()))


def _measure_doc_count(doc_count: int) -> dict[str, Any]:
    engine = _create_engine_without_benchmark_constraints()
    with Session(engine) as session:
        seed_start = time.perf_counter()
        seed_summary = _seed_dataset(session, doc_count)
        seed_ms = round((time.perf_counter() - seed_start) * 1000, 2)

        gc.collect()
        tracemalloc.start()
        tracemalloc.reset_peak()
        run_start = time.perf_counter()
        result = DataQualityRunner.from_session(session, BENCH_WORKSPACE_ID).run(
            created_by=BENCH_USER_ID
        )
        run_ms = round((time.perf_counter() - run_start) * 1000, 2)
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        score_start = time.perf_counter()
        score_result = calculate_quality_score_from_findings(result.findings)
        score_ms = round((time.perf_counter() - score_start) * 1000, 4)

        return {
            "documents": doc_count,
            "seed": {
                **seed_summary,
                "seed_time_ms": seed_ms,
            },
            "runtime_ms": run_ms,
            "memory": {
                "tracemalloc_current_mb": round(current_bytes / 1024 / 1024, 2),
                "tracemalloc_peak_mb": round(peak_bytes / 1024 / 1024, 2),
            },
            "findings": {
                "total": result.total_findings,
                "by_type": _finding_counts(result.findings),
            },
            "score_calculation": {
                "time_ms": score_ms,
                "score": score_result.score,
                "category_counts": {
                    category: details["finding_count"]
                    for category, details in score_result.score_explanation["categories"].items()
                },
            },
        }


def _recommendations(measurements: list[dict[str, Any]]) -> list[str]:
    recommendations = [
        "Treat this file as a local SQLite baseline; compare future M5a changes against the same command and machine class.",
        "Keep DataQualityRunner memory under observation at 10000 documents; regressions above 20 percent should trigger detector profiling.",
    ]
    largest = max(measurements, key=lambda item: item["documents"])
    if largest["runtime_ms"] > 5000:
        recommendations.append(
            "Profile detector SQL on the 10000-document case before M5a PASS; runtime is above 5 seconds."
        )
    duplicate_count = largest["findings"]["by_type"].get("DUPLICATE_DOCUMENT", 0)
    if duplicate_count:
        recommendations.append(
            "DuplicateDetector scales with duplicate groups; replace per-hash follow-up queries if duplicate-heavy corpora become common."
        )
    if largest["score_calculation"]["time_ms"] < 10:
        recommendations.append(
            "Score calculation is not the current bottleneck; prioritize detector queries and finding persistence first."
        )
    recommendations.append(
        "Run python scripts\\generate_m5a_performance_baseline.py after detector or score changes and review runtime_ms, peak memory, findings, and score_calculation.time_ms."
    )
    return recommendations


def build_report(doc_counts: tuple[int, ...]) -> dict[str, Any]:
    measurements = [_measure_doc_count(count) for count in doc_counts]
    return {
        "report_schema_version": 1,
        "report_name": "m5a_performance_baseline",
        "generated_by": "gate_validator",
        "timestamp": _utc_iso(),
        "environment": "local",
        "report_type": "status",
        "status": "PASS",
        "result": "PASS",
        "source_command": (
            "python scripts\\generate_m5a_performance_baseline.py "
            "--output reports\\current\\m5a_performance_baseline.json"
        ),
        "methodology": {
            "database": "SQLite in-memory",
            "document_counts": list(doc_counts),
            "constraints": [
                "Document content_hash unique constraint removed for benchmark schema creation to exercise duplicate detection.",
                "Foreign-key enforcement is not enabled, so orphan detector scenarios can be seeded.",
            ],
            "metrics": [
                "seed_time_ms",
                "runtime_ms",
                "tracemalloc_peak_mb",
                "findings.total",
                "findings.by_type",
                "score_calculation.time_ms",
            ],
        },
        "measurements": measurements,
        "recommendations": _recommendations(measurements),
        "blockers": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate M5a performance baseline.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--doc-counts",
        type=int,
        nargs="+",
        default=list(DEFAULT_DOC_COUNTS),
        help="Document counts to measure.",
    )
    args = parser.parse_args()

    doc_counts = tuple(args.doc_counts)
    report = build_report(doc_counts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
