from __future__ import annotations

from datetime import UTC, datetime
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.main import app
from tests.postgres_truth.support import (
    TRUTH_OTHER_WORKSPACE_ID,
    TRUTH_SESSION_TOKEN,
    TRUTH_USER_ID,
    TRUTH_WORKSPACE_ID,
)


pytestmark = [pytest.mark.postgres_truth, pytest.mark.m4a_gate]

DOC_WORKSPACE_A = "f3000000-0000-0000-0000-0000000000a1"
DOC_WORKSPACE_B = "f3000000-0000-0000-0000-0000000000b1"
VER_WORKSPACE_A = "f5000000-0000-0000-0000-0000000000a1"
VER_WORKSPACE_B = "f5000000-0000-0000-0000-0000000000b1"
CHUNK_WORKSPACE_A = "f4000000-0000-0000-0000-0000000000a1"
CHUNK_WORKSPACE_B = "f4000000-0000-0000-0000-0000000000b1"
CHAT_WORKSPACE_B = "truth-chat-session-workspace-b"
M4A_TERM = "m4aworkspaceisolationtruth"


def test_m4a_user_a_lists_only_documents_from_workspace_a(
    truth_client: TestClient,
    truth_session: Session,
) -> None:
    _seed_workspace_document(
        truth_session,
        document_id=DOC_WORKSPACE_A,
        version_id=VER_WORKSPACE_A,
        chunk_id=CHUNK_WORKSPACE_A,
        workspace_id=TRUTH_WORKSPACE_ID,
        title="Workspace A Truth",
        content=f"{M4A_TERM} workspace A visible document",
    )
    _seed_workspace_document(
        truth_session,
        document_id=DOC_WORKSPACE_B,
        version_id=VER_WORKSPACE_B,
        chunk_id=CHUNK_WORKSPACE_B,
        workspace_id=TRUTH_OTHER_WORKSPACE_ID,
        title="Workspace B Truth",
        content=f"{M4A_TERM} workspace B hidden document",
    )

    response = truth_client.get("/documents")

    assert response.status_code == 200
    document_ids = {item["id"] for item in response.json()}
    assert DOC_WORKSPACE_A in document_ids
    assert DOC_WORKSPACE_B not in document_ids


def test_m4a_user_a_cannot_import_into_workspace_b(truth_seed: dict[str, str], truth_session: Session) -> None:
    client = _client(token=truth_seed["token"], workspace_id=TRUTH_OTHER_WORKSPACE_ID)

    response = client.post(
        "/documents/import",
        files={"file": ("m4a-forbidden.txt", b"# forbidden\n", "text/plain")},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "WORKSPACE_ACCESS_FORBIDDEN"
    assert (
        truth_session.execute(
            text("select count(*) from background_jobs where workspace_id = :workspace_id"),
            {"workspace_id": TRUTH_OTHER_WORKSPACE_ID},
        ).scalar_one()
        == 0
    )


def test_m4a_user_a_cannot_search_workspace_b(truth_seed: dict[str, str]) -> None:
    client = _client(token=truth_seed["token"], workspace_id=TRUTH_OTHER_WORKSPACE_ID)

    response = client.get("/api/v1/search/chunks", params={"q": M4A_TERM})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "WORKSPACE_ACCESS_FORBIDDEN"


def test_m4a_user_a_cannot_use_chat_session_from_workspace_b(
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    truth_session.execute(
        text(
            """
            insert into chat_sessions (id, workspace_id, owner_user_id, title, created_at, updated_at)
            values (:id, :workspace_id, :user_id, 'Workspace B chat', now(), now())
            """
        ),
        {
            "id": CHAT_WORKSPACE_B,
            "workspace_id": TRUTH_OTHER_WORKSPACE_ID,
            "user_id": TRUTH_USER_ID,
        },
    )
    truth_session.commit()
    client = _client(token=truth_seed["token"], workspace_id=TRUTH_WORKSPACE_ID)

    detail_response = client.get(f"/api/v1/chat/sessions/{CHAT_WORKSPACE_B}")
    message_response = client.post(
        f"/api/v1/chat/sessions/{CHAT_WORKSPACE_B}/messages",
        json={"question": M4A_TERM, "retrieval_limit": 3},
    )

    assert detail_response.status_code == 404
    assert detail_response.json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"
    assert message_response.status_code == 404
    assert message_response.json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"


def test_m4a_manipulated_x_workspace_id_is_forbidden(truth_seed: dict[str, str]) -> None:
    client = _client(token=truth_seed["token"], workspace_id=TRUTH_OTHER_WORKSPACE_ID)

    response = client.get("/documents")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "WORKSPACE_ACCESS_FORBIDDEN"


def test_m4a_missing_x_workspace_id_is_auth_or_forbidden_contract(truth_seed: dict[str, str]) -> None:
    client = TestClient(
        app,
        headers={"Authorization": f"Bearer {truth_seed['token']}"},
        raise_server_exceptions=False,
    )

    response = client.get("/documents")

    assert response.status_code in {401, 403}
    assert response.json()["error"]["code"] in {"AUTH_REQUIRED", "WORKSPACE_ACCESS_FORBIDDEN"}


def test_m4a_admin_diagnostics_without_admin_role_is_forbidden(
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    truth_session.execute(
        text(
            """
            update workspace_memberships
            set role = 'member'
            where user_id = :user_id and workspace_id = :workspace_id
            """
        ),
        {"user_id": TRUTH_USER_ID, "workspace_id": TRUTH_WORKSPACE_ID},
    )
    truth_session.commit()
    client = _client(token=truth_seed["token"], workspace_id=TRUTH_WORKSPACE_ID)

    response = client.get("/api/v1/admin/diagnostics")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def _client(*, token: str = TRUTH_SESSION_TOKEN, workspace_id: str) -> TestClient:
    return TestClient(
        app,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Workspace-Id": workspace_id,
        },
        raise_server_exceptions=False,
    )


def _seed_workspace_document(
    session: Session,
    *,
    document_id: str,
    version_id: str,
    chunk_id: str,
    workspace_id: str,
    title: str,
    content: str,
) -> None:
    created = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)
    session.execute(
        text(
            """
            insert into documents
                (id, workspace_id, owner_user_id, current_version_id, title, source_type, mime_type,
                 content_hash, import_status, lifecycle_status, archived_at, deleted_at, created_at, updated_at)
            values
                (:document_id, :workspace_id, :owner_user_id, null, :title, 'upload', 'text/plain',
                 :content_hash, 'pending', 'active', null, null, :created_at, :created_at)
            """
        ),
        {
            "document_id": document_id,
            "workspace_id": workspace_id,
            "owner_user_id": TRUTH_USER_ID,
            "title": title,
            "content_hash": f"hash-{document_id}",
            "created_at": created,
        },
    )
    session.execute(
        text(
            """
            insert into document_versions
                (id, document_id, version_number, normalized_markdown, markdown_hash, parser_version,
                 ocr_used, ki_provider, ki_model, metadata, created_at)
            values
                (:version_id, :document_id, 1, :content, :markdown_hash, 'truth-parser',
                 false, null, null, cast(:metadata as jsonb), :created_at)
            """
        ),
        {
            "version_id": version_id,
            "document_id": document_id,
            "content": content,
            "markdown_hash": f"md-{version_id}",
            "metadata": json.dumps({}),
            "created_at": created,
        },
    )
    session.execute(
        text(
            """
            insert into document_chunks
                (id, document_id, document_version_id, chunk_index, heading_path, anchor, content,
                 is_searchable, content_hash, token_estimate, metadata, created_at)
            values
                (:chunk_id, :document_id, :version_id, 0, cast(:heading_path as jsonb), :anchor, :content,
                 true, :content_hash, 20, cast(:metadata as jsonb), :created_at)
            """
        ),
        {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "version_id": version_id,
            "heading_path": json.dumps([]),
            "anchor": f"truth-{chunk_id}",
            "content": content,
            "content_hash": f"chunk-{chunk_id}",
            "metadata": json.dumps(
                {
                    "source_anchor": {
                        "type": "text",
                        "page": None,
                        "paragraph": 1,
                        "char_start": 0,
                        "char_end": len(content),
                    }
                }
            ),
            "created_at": created,
        },
    )
    session.execute(
        text(
            """
            update documents
            set current_version_id = :version_id, import_status = 'chunked'
            where id = :document_id
            """
        ),
        {"version_id": version_id, "document_id": document_id},
    )
    session.commit()
