from __future__ import annotations

from datetime import UTC, datetime
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.main import app
from tests.postgres_truth.support import TruthIds


pytestmark = [pytest.mark.postgres_truth, pytest.mark.m4a_auth_truth]


def test_m4a_user_a_lists_only_documents_from_workspace_a(
    truth_client: TestClient,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    term = truth_ids.term("m4a-workspace-isolation")
    doc_workspace_a = truth_ids.document_id("workspace-a")
    doc_workspace_b = truth_ids.document_id("workspace-b")
    _seed_workspace_document(
        truth_session,
        truth_ids=truth_ids,
        document_id=doc_workspace_a,
        version_id=truth_ids.version_id("workspace-a"),
        chunk_id=truth_ids.chunk_id("workspace-a"),
        workspace_id=truth_seed["workspace_id"],
        title=f"Workspace A Truth {truth_ids.slug}",
        content=f"{term} workspace A visible document",
    )
    _seed_workspace_document(
        truth_session,
        truth_ids=truth_ids,
        document_id=doc_workspace_b,
        version_id=truth_ids.version_id("workspace-b"),
        chunk_id=truth_ids.chunk_id("workspace-b"),
        workspace_id=truth_seed["other_workspace_id"],
        title=f"Workspace B Truth {truth_ids.slug}",
        content=f"{term} workspace B hidden document",
    )

    response = truth_client.get("/documents")

    assert response.status_code == 200
    document_ids = {item["id"] for item in response.json()}
    assert doc_workspace_a in document_ids
    assert doc_workspace_b not in document_ids


def test_m4a_user_a_cannot_import_into_workspace_b(truth_seed: dict[str, str], truth_session: Session) -> None:
    client = _client(token=truth_seed["token"], workspace_id=truth_seed["other_workspace_id"])

    response = client.post(
        "/documents/import",
        files={"file": ("m4a-forbidden.txt", b"# forbidden\n", "text/plain")},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "WORKSPACE_ACCESS_FORBIDDEN"
    assert (
        truth_session.execute(
            text("select count(*) from background_jobs where workspace_id = :workspace_id"),
            {"workspace_id": truth_seed["other_workspace_id"]},
        ).scalar_one()
        == 0
    )


def test_m4a_user_a_cannot_search_workspace_b(truth_ids: TruthIds, truth_seed: dict[str, str]) -> None:
    client = _client(token=truth_seed["token"], workspace_id=truth_seed["other_workspace_id"])

    response = client.get("/api/v1/search/chunks", params={"q": truth_ids.term("m4a-workspace-isolation")})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "WORKSPACE_ACCESS_FORBIDDEN"


def test_m4a_user_a_cannot_use_chat_session_from_workspace_b(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    chat_workspace_b = truth_ids.chat_session_id("workspace-b")
    truth_session.execute(
        text(
            """
            insert into chat_sessions (id, workspace_id, owner_user_id, title, created_at, updated_at)
            values (:id, :workspace_id, :user_id, 'Workspace B chat', now(), now())
            """
        ),
        {
            "id": chat_workspace_b,
            "workspace_id": truth_seed["other_workspace_id"],
            "user_id": truth_seed["user_id"],
        },
    )
    truth_session.commit()
    client = _client(token=truth_seed["token"], workspace_id=truth_seed["workspace_id"])

    detail_response = client.get(f"/api/v1/chat/sessions/{chat_workspace_b}")
    message_response = client.post(
        f"/api/v1/chat/sessions/{chat_workspace_b}/messages",
        json={"question": truth_ids.term("m4a-workspace-isolation"), "retrieval_limit": 3},
    )

    assert detail_response.status_code == 404
    assert detail_response.json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"
    assert message_response.status_code == 404
    assert message_response.json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"


def test_m4a_manipulated_x_workspace_id_is_forbidden(truth_seed: dict[str, str]) -> None:
    client = _client(token=truth_seed["token"], workspace_id=truth_seed["other_workspace_id"])

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
        {"user_id": truth_seed["user_id"], "workspace_id": truth_seed["workspace_id"]},
    )
    truth_session.commit()
    client = _client(token=truth_seed["token"], workspace_id=truth_seed["workspace_id"])

    response = client.get("/api/v1/admin/diagnostics")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_m4a_user_a_cannot_read_or_replay_workspace_b_queue_job(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    created = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)
    job_id = truth_ids.job_id("workspace-b-dead-letter")
    truth_session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'document_import', 'dead_letter', :workspace_id, :user_id, cast(:payload as jsonb), null,
                1, 1, 'Job in Dead Letter verschoben', 'IMPORT_FAILED', 'foreign workspace failure',
                3, null, null, :created_at, :created_at, :created_at
            )
            """
        ),
        {
            "id": job_id,
            "workspace_id": truth_seed["other_workspace_id"],
            "user_id": truth_seed["other_user_id"],
            "payload": json.dumps({"filename": f"{truth_ids.slug}-foreign.txt"}),
            "created_at": created,
        },
    )
    truth_session.commit()
    client = _client(token=truth_seed["token"], workspace_id=truth_seed["workspace_id"])

    read_response = client.get(f"/api/v1/jobs/{job_id}")
    replay_response = client.post(f"/api/v1/admin/jobs/{job_id}/replay")

    assert read_response.status_code == 404
    assert read_response.json()["error"]["code"] == "JOB_NOT_FOUND"
    assert replay_response.status_code == 404
    assert replay_response.json()["error"]["code"] == "JOB_NOT_FOUND"
    row = truth_session.execute(
        text("select status, payload from background_jobs where id = :id"),
        {"id": job_id},
    ).one()
    assert row.status == "dead_letter"
    assert "replay_history" not in row.payload


def test_m4a_user_a_cannot_archive_workspace_b_document(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    doc_id = truth_ids.document_id("workspace-b-archive-target")
    _seed_workspace_document(
        truth_session,
        truth_ids=truth_ids,
        document_id=doc_id,
        version_id=truth_ids.version_id("workspace-b-archive-target"),
        chunk_id=truth_ids.chunk_id("workspace-b-archive-target"),
        workspace_id=truth_seed["other_workspace_id"],
        title=f"Workspace B Archive Target {truth_ids.slug}",
        content=f"{truth_ids.term('m4a-lifecycle-isolation')} archive target",
    )
    client = _client(token=truth_seed["token"], workspace_id=truth_seed["workspace_id"])

    response = client.patch(f"/documents/{doc_id}/archive")

    assert response.status_code == 404
    row = truth_session.execute(
        text("select lifecycle_status from documents where id = :id"),
        {"id": doc_id},
    ).one()
    assert row.lifecycle_status == "active"


def test_m4a_user_a_cannot_delete_workspace_b_document(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    doc_id = truth_ids.document_id("workspace-b-delete-target")
    _seed_workspace_document(
        truth_session,
        truth_ids=truth_ids,
        document_id=doc_id,
        version_id=truth_ids.version_id("workspace-b-delete-target"),
        chunk_id=truth_ids.chunk_id("workspace-b-delete-target"),
        workspace_id=truth_seed["other_workspace_id"],
        title=f"Workspace B Delete Target {truth_ids.slug}",
        content=f"{truth_ids.term('m4a-lifecycle-isolation')} delete target",
    )
    client = _client(token=truth_seed["token"], workspace_id=truth_seed["workspace_id"])

    response = client.delete(f"/documents/{doc_id}")

    assert response.status_code == 404
    row = truth_session.execute(
        text("select lifecycle_status from documents where id = :id"),
        {"id": doc_id},
    ).one()
    assert row.lifecycle_status == "active"


def test_m4a_logout_revokes_session(truth_seed: dict[str, str]) -> None:
    client = TestClient(
        app,
        headers={"Authorization": f"Bearer {truth_seed['token']}"},
        raise_server_exceptions=False,
    )

    logout_response = client.post("/api/v1/auth/logout")
    me_response = client.get("/api/v1/auth/me")

    assert logout_response.status_code == 204
    assert me_response.status_code == 401
    assert me_response.json()["error"]["code"] == "AUTH_REQUIRED"


def _client(*, token: str, workspace_id: str) -> TestClient:
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
    truth_ids: TruthIds,
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
            "owner_user_id": truth_ids.user_id,
            "title": title,
            "content_hash": truth_ids.content_hash(f"workspace-document-{document_id}"),
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
            "content_hash": truth_ids.content_hash(f"workspace-chunk-{chunk_id}"),
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
