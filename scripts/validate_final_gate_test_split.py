"""Validate the local/external final gate test split report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_REPORT = Path("reports/current/final_gate_test_split.json")


def _load_report(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _blockers(section: dict[str, Any], *, skips_block: bool) -> list[str]:
    blockers: list[str] = []
    if section.get("collected", 0) <= 0:
        blockers.append("no tests collected")
    if section.get("exit_code", 1) != 0:
        blockers.append(f"exit_code={section.get('exit_code')}")
    if section.get("failed", 0):
        blockers.append(f"failed={section.get('failed')}")
    if section.get("errors", 0):
        blockers.append(f"errors={section.get('errors')}")
    if skips_block and section.get("skipped", 0):
        blockers.append(f"skipped={section.get('skipped')}")
    return blockers


def validate(report: dict[str, Any]) -> tuple[bool, list[str]]:
    local = report.get("local_gate", {})
    external = report.get("external_env_gate", {})
    blockers = [f"local_gate: {item}" for item in _blockers(local, skips_block=True)]

    external_markers = set(external.get("required_markers", []))
    required = {"external_env_only", "legacy_live_http"}
    if external.get("skipped", 0) and not required <= external_markers:
        blockers.append("external_env_gate: skipped tests are not classified as external legacy HTTP")

    return not blockers, blockers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", nargs="?", default=str(DEFAULT_REPORT))
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    report = _load_report(report_path)
    ok, blockers = validate(report)
    if ok:
        print(f"PASS local final gate split: {report_path}")
        return 0

    print(f"FAIL local final gate split: {report_path}")
    for blocker in blockers:
        print(f"- {blocker}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
