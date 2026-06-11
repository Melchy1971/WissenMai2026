"""RAG-Endpunkte für GUI: documents, import, reindex, retrieve."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies.auth import require_workspace_member, AuthContext
from app.api.v1.approvals import create_approval

router = APIRouter(prefix="/rag", tags=["rag"])

_documents: list[dict] = [
    {
        "id": "doc-1",
        "title": "Onboarding Guide",
        "classification": "INTERNAL",
        "chunk_count": 12,
        "index_status": "indexed",
        "created_at": "2026-01-15T09:00:00Z",
    },
    {
        "id": "doc-2",
        "title": "Security Policy",
        "classification": "CONFIDENTIAL",
        "chunk_count": 8,
        "index_status": "indexed",
        "created_at": "2026-02-01T10:00:00Z",
    },
    {
        "id": "doc-secret",
        "title": "Classified Report",
        "classification": "SECRET",
        "chunk_count": 0,
        "index_status": "blocked",
        "created_at": "2026-03-01T08:00:00Z",
    },
]


class ImportRequest(BaseModel):
    title: str
    content: str = ""
    classification: str = "INTERNAL"
    source_url: str = ""


class RetrieveRequest(BaseModel):
    query: str
    exclude_secret: bool = True
    max_results: int = 5


@router.get("/documents")
def list_documents(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    """RAG-Dokumente listen. SECRET-Dokumente: Inhalt nie zurückgeben."""
    items = []
    for doc in _documents:
        entry = {k: v for k, v in doc.items() if k not in ("content", "chunks")}
        items.append(entry)
    return {"items": items, "total": len(items)}


@router.post("/import")
def import_document(
    body: ImportRequest,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    """Dokument importieren. GUI greift nie direkt auf Dateien zu."""
    # Privacy Mode blockiert Import-Persistenz (geprüft via governance store)
    from app.api.v1.governance import _privacy_mode
    if _privacy_mode:
        raise HTTPException(
            status_code=403,
            detail="Import-Persistenz im Privacy Mode blockiert",
        )
    new_doc = {
        "id": str(uuid.uuid4()),
        "title": body.title,
        "classification": body.classification,
        "chunk_count": 0,
        "index_status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
    }
    # SECRET-Inhalte niemals speichern
    if body.classification != "SECRET":
        _documents.append(new_doc)
    return {"ok": True, "document": new_doc}


@router.post("/documents/{doc_id}/reindex")
def reindex_document(
    doc_id: str,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    doc = next((d for d in _documents if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # SECRET-Dokumente nicht reindexen
    if doc["classification"] == "SECRET":
        raise HTTPException(status_code=403, detail="SECRET documents cannot be reindexed")
    doc["index_status"] = "reindexing"
    return {"ok": True, "status": "reindexing", "document_id": doc_id}


@router.post("/retrieve")
def retrieve(
    body: RetrieveRequest,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    """Retrieval-Test. SECRET-Dokumente werden nie als Prompt-Kontext verwendet."""
    results = []
    for doc in _documents:
        if body.exclude_secret and doc["classification"] == "SECRET":
            continue
        if doc["index_status"] != "indexed":
            continue
        # Simple mock: jedes Dokument als Treffer
        results.append({
            "document_id": doc["id"],
            "title": doc["title"],
            "classification": doc["classification"],
            "score": 0.85,
            # Inhalt niemals zurückgeben
        })
    return {"results": results[:body.max_results], "query": body.query}
