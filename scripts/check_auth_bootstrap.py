from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
REPORT_PATH = ROOT / "reports" / "auth_bootstrap_guard.json"
DEFAULT_LOGIN = "mdickscheit@gmail.com"
DEFAULT_PASSWORD = "Alex..2026"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_ROLE = "admin"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8001"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def mask_database_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if not parsed.password:
        return value
    netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
    return parsed._replace(netloc=netloc).geturl()


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def check(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: dict[str, Any]) -> None:
    checks.append(
        {
            "id": check_id,
            "status": "PASS" if passed else "FAIL",
            "evidence": evidence,
        }
    )


def request_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    token: str | None = None,
    timeout_seconds: float = 5.0,
) -> tuple[int | None, dict[str, Any] | None, str | None]:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=payload, method=method, headers=headers)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else {}, None
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text) if text else {}
        except json.JSONDecodeError:
            parsed = {"raw": text[:500]}
        return exc.code, parsed, None
    except (TimeoutError, URLError, OSError) as exc:
        return None, None, str(exc)


def wait_for_api(api_base_url: str, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status, _, error = request_json("GET", f"{api_base_url.rstrip('/')}/health", timeout_seconds=1.0)
        if status is not None and status < 500 and error is None:
            return True
        time.sleep(0.5)
    return False


def start_api_if_needed(api_base_url: str, env: dict[str, str], no_start_api: bool) -> subprocess.Popen[bytes] | None:
    if wait_for_api(api_base_url, 1.0):
        return None
    if no_start_api:
        return None

    parsed = urlparse(api_base_url)
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or (443 if parsed.scheme == "https" else 80))
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stdout = (reports_dir / "auth_bootstrap_guard_backend.out.log").open("ab")
    stderr = (reports_dir / "auth_bootstrap_guard_backend.err.log").open("ab")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--app-dir",
            str(BACKEND_DIR),
            "app.main:app",
            "--host",
            host,
            "--port",
            port,
        ],
        cwd=str(ROOT),
        env=env,
        stdout=stdout,
        stderr=stderr,
    )
    return process


def run_seed_auth(env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(BACKEND_DIR / "scripts" / "seed_auth.py")],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    return {
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-1200:],
        "stderr_tail": completed.stderr[-1200:],
    }


def add_backend_path() -> None:
    backend = str(BACKEND_DIR)
    if backend not in sys.path:
        sys.path.insert(0, backend)


def run_db_checks(
    *,
    login: str,
    password: str,
    user_id: str,
    workspace_id: str,
    expected_role: str,
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    add_backend_path()

    from sqlalchemy import select

    from sqlalchemy.orm import Session

    from app.db.session import get_engine
    from app.models.documents import AuthSession, User, Workspace, WorkspaceMembership
    from app.services.auth import AuthService

    state: dict[str, Any] = {}
    with Session(get_engine()) as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if user is None:
            user = session.scalar(select(User).where(User.login == login))
        workspace = session.scalar(select(Workspace).where(Workspace.id == workspace_id))
        membership = session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.workspace_id == workspace_id,
            )
        )

        state["user"] = (
            {
                "id": str(user.id),
                "login": user.login,
                "is_active": bool(user.is_active),
                "is_default": bool(user.is_default),
            }
            if user is not None
            else None
        )
        state["workspace"] = (
            {
                "id": str(workspace.id),
                "name": workspace.name,
                "is_default": bool(workspace.is_default),
            }
            if workspace is not None
            else None
        )
        state["membership"] = (
            {
                "id": str(membership.id),
                "user_id": str(membership.user_id),
                "workspace_id": str(membership.workspace_id),
                "role": membership.role,
            }
            if membership is not None
            else None
        )

        check(checks, "seed_user_exists", user is not None and user.login == login, {"user": state["user"]})
        check(checks, "user_active", user is not None and bool(user.is_active), {"user": state["user"]})
        check(checks, "workspace_exists", workspace is not None, {"workspace": state["workspace"]})
        check(checks, "membership_exists", membership is not None, {"membership": state["membership"]})
        check(
            checks,
            "membership_role_admin",
            membership is not None and membership.role == expected_role,
            {"expected_role": expected_role, "membership": state["membership"]},
        )

        password_ok = False
        auth_error = None
        try:
            _, auth_session, _, memberships = AuthService(session).login(login=login, password=password)
            password_ok = True
            session.delete(session.get(AuthSession, str(auth_session.id)) or auth_session)
            session.commit()
            state["auth_service_membership_count"] = len(memberships)
        except Exception as exc:  # noqa: BLE001 - report exact guard failure cause.
            session.rollback()
            auth_error = f"{type(exc).__name__}: {exc}"

        check(
            checks,
            "password_works",
            password_ok,
            {"login": login, "auth_error": auth_error},
        )

    return state


def run_api_checks(
    *,
    api_base_url: str,
    login: str,
    password: str,
    workspace_id: str,
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    base = api_base_url.rstrip("/")
    login_status, login_body, login_error = request_json(
        "POST",
        f"{base}/api/v1/auth/login",
        body={"login": login, "password": password},
    )
    token = login_body.get("token") if isinstance(login_body, dict) else None
    login_ok = login_status == 200 and isinstance(token, str) and bool(token)
    check(
        checks,
        "auth_login_endpoint_works",
        login_ok,
        {
            "status": login_status,
            "error": login_error,
            "response_keys": sorted(login_body.keys()) if isinstance(login_body, dict) else None,
            "active_workspace_id": login_body.get("active_workspace_id") if isinstance(login_body, dict) else None,
        },
    )

    me_status: int | None = None
    me_body: dict[str, Any] | None = None
    me_error: str | None = None
    if token:
        me_status, me_body, me_error = request_json("GET", f"{base}/api/v1/auth/me", token=token)
    active_workspace_id = me_body.get("active_workspace_id") if isinstance(me_body, dict) else None
    me_ok = me_status == 200 and active_workspace_id == workspace_id
    check(
        checks,
        "auth_me_returns_active_workspace_id",
        me_ok,
        {
            "status": me_status,
            "error": me_error,
            "expected_active_workspace_id": workspace_id,
            "active_workspace_id": active_workspace_id,
            "response_keys": sorted(me_body.keys()) if isinstance(me_body, dict) else None,
        },
    )
    return {
        "login_status": login_status,
        "login_error": login_error,
        "me_status": me_status,
        "me_error": me_error,
        "active_workspace_id": active_workspace_id,
    }


def write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regression guard for auth/workspace bootstrap.")
    parser.add_argument("--api-base-url", default=os.environ.get("AUTH_BOOTSTRAP_API_BASE_URL") or os.environ.get("API_BASE_URL") or DEFAULT_API_BASE_URL)
    parser.add_argument("--no-start-api", action="store_true", help="Do not start uvicorn when the API is unreachable.")
    return parser.parse_args()


def main() -> int:
    load_dotenv(ROOT / ".env")
    args = parse_args()

    env = os.environ.copy()
    if not env.get("DATABASE_URL") and env.get("TEST_DATABASE_URL"):
        env["DATABASE_URL"] = env["TEST_DATABASE_URL"]
        os.environ["DATABASE_URL"] = env["DATABASE_URL"]
    env.setdefault("WISSEN_DEV_LOGIN", DEFAULT_LOGIN)
    env.setdefault("WISSEN_DEV_PASSWORD", DEFAULT_PASSWORD)
    env.setdefault("DEFAULT_USER_ID", DEFAULT_USER_ID)
    env.setdefault("DEFAULT_WORKSPACE_ID", DEFAULT_WORKSPACE_ID)

    login = env["WISSEN_DEV_LOGIN"]
    password = env["WISSEN_DEV_PASSWORD"]
    user_id = env["DEFAULT_USER_ID"]
    workspace_id = env["DEFAULT_WORKSPACE_ID"]
    expected_role = DEFAULT_ROLE
    checks: list[dict[str, Any]] = []
    api_process: subprocess.Popen[bytes] | None = None

    report: dict[str, Any] = {
        "generated_at": now_iso(),
        "guard": "auth_workspace_bootstrap",
        "result": "FAIL",
        "api_base_url": args.api_base_url,
        "database_url": mask_database_url(env.get("DATABASE_URL")),
        "seed_login": login,
        "seed_user_id": user_id,
        "seed_workspace_id": workspace_id,
        "expected_role": expected_role,
        "checks": checks,
    }

    try:
        if not env.get("DATABASE_URL"):
            check(checks, "database_url_configured", False, {"database_url": None})
            report["remaining_errors"] = ["DATABASE_URL is not configured"]
            write_report(report)
            return 1

        check(checks, "database_url_configured", True, {"database_url": mask_database_url(env.get("DATABASE_URL"))})
        seed = run_seed_auth(env)
        report["seed_auth"] = seed
        check(checks, "seed_auth_succeeded", seed["exit_code"] == 0, {"exit_code": seed["exit_code"]})
        if seed["exit_code"] != 0:
            report["remaining_errors"] = ["seed_auth.py failed"]
            write_report(report)
            return 1

        report["database_state"] = run_db_checks(
            login=login,
            password=password,
            user_id=user_id,
            workspace_id=workspace_id,
            expected_role=expected_role,
            checks=checks,
        )

        api_process = start_api_if_needed(args.api_base_url, env, args.no_start_api)
        api_ready = wait_for_api(args.api_base_url, 20.0)
        report["api_started_by_guard"] = api_process is not None
        check(checks, "api_reachable", api_ready, {"api_base_url": args.api_base_url})
        if api_ready:
            report["api"] = run_api_checks(
                api_base_url=args.api_base_url,
                login=login,
                password=password,
                workspace_id=workspace_id,
                checks=checks,
            )
        else:
            report["api"] = {"error": "API_UNREACHABLE"}

        failed = [item["id"] for item in checks if item["status"] != "PASS"]
        report["remaining_errors"] = failed
        report["result"] = "PASS" if not failed else "FAIL"
        write_report(report)
        return 0 if not failed else 1
    finally:
        if api_process is not None:
            api_process.terminate()
            try:
                api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api_process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
