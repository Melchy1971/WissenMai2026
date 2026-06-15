"""RAG GUI endpoints with source-enforced retrieval responses."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, require_workspace_member
from app.api.v1.approvals import _log_audit, create_approval
from app.core.redaction import redact_for_ui

router = APIRouter(prefix="/rag", tags=["rag"])

_documents: list[dict] = []


class ImportRequest(BaseModel):
    title: str = Field(min_length=1)
    content: str = ""
    classification: str = "INTERNAL"
    source_url: str = ""


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    exclude_secret: bool = True
    max_results: int = Field(default=5, ge=1, le=20)


def _public_doc(doc: dict) -> dict:
    return redact_for_ui({k: v for k, v in doc.items() if k not in {"content", "chunks"}})


@router.get("/documents")
def list_documents(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    items = [_public_doc(doc) for doc in _documents]
    return {"items": items, "total": len(items)}


@router.post("/import")
def import_document(
    body: ImportRequest,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    from app.api.v1.governance import _privacy_mode

    if _privacy_mode:
        raise HTTPException(status_code=403, detail="Import persistence is blocked in Privacy Mode")
    classification = body.classification.upper()
    new_doc = {
        "id": str(uuid.uuid4()),
        "title": body.title,
        "classification": classification,
        "chunk_count": 0 if classification == "SECRET" else (1 if body.content else 0),
        "index_status": "blocked" if classification == "SECRET" else "pending",
        "created_at": datetime.now(UTC).isoformat(),
        "source_url": body.source_url,
    }
    if body.content and classification != "SECRET":
        new_doc["chunks"] = [
            {
                "chunk_id": f"{new_doc['id']}:chunk-0",
                "page": None,
                "score": 1.0,
                "classification": classification,
            }
        ]
    if classification != "SECRET":
        _documents.append(new_doc)
    _log_audit("RAG_DOCUMENT_IMPORTED", ctx.login, new_doc["id"], {"document": new_doc})
    return {"ok": True, "document": _public_doc(new_doc)}


@router.post("/documents/{doc_id}/reindex")
def reindex_document(
    doc_id: str,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    doc = next((d for d in _documents if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc["classification"] == "SECRET":
        raise HTTPException(status_code=403, detail="SECRET documents cannot be reindexed")
    approval = create_approval(
        action="RAG_REINDEX",
        risk="HIGH",
        category="rag",
        context={"document_id": doc_id},
    )
    _log_audit("RAG_REINDEX_APPROVAL_REQUIRED", ctx.login, doc_id, {"approval_id": approval["id"]})
    return {"ok": True, "approval_required": True, "approval_id": approval["id"], "status": doc["index_status"]}


def _build_source(doc: dict, chunk: dict) -> dict:
    return {
        "document_id": doc["id"],
        "document_name": doc["title"],
        "chunk_id": chunk["chunk_id"],
        "page": chunk.get("page"),
        "score": float(chunk.get("score", 0.0)),
        "classification": chunk.get("classification", doc["classification"]),
    }


def _retrieve_response(body: RetrieveRequest) -> dict:
    sources: list[dict] = []
    blocked_source_count = 0
    for doc in _documents:
        if doc.get("index_status") not in {"indexed", "pending"}:
            continue
        chunks = doc.get("chunks") or []
        for chunk in chunks:
            classification = chunk.get("classification", doc.get("classification"))
            if classification == "SECRET":
                blocked_source_count += 1
                continue
            sources.append(_build_source(doc, chunk))
            if len(sources) >= body.max_results:
                break
        if len(sources) >= body.max_results:
            break

    used_rag_context = True
    if used_rag_context and not sources:
        return {
            "status": "blocked",
            "used_rag_context": True,
            "answer": None,
            "sources": [],
            "results": [],
            "blocked_source_count": blocked_source_count,
            "message": "Antwort blockiert, weil keine sichtbaren Quellen verfuegbar sind.",
        }

    return {
        "status": "ok",
        "used_rag_context": used_rag_context,
        "answer": "Antwort mit sichtbaren Quellen verfuegbar.",
        "sources": sources,
        "results": sources,
        "blocked_source_count": blocked_source_count,
    }


@router.post("/retrieve")
def retrieve(
    body: RetrieveRequest,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    return _retrieve_response(body)


@router.post("/test-retrieval")
def test_retrieval(
    body: RetrieveRequest,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    return _retrieve_response(body)
