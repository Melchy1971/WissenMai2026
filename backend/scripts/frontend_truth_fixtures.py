import os
import uuid
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.documents import User, Workspace, WorkspaceMembership, Document, Chunk
from app.services.auth import hash_password

DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/wissen")
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def create_frontend_truth_fixtures():
    with session_scope() as session:
        # Workspace
        ws = Workspace(id=str(uuid.uuid4()), name="frontend-truth-ws")
        session.add(ws)
        # User
        user = User(id=str(uuid.uuid4()), login="frontend-truth-user", display_name="Frontend Truth User", password_hash=hash_password("frontend-truth-pass"))
        session.add(user)
        # Membership
        membership = WorkspaceMembership(user_id=user.id, workspace_id=ws.id, role="owner")
        session.add(membership)
        # Documents
        doc_active = Document(id=str(uuid.uuid4()), workspace_id=ws.id, title="GUI Truth Active Document", lifecycle_status="active")
        doc_archived = Document(id=str(uuid.uuid4()), workspace_id=ws.id, title="GUI Truth Archived Document", lifecycle_status="archived")
        doc_deleted = Document(id=str(uuid.uuid4()), workspace_id=ws.id, title="GUI Truth Deleted Document", lifecycle_status="deleted")
        session.add_all([doc_active, doc_archived, doc_deleted])
        # Chunk
        chunk = Chunk(id=str(uuid.uuid4()), document_id=doc_active.id, text="truthneedle active knowledge base content", position=1)
        session.add(chunk)
        session.flush()
        return {
            "workspace_id": ws.id,
            "user_id": user.id,
            "doc_active_id": doc_active.id,
            "doc_archived_id": doc_archived.id,
            "doc_deleted_id": doc_deleted.id,
            "chunk_id": chunk.id
        }

def cleanup_frontend_truth_fixtures(ids):
    with session_scope() as session:
        session.query(Chunk).filter(Chunk.id == ids["chunk_id"]).delete()
        session.query(Document).filter(Document.id.in_([ids["doc_active_id"], ids["doc_archived_id"], ids["doc_deleted_id"]])).delete()
        session.query(WorkspaceMembership).filter(WorkspaceMembership.user_id == ids["user_id"], WorkspaceMembership.workspace_id == ids["workspace_id"]).delete()
        session.query(User).filter(User.id == ids["user_id"]).delete()
        session.query(Workspace).filter(Workspace.id == ids["workspace_id"]).delete()
