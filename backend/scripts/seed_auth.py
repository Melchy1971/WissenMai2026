from app.services.auth import hash_password
from app.models.documents import User, Workspace, WorkspaceMembership
from app.db.session import get_session
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime, UTC

USER_LOGIN = "mdickscheit@gmail.com"
USER_PASSWORD = "Alex..2026"
USER_DISPLAY_NAME = "Seed User"
WORKSPACE_NAME = "WissensDB Local"
WORKSPACE_STATUS = "active"
ROLE = "admin"


def main():
    for session in get_session():
        # User
        user = session.scalar(select(User).where(User.login == USER_LOGIN))
        if not user:
            user = User(
                id=str(uuid4()),
                display_name=USER_DISPLAY_NAME,
                login=USER_LOGIN,
                password_hash=hash_password(USER_PASSWORD, salt=USER_LOGIN),
                is_active=True,
                is_default=False,
                created_at=datetime.now(UTC),
            )
            session.add(user)
            session.commit()
            print(f"User created: {user.id}")
        else:
            # Update password and is_active if needed
            updated = False
            if not user.is_active:
                user.is_active = True
                updated = True
            new_hash = hash_password(USER_PASSWORD, salt=USER_LOGIN)
            if user.password_hash != new_hash:
                user.password_hash = new_hash
                updated = True
            if updated:
                session.commit()
                print(f"User updated: {user.id}")

        # Workspace
        workspace = session.scalar(select(Workspace).where(Workspace.name == WORKSPACE_NAME))
        if not workspace:
            workspace = Workspace(
                id=str(uuid4()),
                name=WORKSPACE_NAME,
                is_default=False,
                created_at=datetime.now(UTC),
            )
            session.add(workspace)
            session.commit()
            print(f"Workspace created: {workspace.id}")

        # Membership
        membership = session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.workspace_id == workspace.id,
            )
        )
        if not membership:
            membership = WorkspaceMembership(
                id=str(uuid4()),
                workspace_id=workspace.id,
                user_id=user.id,
                role=ROLE,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(membership)
            session.commit()
            print(f"Membership created: {membership.id}")
        else:
            if membership.role != ROLE:
                membership.role = ROLE
                session.commit()
                print(f"Membership role updated: {membership.id}")

        # Validation output
        print("\nValidation:")
        print(f"user_id: {user.id}")
        print(f"workspace_id: {workspace.id}")
        print(f"role: {membership.role}")
        print(f"is_active: {user.is_active}")

if __name__ == "__main__":
    main()
