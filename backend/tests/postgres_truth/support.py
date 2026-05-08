from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


TRUTH_WORKSPACE_ID = "f1000000-0000-0000-0000-000000000001"
TRUTH_OTHER_WORKSPACE_ID = "f1000000-0000-0000-0000-000000000002"
TRUTH_USER_ID = "f2000000-0000-0000-0000-000000000001"
TRUTH_OTHER_USER_ID = "f2000000-0000-0000-0000-000000000002"
TRUTH_SESSION_TOKEN = "postgres-truth-session-token"
TRUTH_OTHER_SESSION_TOKEN = "postgres-truth-other-session-token"


def assert_no_truth_rows(session: Session) -> None:
    checks = {
        "workspaces": "select count(*) from workspaces where id::text like 'f1000000-%'",
        "users": "select count(*) from users where id::text like 'f2000000-%'",
        "documents": "select count(*) from documents where id::text like 'f3000000-%'",
        "document_versions": "select count(*) from document_versions where id::text like 'f5000000-%'",
        "document_chunks": "select count(*) from document_chunks where id::text like 'f4000000-%'",
        "chat_sessions": "select count(*) from chat_sessions where id::text like 'truth-%'",
        "background_jobs": "select count(*) from background_jobs where id::text like 'truth-%' or workspace_id::text like 'f1000000-%'",
    }
    stale = {name: session.execute(text(query)).scalar_one() for name, query in checks.items()}
    assert stale == {name: 0 for name in checks}
