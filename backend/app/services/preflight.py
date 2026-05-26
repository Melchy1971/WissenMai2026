"""
PreflightService
================
Prüft kritische Runtime-Voraussetzungen beim Backend-Start oder auf Anfrage.

Checks:
  1. database_url_set      — DATABASE_URL ist konfiguriert
  2. db_reachable          — Datenbankverbindung möglich
  3. alembic_head          — Schema ist auf aktuellem Stand
  4. public_schema_tables  — Pflichttabellen existieren
  5. seed_user_present     — Seed-User vorhanden (optional: Warnung, kein Fehler)
  6. app_config_complete   — Pflicht-Settings sind gesetzt

Fail-Fast-Modus:
  - production (APP_ENV=production): immer fail-fast
  - development: PREFLIGHT_FAIL_FAST=true → fail-fast, =false (Standard) → nur warnen

Verwendung:
  from app.services.preflight import PreflightService
  result = PreflightService().run()
  if not result.passed:
      raise RuntimeError(result.summary())
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import DatabaseConfigurationError, check_database_connection, get_sqlalchemy_database_url

logger = logging.getLogger("app.services.preflight")

CheckStatus = Literal["pass", "warn", "fail"]

# Tables that must exist for the app to be operational.
REQUIRED_TABLES = [
    "users",
    "workspaces",
    "workspace_memberships",
    "documents",
    "auth_sessions",
    "alembic_version",
]

# Settings that must be non-None/non-empty in production.
REQUIRED_SETTINGS_PROD = ["database_url"]
# Warn-only in development when missing.
REQUIRED_SETTINGS_DEV_WARN = ["admin_api_token"]


@dataclass
class PreflightCheck:
    id: str
    status: CheckStatus
    detail: str | None = None


@dataclass
class PreflightResult:
    checks: list[PreflightCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.status != "fail" for c in self.checks)

    @property
    def failed_checks(self) -> list[PreflightCheck]:
        return [c for c in self.checks if c.status == "fail"]

    @property
    def warned_checks(self) -> list[PreflightCheck]:
        return [c for c in self.checks if c.status == "warn"]

    def summary(self) -> str:
        lines = [f"Preflight {'PASS' if self.passed else 'FAIL'}"]
        for c in self.checks:
            prefix = {"pass": "[OK]", "warn": "[WARN]", "fail": "[FAIL]"}[c.status]
            lines.append(f"  {prefix} {c.id}" + (f": {c.detail}" if c.detail else ""))
        return "\n".join(lines)

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": [
                {"id": c.id, "status": c.status, **({"detail": c.detail} if c.detail else {})}
                for c in self.checks
            ],
        }


def _fail_fast_mode() -> bool:
    """True when any preflight failure must abort startup."""
    if settings.app_env == "production":
        return True
    env_val = os.environ.get("PREFLIGHT_FAIL_FAST", "").lower()
    return env_val in ("1", "true", "yes")


class PreflightService:
    def __init__(self) -> None:
        self._checks: list[PreflightCheck] = []

    def _add(self, check_id: str, status: CheckStatus, detail: str | None = None) -> None:
        self._checks.append(PreflightCheck(id=check_id, status=status, detail=detail))
        log_fn = logger.info if status == "pass" else (logger.warning if status == "warn" else logger.error)
        log_fn(
            "preflight.check",
            extra={"event": "preflight.check", "check": check_id, "status": status, "detail": detail},
        )

    # ── Individual checks ────────────────────────────────────────────────────

    def _check_database_url(self) -> bool:
        if settings.database_url:
            self._add("database_url_set", "pass")
            return True
        self._add("database_url_set", "fail", "DATABASE_URL is not configured")
        return False

    def _check_db_reachable(self) -> bool:
        try:
            check_database_connection()
            self._add("db_reachable", "pass")
            return True
        except DatabaseConfigurationError as exc:
            self._add("db_reachable", "fail", str(exc))
            return False
        except Exception as exc:
            self._add("db_reachable", "fail", f"Connection failed: {type(exc).__name__}: {exc}")
            return False

    def _check_alembic_head(self) -> None:
        try:
            from sqlalchemy import create_engine
            from alembic.runtime.migration import MigrationContext
            from alembic.script import ScriptDirectory
            from alembic.config import Config as AlembicConfig

            engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=False)
            with engine.connect() as conn:
                migration_ctx = MigrationContext.configure(conn)
                current_heads = set(migration_ctx.get_current_heads())

            import pathlib
            repo_root = pathlib.Path(__file__).resolve().parents[4]
            alembic_cfg = AlembicConfig(str(repo_root / "backend" / "alembic.ini"))
            alembic_cfg.set_main_option(
                "script_location", str(repo_root / "backend" / "migrations")
            )
            script = ScriptDirectory.from_config(alembic_cfg)
            expected_heads = {rev.revision for rev in script.get_revisions("heads")}

            if current_heads == expected_heads:
                self._add("alembic_head", "pass", f"heads={current_heads}")
            else:
                missing = expected_heads - current_heads
                extra = current_heads - expected_heads
                self._add(
                    "alembic_head", "fail",
                    f"Schema out of date. missing={missing} extra={extra}",
                )
        except Exception as exc:
            self._add("alembic_head", "warn", f"Could not verify Alembic head: {exc}")

    def _check_public_schema_tables(self) -> None:
        try:
            from sqlalchemy import create_engine
            engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=False)
            inspector = inspect(engine)
            existing = set(inspector.get_table_names(schema="public"))
            missing = [t for t in REQUIRED_TABLES if t not in existing]
            if not missing:
                self._add("public_schema_tables", "pass")
            else:
                self._add("public_schema_tables", "fail", f"Missing tables: {missing}")
        except Exception as exc:
            self._add("public_schema_tables", "warn", f"Could not inspect schema: {exc}")

    def _check_seed_user(self) -> None:
        """Optional check — warns but never fails (seed may not exist in fresh env)."""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import Session as SQLASession
            from sqlalchemy import text as sql_text
            engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=False)
            with SQLASession(engine) as session:
                count = session.execute(sql_text("SELECT COUNT(*) FROM users WHERE is_active = true")).scalar()
            if count and count > 0:
                self._add("seed_user_present", "pass", f"{count} active user(s)")
            else:
                self._add("seed_user_present", "warn", "No active users found — run seed_auth.py")
        except Exception as exc:
            self._add("seed_user_present", "warn", f"Could not query users table: {exc}")

    def _check_app_config(self) -> None:
        is_prod = settings.app_env == "production"
        issues: list[str] = []
        for attr in REQUIRED_SETTINGS_PROD:
            val = getattr(settings, attr, None)
            if not val:
                issues.append(f"{attr.upper()} missing")
        if is_prod:
            for attr in REQUIRED_SETTINGS_DEV_WARN:
                val = getattr(settings, attr, None)
                if not val:
                    issues.append(f"{attr.upper()} missing")
        if not issues:
            self._add("app_config_complete", "pass")
        elif is_prod:
            self._add("app_config_complete", "fail", "; ".join(issues))
        else:
            self._add("app_config_complete", "warn", "; ".join(issues))

    # ── Public API ───────────────────────────────────────────────────────────

    def run(self) -> PreflightResult:
        """Run all checks. Order matters: later checks are skipped if DB unavailable."""
        self._checks = []

        db_url_ok = self._check_database_url()
        if not db_url_ok:
            return PreflightResult(checks=self._checks)

        db_ok = self._check_db_reachable()
        self._check_app_config()

        if db_ok:
            self._check_alembic_head()
            self._check_public_schema_tables()
            self._check_seed_user()

        result = PreflightResult(checks=self._checks)
        logger.info(
            "preflight.complete",
            extra={"event": "preflight.complete", "passed": result.passed,
                   "failed": len(result.failed_checks), "warned": len(result.warned_checks)},
        )
        return result

    def run_or_raise(self) -> PreflightResult:
        """Run checks. In fail-fast mode, raise RuntimeError on any failure."""
        result = self.run()
        if not result.passed and _fail_fast_mode():
            raise RuntimeError(
                f"Preflight failed — backend startup aborted.\n{result.summary()}"
            )
        if not result.passed:
            logger.error(
                "preflight.failed_warn_only",
                extra={"event": "preflight.failed_warn_only",
                       "detail": "fail-fast disabled; continuing despite preflight failures"},
            )
        return result
