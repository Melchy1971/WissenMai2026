from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.documents import User, Workspace, WorkspaceMembership  # noqa: E402
from app.services.auth import hash_password  # noqa: E402


def _load_local_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_local_env()

LOCAL_DEV_DATABASE_URL = "postgresql+psycopg://testuser:testpass@127.0.0.1:5433/wissen_test"
DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
# Canonical: SEED_ADMIN_* › WISSEN_DEV_* (legacy) › built-in fallback.
DEFAULT_LOGIN: str = (
    os.environ.get("SEED_ADMIN_LOGIN")
    or os.environ.get("WISSEN_DEV_LOGIN")
    or "admin@localhost"
)
DEFAULT_PASSWORD: str = (
    os.environ.get("SEED_ADMIN_PASSWORD")
    or os.environ.get("WISSEN_DEV_PASSWORD")
    or "change-me"
)


def _database_url() -> str:
    return os.environ.get("DATABASE_URL") or LOCAL_DEV_DATABASE_URL


def _alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", _database_url())
    return config


def _seed_defaults() -> None:
    engine = create_engine(_database_url(), pool_pre_ping=True)
    now = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)
    try:
        with Session(engine) as session:
            workspace = session.scalar(select(Workspace).where(Workspace.id == DEFAULT_WORKSPACE_ID))
            if workspace is None:
                session.add(
                    Workspace(
                        id=DEFAULT_WORKSPACE_ID,
                        name="Default Workspace",
                        is_default=True,
                        created_at=now,
                    )
                )

            user = session.scalar(select(User).where(User.id == DEFAULT_USER_ID))
            if user is None:
                session.add(
                    User(
                        id=DEFAULT_USER_ID,
                        display_name="Default User",
                        login=DEFAULT_LOGIN,
                        password_hash=hash_password(DEFAULT_PASSWORD, salt="devsalt"),
                        is_active=True,
                        is_default=True,
                        created_at=now,
                    )
                )
            else:
                user.display_name = DEFAULT_LOGIN
                user.login = DEFAULT_LOGIN
                user.password_hash = hash_password(DEFAULT_PASSWORD, salt="devsalt")
                user.is_active = True

            membership = session.scalar(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == DEFAULT_WORKSPACE_ID,
                    WorkspaceMembership.user_id == DEFAULT_USER_ID,
                )
            )
            if membership is None:
                session.add(
                    WorkspaceMembership(
                        id="default-membership",
                        workspace_id=DEFAULT_WORKSPACE_ID,
                        user_id=DEFAULT_USER_ID,
                        role="owner",
                        created_at=now,
                        updated_at=now,
                    )
                )

            session.commit()
    finally:
        engine.dispose()


def main() -> int:
    os.environ.setdefault("DATABASE_URL", _database_url())
    command.upgrade(_alembic_config(), "head")
    _seed_defaults()
    print(f"Bootstrapped local backend database at {os.environ['DATABASE_URL']}")
    print(f"Default login: {DEFAULT_LOGIN}")
    print("Default password: configured via local environment")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
