"""
M4-Gate Runner
==============
Führt pytest mit ausschließlich M4-Gate-Markern aus.

Regeln:
  Rule 1  Wertet nur M4-Marker aus.
  Rule 2  M5- und Governance-Tests werden nicht geladen.
  Rule 4  Split-Reports werden automatisch durch den conftest-Plugin erzeugt.

Verwendung:
  python scripts/run_m4_gate.py
  python scripts/run_m4_gate.py -- -x -v        # pytest-Argumente nach --
  python scripts/run_m4_gate.py --dry-run        # zeigt pytest-Kommando, führt nicht aus

Exit-Codes:
  0  M4-Gate PASS (alle M4-Tests bestanden)
  1  M4-Gate FAIL (mindestens ein M4-Test fehlgeschlagen)
  2  Konfigurationsfehler (TEST_DATABASE_URL fehlt)
  3  Collection-Fehler (Rule 3: unmarkierte Truth-Tests gefunden)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"

# Rule 1: nur diese Marker
M4_GATE_MARKERS: tuple[str, ...] = (
    "m4_truth",
    "m4a_auth_truth",
    "m4b_upload_queue_truth",
    "m4c_lifecycle_retrieval_truth",
    "m4e_backup_restore_truth",
)

# Rule 2: diese Marker blockieren M4 nicht und werden bewusst ausgeschlossen
NON_BLOCKING_MARKERS: tuple[str, ...] = (
    "m5_truth",
    "governance_truth",
)


def _build_marker_expression() -> str:
    return " or ".join(M4_GATE_MARKERS)


def _check_prerequisites() -> list[str]:
    errors: list[str] = []
    if not os.getenv("TEST_DATABASE_URL"):
        errors.append(
            "TEST_DATABASE_URL ist nicht gesetzt. "
            "Postgres-Instanz konfigurieren oder docker-compose.test.yml starten."
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="M4-Gate: führt nur M4-Truth-Tests aus (Rule 1+2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Zeigt das pytest-Kommando, ohne es auszuführen.",
    )
    parser.add_argument(
        "--no-preflight-check",
        action="store_true",
        help="TEST_DATABASE_URL-Prüfung überspringen (nicht empfohlen).",
    )
    parser.add_argument(
        "extra_pytest_args",
        nargs=argparse.REMAINDER,
        metavar="-- [pytest-args]",
        help="Optionale pytest-Argumente nach --.",
    )
    args = parser.parse_args(argv)

    extra: list[str] = args.extra_pytest_args
    if extra and extra[0] == "--":
        extra = extra[1:]

    if not args.no_preflight_check:
        errors = _check_prerequisites()
        if errors:
            for error in errors:
                print(f"[M4-Gate] Fehler: {error}", file=sys.stderr)
            return 2

    marker_expr = _build_marker_expression()
    cmd: list[str] = [
        sys.executable, "-m", "pytest",
        str(BACKEND_DIR / "tests"),
        "-m", marker_expr,
        "--tb=short",
        "-q",
        f"--rootdir={REPO_ROOT}",
    ] + extra

    print("[M4-Gate] Rule 1: Marker =", " | ".join(M4_GATE_MARKERS))
    print("[M4-Gate] Rule 2: Excluded =", " | ".join(NON_BLOCKING_MARKERS))
    print("[M4-Gate] Kommando:", " ".join(cmd))

    if args.dry_run:
        print("[M4-Gate] Dry-run — kein Aufruf.")
        return 0

    result = subprocess.run(cmd, cwd=REPO_ROOT)
    exit_code = result.returncode

    if exit_code == 0:
        print("[M4-Gate] STATUS: PASS")
    elif exit_code == 3:
        print("[M4-Gate] STATUS: ABBRUCH — Rule-3-Verletzung (unmarkierte Truth-Tests)", file=sys.stderr)
    else:
        print(f"[M4-Gate] STATUS: FAIL (exit code {exit_code})", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
