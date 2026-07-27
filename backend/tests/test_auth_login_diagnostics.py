"""
Tests für strukturiertes Auth-Login-Logging (Task D).

Regeln:
  - API-Response bleibt generisch: AUTH_INVALID_CREDENTIALS
  - Interne Logs unterscheiden: login_not_found, user_inactive, password_mismatch, db_error, empty_credentials
  - Logs enthalten niemals Passwörter
"""
from __future__ import annotations

import logging

import pytest
from sqlalchemy.orm import Session

from app.services.auth import AuthService, AuthenticationError, hash_password


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_service(db_session: Session) -> AuthService:
    return AuthService(db_session)


# ── Hilfsfunktion: Logs abfangen ─────────────────────────────────────────────


class LogCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def reasons(self) -> list[str]:
        return [r.extra_dict.get("reason", "") for r in self.records if hasattr(r, "extra_dict")]

    def events(self) -> list[str]:
        return [getattr(r, "__dict__", {}).get("event", "") for r in self.records]


def _capture_auth_logs() -> LogCapture:
    handler = LogCapture()
    logger = logging.getLogger("app.services.auth")
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    return handler


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_login_not_found_raises_generic_error(db_session: Session) -> None:
    """Unbekannter Login → AuthenticationError mit generischer Meldung."""
    handler = _capture_auth_logs()
    svc = _make_service(db_session)

    with pytest.raises(AuthenticationError) as exc_info:
        svc.login(login="nobody@example.com", password="any")

    assert "Invalid credentials" in str(exc_info.value)
    logging.getLogger("app.services.auth").removeHandler(handler)


def test_login_not_found_logs_reason(db_session: Session) -> None:
    """Unbekannter Login → Log-Reason ist 'login_not_found', kein Passwort im Log."""
    handler = _capture_auth_logs()
    logger = logging.getLogger("app.services.auth")

    records: list[logging.LogRecord] = []
    original_warning = logger.warning

    def capturing_warning(msg, *args, **kwargs):
        extra = kwargs.get("extra", {})
        records.append(extra)
        return original_warning(msg, *args, **kwargs)

    logger.warning = capturing_warning  # type: ignore[method-assign]
    try:
        svc = _make_service(db_session)
        with pytest.raises(AuthenticationError):
            svc.login(login="nobody@example.com", password="secret")
    finally:
        logger.warning = original_warning  # type: ignore[method-assign]
        logger.removeHandler(handler)

    assert any(r.get("reason") == "login_not_found" for r in records)
    # Kein Passwort im Log
    all_values = " ".join(str(v) for rec in records for v in rec.values())
    assert "secret" not in all_values


def test_user_inactive_logs_reason(db_session: Session) -> None:
    """Inaktiver User → reason=user_inactive, Response bleibt generisch."""
    from app.models.documents import User, Workspace, WorkspaceMembership
    from uuid import uuid4
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    ws = Workspace(id=str(uuid4()), name="ws", is_default=False, created_at=now)
    user = User(
        id=str(uuid4()),
        display_name="Inactive User",
        login="inactive@example.com",
        password_hash=hash_password("pw123", salt="inactive@example.com"),
        is_active=False,  # ← inactive
        is_default=False,
        created_at=now,
    )
    db_session.add_all([ws, user])
    db_session.commit()

    records: list[dict] = []
    logger = logging.getLogger("app.services.auth")
    original_warning = logger.warning

    def capturing_warning(msg, *args, **kwargs):
        records.append(kwargs.get("extra", {}))
        return original_warning(msg, *args, **kwargs)

    logger.warning = capturing_warning  # type: ignore[method-assign]
    try:
        with pytest.raises(AuthenticationError) as exc_info:
            AuthService(db_session).login(login="inactive@example.com", password="pw123")
    finally:
        logger.warning = original_warning  # type: ignore[method-assign]

    assert "Invalid credentials" in str(exc_info.value)
    assert any(r.get("reason") == "user_inactive" for r in records)
    # user_id im Log, aber kein Passwort
    assert all("pw123" not in str(v) for rec in records for v in rec.values())


def test_password_mismatch_logs_reason(db_session: Session) -> None:
    """Falsches Passwort → reason=password_mismatch."""
    from app.models.documents import User, Workspace
    from uuid import uuid4
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    ws = Workspace(id=str(uuid4()), name="ws2", is_default=False, created_at=now)
    user = User(
        id=str(uuid4()),
        display_name="Active User",
        login="active@example.com",
        password_hash=hash_password("correct_pw", salt="active@example.com"),
        is_active=True,
        is_default=False,
        created_at=now,
    )
    db_session.add_all([ws, user])
    db_session.commit()

    records: list[dict] = []
    logger = logging.getLogger("app.services.auth")
    original_warning = logger.warning

    def capturing_warning(msg, *args, **kwargs):
        records.append(kwargs.get("extra", {}))
        return original_warning(msg, *args, **kwargs)

    logger.warning = capturing_warning  # type: ignore[method-assign]
    try:
        with pytest.raises(AuthenticationError):
            AuthService(db_session).login(login="active@example.com", password="wrong_pw")
    finally:
        logger.warning = original_warning  # type: ignore[method-assign]

    assert any(r.get("reason") == "password_mismatch" for r in records)
    # Kein Passwort im Log
    assert all("wrong_pw" not in str(v) for rec in records for v in rec.values())
    assert all("correct_pw" not in str(v) for rec in records for v in rec.values())


def test_empty_credentials_logs_reason(db_session: Session) -> None:
    """Leere Credentials → reason=empty_credentials."""
    records: list[dict] = []
    logger = logging.getLogger("app.services.auth")
    original_warning = logger.warning

    def capturing_warning(msg, *args, **kwargs):
        records.append(kwargs.get("extra", {}))
        return original_warning(msg, *args, **kwargs)

    logger.warning = capturing_warning  # type: ignore[method-assign]
    try:
        with pytest.raises(AuthenticationError):
            AuthService(db_session).login(login="", password="")
    finally:
        logger.warning = original_warning  # type: ignore[method-assign]

    assert any(r.get("reason") == "empty_credentials" for r in records)
